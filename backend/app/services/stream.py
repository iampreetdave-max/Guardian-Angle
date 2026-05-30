"""Live public-stream ingestion.

Lets an investigator point VisionScan at an *intentionally public* live feed —
a government traffic camera (RTSP/HLS/MJPEG) or a public YouTube-live street
cam — capture a bounded window of it, and run the exact same analysis pipeline
used for uploaded files.

IMPORTANT (ethics/legal): this is intended for feeds that are deliberately
published for public viewing. Accessing private or unsecured CCTV cameras
without authorization is illegal. The UI states this; the backend does not and
cannot police it, so operators are responsible for using lawful sources.

YouTube-live URLs are resolved to a direct stream URL with yt-dlp (if present);
RTSP/HLS/HTTP(MJPEG) URLs are opened directly by OpenCV.
"""
from __future__ import annotations

import logging

from .pipeline import process_video

log = logging.getLogger("visionscan.stream")

_YT_HOSTS = ("youtube.com", "youtu.be")


def resolve_stream_url(url: str) -> str:
    """Return a URL that OpenCV's VideoCapture can open.

    For YouTube(-live) links we use yt-dlp to extract the underlying HLS/stream
    URL. Other schemes (rtsp://, http(s):// .m3u8 / mjpeg) are returned as-is.
    """
    lowered = url.lower()
    if any(h in lowered for h in _YT_HOSTS):
        try:
            import yt_dlp  # lazy: only needed for YouTube sources
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "yt-dlp is required to ingest YouTube streams. "
                "Install it with: pip install yt-dlp"
            ) from e

        opts = {
            "quiet": True,
            "no_warnings": True,
            # prefer a single progressive/HLS stream OpenCV can read
            "format": "best[protocol^=http]/best",
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        stream_url = info.get("url")
        if not stream_url:
            raise RuntimeError("Could not resolve a playable stream URL from YouTube")
        return stream_url

    return url


def process_stream(
    video_id: int,
    url: str,
    max_duration_sec: float,
    max_frames: int | None = None,
) -> None:
    """Resolve a public stream URL and run the analysis pipeline on a bounded
    capture window. Safe to call in a background thread."""
    try:
        resolved = resolve_stream_url(url)
    except Exception as e:
        log.exception("Failed to resolve stream %s", url)
        from ..database import get_conn

        with get_conn() as conn:
            conn.execute(
                "UPDATE videos SET status = 'error', error = ? WHERE id = ?",
                (str(e), video_id),
            )
        return

    process_video(
        video_id,
        source_path=resolved,
        max_duration_sec=max_duration_sec,
        max_frames=max_frames,
    )


# ----------------------------------------------------------------------------
# Continuous LIVE monitoring: watch a public feed and keep indexing it until
# stopped, so an investigator can view the stream and search it in real time.
# ----------------------------------------------------------------------------
import threading

from ..config import get_settings
from ..database import get_conn

_live_sessions: dict[int, threading.Event] = {}
_live_lock = threading.Lock()


def is_live(video_id: int) -> bool:
    return video_id in _live_sessions


def _run_live(video_id: int, url: str, stop_event: threading.Event) -> None:
    """Daemon loop: resolve the feed, then continuously extract + index
    keyframes until stop_event is set."""
    from ..core import ingestion
    from ..core.index import get_clip_index, get_face_index
    from .pipeline import process_keyframe

    settings = get_settings()
    try:
        resolved = resolve_stream_url(url)
    except Exception as e:
        log.exception("Live: failed to resolve %s", url)
        with get_conn() as conn:
            conn.execute("UPDATE videos SET status='error', error=? WHERE id=?",
                         (str(e), video_id))
        _live_sessions.pop(video_id, None)
        return

    thumb_dir = settings.thumbnails_dir / str(video_id)
    thumb_dir.mkdir(parents=True, exist_ok=True)
    clip_index, face_index = get_clip_index(), get_face_index()
    kept = 0
    try:
        for kf in ingestion.extract_keyframes(resolved, stop_event=stop_event):
            process_keyframe(video_id, kf, thumb_dir)
            kept += 1
            # Update the visible count every frame so the live indicator moves;
            # persist the FAISS indexes less often (every 5) to limit disk I/O.
            with get_conn() as conn:
                conn.execute(
                    "UPDATE videos SET keyframe_count=?, duration_sec=? WHERE id=?",
                    (kept, kf.timestamp_sec, video_id))
            if kept % 5 == 0:
                clip_index.save()
                face_index.save()
    except Exception:
        log.exception("Live capture error for video %s", video_id)
    finally:
        clip_index.save()
        face_index.save()
        with get_conn() as conn:
            conn.execute(
                "UPDATE videos SET status='ready', keyframe_count=? WHERE id=?",
                (kept, video_id))
        _live_sessions.pop(video_id, None)
        log.info("Live session ended for video %s: %d keyframes", video_id, kept)


def start_live(url: str, camera_id: str) -> int:
    """Create a feed record and start a continuous live-capture session.
    Returns the new video_id."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO videos (filename, path, camera_id, status) "
            "VALUES (?, ?, ?, 'live')",
            (f"[LIVE] {url[:80]}", url, camera_id),
        )
        video_id = cur.lastrowid

    stop_event = threading.Event()
    with _live_lock:
        _live_sessions[video_id] = stop_event
    threading.Thread(
        target=_run_live, args=(video_id, url, stop_event), daemon=True
    ).start()
    return video_id


def stop_live(video_id: int) -> bool:
    """Signal a live session to stop. Returns True if one was running."""
    with _live_lock:
        ev = _live_sessions.get(video_id)
    if ev is None:
        return False
    ev.set()
    return True
