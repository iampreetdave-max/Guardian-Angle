"""Pipeline orchestration — turns a raw video into searchable, indexed data.

Flow per video (the 5-layer pipeline, layers 1-3):
  1. Ingestion   : adaptive keyframe extraction (OpenCV)
  2. Preprocess  : CLAHE on low-light frames
  2. Embedding   : CLIP vector per keyframe  -> CLIP FAISS index
  3. Detection   : YOLOv8 objects + InsightFace faces -> DB + face FAISS index

Each keyframe's thumbnail is written to disk; metadata + faiss ids go to SQLite.
Runs as a FastAPI background task; progress is reflected in videos.status.
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
from PIL import Image

from ..config import get_settings
from ..core import detection, embedding, ingestion, preprocessing
from ..core.index import get_clip_index, get_face_index
from ..database import get_conn

log = logging.getLogger("visionscan.pipeline")


def _save_thumbnail(frame_bgr, dest: Path, max_size: int) -> None:
    h, w = frame_bgr.shape[:2]
    scale = max_size / max(h, w)
    if scale < 1.0:
        frame_bgr = cv2.resize(frame_bgr, (int(w * scale), int(h * scale)))
    cv2.imwrite(str(dest), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])


def _set_status(video_id: int, status: str, error: str | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE videos SET status = ?, error = ? WHERE id = ?",
            (status, error, video_id),
        )


def process_video(
    video_id: int,
    source_path: str | None = None,
    max_duration_sec: float | None = None,
    max_frames: int | None = None,
) -> None:
    """Full ingest+embed+detect pass for one video or live stream.

    For files, call with just video_id. For live streams, pass source_path (the
    resolved stream URL) plus a bound (max_duration_sec and/or max_frames) so
    capture terminates — a live feed never reaches EOF on its own.
    Safe to call in a background thread.
    """
    settings = get_settings()
    clip_index = get_clip_index()
    face_index = get_face_index()
    is_stream = max_duration_sec is not None or max_frames is not None

    with get_conn() as conn:
        row = conn.execute(
            "SELECT path FROM videos WHERE id = ?", (video_id,)
        ).fetchone()
    if row is None:
        log.error("process_video: video %s not found", video_id)
        return

    video_path = source_path or row["path"]
    _set_status(video_id, "processing")

    try:
        if not is_stream:
            meta = ingestion.probe(video_path)
            with get_conn() as conn:
                conn.execute(
                    "UPDATE videos SET fps = ?, frame_count = ?, duration_sec = ? "
                    "WHERE id = ?",
                    (meta.fps, meta.frame_count, meta.duration_sec, video_id),
                )

        thumb_dir = settings.thumbnails_dir / str(video_id)
        thumb_dir.mkdir(parents=True, exist_ok=True)
        kept = 0
        last_ts = 0.0

        for kf in ingestion.extract_keyframes(
            video_path, max_duration_sec=max_duration_sec, max_frames=max_frames
        ):
            last_ts = kf.timestamp_sec
            enhanced = preprocessing.maybe_enhance(kf.image_bgr)

            # --- thumbnail ---
            thumb_name = f"{kf.frame_number:08d}.jpg"
            thumb_path = thumb_dir / thumb_name
            _save_thumbnail(enhanced, thumb_path, settings.thumbnail_max_size)
            rel_thumb = f"{video_id}/{thumb_name}"

            # --- CLIP embedding (layer 2) ---
            rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb)
            vec = embedding.embed_images(pil)  # (1, 512)
            clip_faiss_id = clip_index.add(vec)[0]

            # --- persist frame ---
            with get_conn() as conn:
                cur = conn.execute(
                    "INSERT INTO frames (video_id, frame_number, timestamp_sec, "
                    "thumbnail_path, clip_faiss_id) VALUES (?, ?, ?, ?, ?)",
                    (video_id, kf.frame_number, kf.timestamp_sec, rel_thumb,
                     clip_faiss_id),
                )
                frame_id = cur.lastrowid

            # --- detection (layer 3) ---
            for det in detection.detect_objects(enhanced):
                with get_conn() as conn:
                    conn.execute(
                        "INSERT INTO detections (frame_id, label, confidence, "
                        "x1, y1, x2, y2) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (frame_id, det.label, det.confidence, *det.bbox),
                    )

            for face in detection.detect_faces(enhanced):
                face_faiss_id = face_index.add(face.embedding.reshape(1, -1))[0]
                with get_conn() as conn:
                    conn.execute(
                        "INSERT INTO faces (frame_id, face_faiss_id, det_score, "
                        "x1, y1, x2, y2) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (frame_id, face_faiss_id, face.det_score, *face.bbox),
                    )

            kept += 1
            if kept % 25 == 0:
                clip_index.save()
                face_index.save()
                with get_conn() as conn:
                    conn.execute(
                        "UPDATE videos SET keyframe_count = ? WHERE id = ?",
                        (kept, video_id),
                    )

        clip_index.save()
        face_index.save()
        with get_conn() as conn:
            if is_stream:
                conn.execute(
                    "UPDATE videos SET keyframe_count = ?, duration_sec = ?, "
                    "status = 'ready' WHERE id = ?",
                    (kept, last_ts, video_id),
                )
            else:
                conn.execute(
                    "UPDATE videos SET keyframe_count = ?, status = 'ready' "
                    "WHERE id = ?",
                    (kept, video_id),
                )
        log.info("Processed %s %s: %d keyframes",
                 "stream" if is_stream else "video", video_id, kept)

    except Exception as e:  # pragma: no cover
        log.exception("Failed to process video %s", video_id)
        _set_status(video_id, "error", str(e))
