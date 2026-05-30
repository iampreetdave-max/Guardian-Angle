"""Image preprocessing for low-light / IR CCTV footage.

CLAHE (Contrast Limited Adaptive Histogram Equalization) is applied on the
luminance channel only, which lifts detail out of dark night-vision frames
without blowing out color. This materially improves both CLIP embeddings and
YOLO/face detection on poor-quality field footage.
"""
from __future__ import annotations

import cv2
import numpy as np

from ..config import get_settings


def apply_clahe(frame_bgr: np.ndarray) -> np.ndarray:
    """Enhance a BGR frame's local contrast. Returns a BGR frame."""
    settings = get_settings()
    if not settings.enable_clahe:
        return frame_bgr

    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(
        clipLimit=settings.clahe_clip_limit,
        tileGridSize=(settings.clahe_grid_size, settings.clahe_grid_size),
    )
    l = clahe.apply(l)
    enhanced = cv2.merge((l, a, b))
    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)


def is_low_light(frame_bgr: np.ndarray, threshold: float = 60.0) -> bool:
    """Heuristic: mean luminance below threshold => treat as low-light."""
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return float(gray.mean()) < threshold


def maybe_enhance(frame_bgr: np.ndarray) -> np.ndarray:
    """Apply CLAHE only when the frame looks dark — avoids over-processing
    well-lit daytime footage."""
    if is_low_light(frame_bgr):
        return apply_clahe(frame_bgr)
    return frame_bgr
