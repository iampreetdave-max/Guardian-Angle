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

import numpy as np

from ..config import get_settings
from ..core import detection, embedding, ingestion, preprocessing
from ..core.index import get_clip_index, get_face_index, get_object_index
from ..database import get_conn

log = logging.getLogger("visionscan.pipeline")

# Skip embedding crops smaller than this (px on the longest edge) — tiny
# detections are too low-detail to embed meaningfully.
_MIN_CROP_EDGE = 24


def _save_thumbnail(frame_bgr, dest: Path, max_size: int) -> None:
    h, w = frame_bgr.shape[:2]
    scale = max_size / max(h, w)
    if scale < 1.0:
        frame_bgr = cv2.resize(frame_bgr, (int(w * scale), int(h * scale)))
    cv2.imwrite(str(dest), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])


def _embed_object_crop(frame_bgr, bbox, object_index) -> int | None:
    """Crop the detected object, CLIP-embed it, add to the object index.
    Returns the assigned faiss id, or None if the crop is unusable."""
    h, w = frame_bgr.shape[:2]
    x1, y1, x2, y2 = bbox
    # clamp + pad a little for context
    x1 = max(0, int(x1)); y1 = max(0, int(y1))
    x2 = min(w, int(x2)); y2 = min(h, int(y2))
    if x2 - x1 < _MIN_CROP_EDGE or y2 - y1 < _MIN_CROP_EDGE:
        return None
    crop = frame_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    vec = embedding.embed_images(Image.fromarray(rgb))
    return object_index.add(vec)[0]


def _set_status(video_id: int, status: str, error: str | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE videos SET status = ?, error = ? WHERE id = ?",
            (status, error, video_id),
        )


def process_keyframe(video_id: int, kf, thumb_dir: Path,
                     is_live: bool = False) -> int:
    """Run layers 2-3 on a single keyframe: enhance, thumbnail, CLIP-embed +
    index, persist the frame row, and run object/face detection. Returns the
    new frame_id. Shared by both the batch (process_video) and continuous
    (process_stream_live) paths so they stay identical. is_live marks frames
    from a continuous feed so anomaly alerts can notify admins in real time."""
    settings = get_settings()
    clip_index = get_clip_index()
    face_index = get_face_index()

    enhanced = preprocessing.maybe_enhance(kf.image_bgr)

    thumb_name = f"{kf.frame_number:08d}.jpg"
    _save_thumbnail(enhanced, thumb_dir / thumb_name, settings.thumbnail_max_size)
    rel_thumb = f"{video_id}/{thumb_name}"

    rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
    vec = embedding.embed_images(Image.fromarray(rgb))
    clip_faiss_id = clip_index.add(vec)[0]

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO frames (video_id, frame_number, timestamp_sec, "
            "thumbnail_path, clip_faiss_id) VALUES (?, ?, ?, ?, ?)",
            (video_id, kf.frame_number, kf.timestamp_sec, rel_thumb, clip_faiss_id),
        )
        frame_id = cur.lastrowid

    object_index = get_object_index()
    dets = detection.detect_objects(enhanced)
    for det in dets:
        # Embed the object's crop in CLIP space so it can be found individually
        # by a text/image query (e.g. each of five red cars), not just the frame.
        obj_faiss_id = _embed_object_crop(enhanced, det.bbox, object_index)
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO detections (frame_id, label, confidence, "
                "x1, y1, x2, y2, obj_faiss_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (frame_id, det.label, det.confidence, *det.bbox, obj_faiss_id),
            )

    # Anomaly watch: score the SAME clip vector + detections we just computed
    # (near-zero extra cost) and record any fire/smoke/accident/weapon/violence
    # signal as a debounced event. Strictly fail-soft — never blocks ingest.
    if settings.enable_anomaly:
        try:
            from ..core import anomaly
            from .anomaly_events import record_signals

            signals = anomaly.detect_anomalies(vec[0], dets, frame_bgr=enhanced)
            if signals:
                record_signals(video_id, frame_id, kf.timestamp_sec,
                               signals, is_live=is_live)
        except Exception:
            log.warning("anomaly scoring failed for frame %s", frame_id,
                        exc_info=True)

    for face in detection.detect_faces(enhanced):
        face_faiss_id = face_index.add(face.embedding.reshape(1, -1))[0]
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO faces (frame_id, face_faiss_id, det_score, "
                "x1, y1, x2, y2) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (frame_id, face_faiss_id, face.det_score, *face.bbox),
            )
    return frame_id


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
    object_index = get_object_index()
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
            process_keyframe(video_id, kf, thumb_dir)

            kept += 1
            if kept % 25 == 0:
                clip_index.save()
                face_index.save()
                object_index.save()
                with get_conn() as conn:
                    conn.execute(
                        "UPDATE videos SET keyframe_count = ? WHERE id = ?",
                        (kept, video_id),
                    )

        clip_index.save()
        face_index.save()
        object_index.save()
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


def reindex_video(video_id: int) -> None:
    """Clear a file-based video's existing frames + index entries, then re-run
    the full pipeline so it gains object-crop (region) embeddings."""
    clip_index, face_index, object_index = (
        get_clip_index(), get_face_index(), get_object_index()
    )
    with get_conn() as conn:
        clip_ids = [r["clip_faiss_id"] for r in conn.execute(
            "SELECT clip_faiss_id FROM frames WHERE video_id=? AND clip_faiss_id "
            "IS NOT NULL", (video_id,))]
        face_ids = [r["face_faiss_id"] for r in conn.execute(
            "SELECT fa.face_faiss_id FROM faces fa JOIN frames f ON f.id=fa.frame_id "
            "WHERE f.video_id=? AND fa.face_faiss_id IS NOT NULL", (video_id,))]
        obj_ids = [r["obj_faiss_id"] for r in conn.execute(
            "SELECT d.obj_faiss_id FROM detections d JOIN frames f ON f.id=d.frame_id "
            "WHERE f.video_id=? AND d.obj_faiss_id IS NOT NULL", (video_id,))]
        conn.execute("DELETE FROM frames WHERE video_id=?", (video_id,))
    clip_index.remove(clip_ids)
    face_index.remove(face_ids)
    object_index.remove(obj_ids)
    log.info("Reindexing video %s (cleared %d frames' vectors)", video_id, len(clip_ids))
    process_video(video_id)
