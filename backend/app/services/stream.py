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
