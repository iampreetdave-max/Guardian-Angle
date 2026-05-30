"""Detection layer — YOLOv8 (objects) + InsightFace ArcFace (faces).

Both detectors load lazily and fail soft: if a model can't be loaded (missing
weights, no internet on a field laptop, unsupported hardware), the relevant
feature is silently disabled and the rest of the pipeline keeps working. This
is deliberate — semantic text/image search must never be blocked by an optional
detector.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..config import get_settings

log = logging.getLogger("visionscan.detection")

# ---------------- YOLOv8 ----------------
_yolo_lock = threading.Lock()
_yolo = None
_yolo_failed = False


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2


def _ensure_yolo():
    global _yolo, _yolo_failed
    if _yolo is not None or _yolo_failed:
        return _yolo
    with _yolo_lock:
        if _yolo is not None or _yolo_failed:
            return _yolo
        try:
            from ultralytics import YOLO

            s = get_settings()
            model = YOLO(s.yolo_model_name)
            _yolo = model
            log.info("YOLOv8 loaded: %s", s.yolo_model_name)
        except Exception as e:  # pragma: no cover - environment dependent
            _yolo_failed = True
            log.warning("YOLOv8 unavailable, object detection disabled: %s", e)
    return _yolo


def yolo_available() -> bool:
    s = get_settings()
    if not s.enable_detection or _yolo_failed:
        return False
    if _yolo is not None:
        return True
    import importlib.util
    return importlib.util.find_spec("ultralytics") is not None


def detect_objects(frame_bgr: np.ndarray) -> list[Detection]:
    s = get_settings()
    if not s.enable_detection:
        return []
    model = _ensure_yolo()
    if model is None:
        return []
    results = model.predict(
        frame_bgr, conf=s.yolo_conf_threshold, verbose=False
    )
    out: list[Detection] = []
    for r in results:
        names = r.names
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            out.append(Detection(names[cls_id], conf, (x1, y1, x2, y2)))
    return out


# ---------------- InsightFace (ArcFace) ----------------
_face_lock = threading.Lock()
_face_app = None
_face_failed = False


@dataclass
class Face:
    bbox: tuple[float, float, float, float]
    det_score: float
    embedding: np.ndarray  # (512,) normalized float32


def _ensure_face():
    global _face_app, _face_failed
    if _face_app is not None or _face_failed:
        return _face_app
    with _face_lock:
        if _face_app is not None or _face_failed:
            return _face_app
        try:
            from insightface.app import FaceAnalysis

            s = get_settings()
            providers = (
                ["CUDAExecutionProvider", "CPUExecutionProvider"]
                if s.resolve_device() == "cuda"
                else ["CPUExecutionProvider"]
            )
            app = FaceAnalysis(name=s.face_model_name, providers=providers)
            app.prepare(ctx_id=0 if s.resolve_device() == "cuda" else -1,
                        det_size=(640, 640))
            _face_app = app
            log.info("InsightFace loaded: %s", s.face_model_name)
        except Exception as e:  # pragma: no cover - environment dependent
            _face_failed = True
            log.warning("InsightFace unavailable, face matching disabled: %s", e)
    return _face_app


def face_available() -> bool:
    s = get_settings()
    if not s.enable_face or _face_failed:
        return False
    if _face_app is not None:
        return True
    # Report honestly before first use: only "available" if the package is
    # actually importable (the core / HF image omits insightface).
    import importlib.util
    return importlib.util.find_spec("insightface") is not None


def _norm(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return (v / n).astype("float32") if n > 0 else v.astype("float32")


def detect_faces(frame_bgr: np.ndarray) -> list[Face]:
    s = get_settings()
    if not s.enable_face:
        return []
    app = _ensure_face()
    if app is None:
        return []
    faces = app.get(frame_bgr)
    out: list[Face] = []
    for f in faces:
        x1, y1, x2, y2 = [float(v) for v in f.bbox]
        emb = _norm(np.asarray(f.normed_embedding, dtype="float32"))
        out.append(Face((x1, y1, x2, y2), float(f.det_score), emb))
    return out


def warmup() -> None:
    """Eagerly load the detectors so the first live frame / search isn't stalled
    by lazy model loading (which can take ~30s for all models on CPU)."""
    s = get_settings()
    if s.enable_detection:
        _ensure_yolo()
    if s.enable_face:
        _ensure_face()


def embed_reference_face(frame_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Embed the most prominent face in a reference image (suspect photo).
    Returns a normalized (512,) vector, or None if no face found."""
    faces = detect_faces(frame_bgr)
    if not faces:
        return None
    # pick the largest face by bbox area
    faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
               reverse=True)
    return faces[0].embedding
