"""Anomaly watch — always-on incident detection over the keyframe stream.

Hybrid, zero-extra-inference design:
  * CLIP zero-shot: every keyframe already gets a CLIP vector for search; we
    score that same vector against per-class prompt ensembles (fire, smoke,
    accident, weapon, violence). A class fires only when it beats the best
    "normal scene" prompt by a margin — this calibration keeps ordinary street
    footage at ~zero and is the main false-positive guard.
  * YOLO objects: the detections the pipeline already produced are scanned for
    weapon-class labels (COCO 'knife'); an optional specialized weights file
    can add domain classes (fire, gun...) and is loaded fail-soft like every
    other model in this codebase.

Nothing here may ever block ingestion: callers wrap us in try/except and all
model access is lazy + fail-soft.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import numpy as np

from ..config import get_settings
from . import embedding
from .detection import YOLO_INFER_LOCK, Detection

log = logging.getLogger("visionscan.anomaly")

ANOMALY_CLASSES = ("fire", "smoke", "accident", "weapon", "violence")

# Prompt ensembles — several phrasings per class are averaged so a single
# odd wording doesn't dominate. Negative/"normal" prompts anchor the margin.
ANOMALY_PROMPTS: dict[str, list[str]] = {
    "fire": [
        "a building on fire with visible flames",
        "large orange flames burning",
        "a fire emergency with burning objects",
    ],
    "smoke": [
        "thick dark smoke billowing into the air",
        "a smoke-filled street after an explosion",
        "heavy smoke rising from a building",
    ],
    "accident": [
        "a car crash with damaged vehicles",
        "a road traffic accident scene",
        "a wrecked vehicle after a collision",
    ],
    "weapon": [
        "a person holding a gun and threatening",
        "a person brandishing a knife",
        "an armed robbery with a firearm",
    ],
    "violence": [
        "people fighting violently in the street",
        "a physical assault between people",
        "a violent brawl in a crowd",
    ],
}

NORMAL_PROMPTS: list[str] = [
    "a normal city street with traffic",
    "people walking peacefully on a sidewalk",
    "an ordinary indoor scene with people",
    "calm traffic flowing on a road",
    "an empty quiet street",
    "a person standing and talking normally",
]

# YOLO label -> anomaly class. COCO only ships 'knife'; specialized weights
# (if configured) commonly use these label names too.
_YOLO_LABEL_MAP = {
    "knife": "weapon",
    "gun": "weapon",
    "pistol": "weapon",
    "rifle": "weapon",
    "fire": "fire",
    "smoke": "smoke",
}


@dataclass
class AnomalySignal:
    type: str
    confidence: float
    source: str  # "clip" | "yolo"
    # Bounding box as fractions of frame size (x1, y1, x2, y2 in 0..1), so the
    # UI can overlay it as percentages without knowing the source resolution.
    # None for CLIP signals — CLIP scores the whole frame and cannot localize.
    bbox: tuple[float, float, float, float] | None = None


def _norm_bbox(bbox: tuple[float, float, float, float] | None,
               w: int, h: int) -> tuple[float, float, float, float] | None:
    """Convert a pixel-space (x1,y1,x2,y2) box to 0..1 fractions, clamped."""
    if bbox is None or w <= 0 or h <= 0:
        return None
    x1, y1, x2, y2 = bbox
    clamp = lambda v: min(max(float(v), 0.0), 1.0)
    return (clamp(x1 / w), clamp(y1 / h), clamp(x2 / w), clamp(y2 / h))


# ---------------- CLIP text bank (lazy process-wide singleton) ----------------
_bank_lock = threading.Lock()
_class_means: dict[str, np.ndarray] | None = None  # class -> (512,) normalized
_normal_bank: np.ndarray | None = None             # (N, 512) normalized


def _ensure_text_bank() -> bool:
    """Embed all anomaly + normal prompts once. Returns False if CLIP is
    unavailable (the caller then simply skips CLIP scoring)."""
    global _class_means, _normal_bank
    if _class_means is not None:
        return True
    with _bank_lock:
        if _class_means is not None:
            return True
        try:
            means: dict[str, np.ndarray] = {}
            for cls, prompts in ANOMALY_PROMPTS.items():
                vecs = embedding.embed_text(prompts)          # (k, 512)
                mean = vecs.mean(axis=0)
                mean /= max(float(np.linalg.norm(mean)), 1e-12)
                means[cls] = mean.astype("float32")
            _normal_bank = embedding.embed_text(NORMAL_PROMPTS)
            _class_means = means
            log.info("Anomaly text bank ready (%d classes, %d normal anchors)",
                     len(means), len(NORMAL_PROMPTS))
        except Exception:
            log.warning("Anomaly text bank unavailable (CLIP not loaded?)",
                        exc_info=True)
            return False
    return True


# Per-class margin floors, tuned on the selftest probe set: classes whose
# prompts sit close to "normal" CLIP space (violence, accident) get a lower
# floor; visually loud classes (fire) a higher one. Env-overridable via
# VISIONSCAN_ANOMALY_CLASS_THRESHOLDS.
_DEFAULT_CLASS_THRESHOLDS = {
    "fire": 0.05,
    "smoke": 0.05,
    "accident": 0.03,
    "weapon": 0.04,
    "violence": 0.03,
}

# Margin where the normalized confidence saturates (~0.99). Margins observed
# for unambiguous anomaly content top out around +0.15.
_MARGIN_SATURATION = 0.12


def _class_threshold(cls: str) -> float:
    s = get_settings()
    if cls in s.anomaly_class_thresholds:
        return float(s.anomaly_class_thresholds[cls])
    return float(_DEFAULT_CLASS_THRESHOLDS.get(cls, s.anomaly_conf_threshold))


def _margin_to_conf(margin: float, threshold: float) -> float:
    """Rescale a CLIP margin onto the 0..1 confidence scale YOLO uses, so the
    UI percentage and the notify threshold mean the same thing for both
    sources: 0.5 at the firing floor, saturating near 0.99."""
    span = max(_MARGIN_SATURATION - threshold, 1e-6)
    frac = min(max((margin - threshold) / span, 0.0), 1.0)
    return round(0.5 + 0.49 * frac, 4)


def score_clip(frame_vec: np.ndarray) -> list[AnomalySignal]:
    """Margin scoring: cos(frame, class) − max cos(frame, normal anchors).
    Normal footage lands at or below zero by construction."""
    if not _ensure_text_bank():
        return []
    v = np.asarray(frame_vec, dtype="float32").reshape(-1)
    n = float(np.linalg.norm(v))
    if n <= 0:
        return []
    v = v / n
    best_normal = float(np.max(_normal_bank @ v))
    out: list[AnomalySignal] = []
    for cls, mean in _class_means.items():
        threshold = _class_threshold(cls)
        margin = float(mean @ v) - best_normal
        if margin >= threshold:
            out.append(AnomalySignal(cls, _margin_to_conf(margin, threshold),
                                     "clip"))
    return out


# ---------------- optional specialized YOLO (fail-soft) ----------------
_spec_lock = threading.Lock()
_spec_model = None
_spec_failed = False


def _ensure_specialized():
    global _spec_model, _spec_failed
    s = get_settings()
    if not s.anomaly_specialized_weights or _spec_failed:
        return None
    if _spec_model is not None:
        return _spec_model
    with _spec_lock:
        if _spec_model is not None or _spec_failed:
            return _spec_model
        try:
            from ultralytics import YOLO

            _spec_model = YOLO(s.anomaly_specialized_weights)
            log.info("Specialized anomaly YOLO loaded: %s",
                     s.anomaly_specialized_weights)
        except Exception as e:  # pragma: no cover - environment dependent
            _spec_failed = True
            log.warning("Specialized anomaly weights unavailable: %s", e)
    return _spec_model


def score_yolo(frame_bgr: np.ndarray | None,
               detections: list[Detection]) -> list[AnomalySignal]:
    """Object-level signals from detections the pipeline already ran, plus an
    optional specialized model pass when weights are configured."""
    s = get_settings()
    out: list[AnomalySignal] = []
    h, w = (frame_bgr.shape[:2] if frame_bgr is not None else (0, 0))
    for det in detections:
        cls = _YOLO_LABEL_MAP.get(det.label.lower())
        if cls and det.confidence >= s.anomaly_weapon_yolo_conf:
            out.append(AnomalySignal(cls, round(det.confidence, 4), "yolo",
                                     _norm_bbox(det.bbox, w, h)))

    model = _ensure_specialized()
    if model is not None and frame_bgr is not None:
        try:
            # Same non-thread-safe first-predict fuse as the base detector —
            # see detection.YOLO_INFER_LOCK.
            with YOLO_INFER_LOCK:
                results = list(model.predict(
                    frame_bgr, conf=s.anomaly_weapon_yolo_conf, verbose=False))
            for r in results:
                for box in r.boxes:
                    label = r.names[int(box.cls[0])].lower()
                    cls = _YOLO_LABEL_MAP.get(label, label)
                    if cls in ANOMALY_CLASSES:
                        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                        out.append(AnomalySignal(
                            cls, round(float(box.conf[0]), 4), "yolo",
                            _norm_bbox((x1, y1, x2, y2), w, h)))
        except Exception:  # pragma: no cover
            log.warning("Specialized anomaly inference failed", exc_info=True)
    return out


def detect_anomalies(frame_vec: np.ndarray,
                     detections: list[Detection],
                     frame_bgr: np.ndarray | None = None) -> list[AnomalySignal]:
    """Union of CLIP + YOLO signals, one per type (highest confidence wins,
    sources merged so the admin card can show how it was caught)."""
    merged: dict[str, AnomalySignal] = {}
    for sig in score_clip(frame_vec) + score_yolo(frame_bgr, detections):
        prev = merged.get(sig.type)
        if prev is None:
            merged[sig.type] = sig
        else:
            best = sig if sig.confidence > prev.confidence else prev
            if prev.source != sig.source:
                best = AnomalySignal(best.type, best.confidence, "clip+yolo",
                                     best.bbox or prev.bbox or sig.bbox)
            merged[sig.type] = best
    return list(merged.values())


def warmup() -> None:
    """Pre-embed the prompt bank so the first live frame isn't stalled."""
    if get_settings().enable_anomaly:
        _ensure_text_bank()
