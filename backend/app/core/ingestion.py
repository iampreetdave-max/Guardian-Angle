"""Ingestion layer — OpenCV frame extraction with adaptive keyframe sampling.

Naively embedding every frame is wasteful: CCTV footage is mostly static. The
adaptive sampler keeps a frame when EITHER
  * the scene changes (HSV histogram correlation with the last kept frame
    drops below scene_change_threshold), OR
  * motion is detected (mean absolute pixel difference exceeds motion_threshold),
subject to a minimum spacing (min_frame_interval_sec) to avoid bursts, and a
hard ceiling (max_frame_interval_sec) so long static stretches still get a
periodic keyframe. This typically reduces frames 10-50x while preserving every
visually distinct moment — exactly what an investigator needs to scrub.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterator

import cv2
import numpy as np

from ..config import get_settings

log = logging.getLogger("visionscan.ingestion")


@dataclass
class VideoMeta:
    fps: float
    frame_count: int
    duration_sec: float


@dataclass
class Keyframe:
    frame_number: int
    timestamp_sec: float
    image_bgr: np.ndarray


def probe(video_path: str) -> VideoMeta:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    duration = frame_count / fps if fps else 0.0
    return VideoMeta(fps=fps, frame_count=frame_count, duration_sec=duration)


def _hist(frame_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
    return hist


def extract_keyframes(
    video_path: str,
    max_duration_sec: float | None = None,
    max_frames: int | None = None,
) -> Iterator[Keyframe]:
    """Yield adaptively-sampled keyframes from a video or live stream.

    For finite files, iteration ends naturally at EOF. For live streams (which
    never end), pass max_duration_sec and/or max_frames to bound capture — the
    timestamp is then taken from wall-clock elapsed time, since a stream's
    reported frame index is not meaningful.
    """
    import time

    s = get_settings()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    min_gap = int(max(1, s.min_frame_interval_sec * fps))
    max_gap = int(max(min_gap, s.max_frame_interval_sec * fps))
    is_stream = max_duration_sec is not None
    start_wall = time.time()

    prev_hist: np.ndarray | None = None
    prev_gray: np.ndarray | None = None
    last_kept_idx = -10**9
    kept = 0
    idx = -1

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1

        elapsed = time.time() - start_wall
        if max_duration_sec is not None and elapsed >= max_duration_sec:
            break

        gray = cv2.cvtColor(
            cv2.resize(frame, (320, 180)), cv2.COLOR_BGR2GRAY
        )
        cur_hist = _hist(frame)

        keep = False
        if prev_hist is None:
            keep = True  # always keep the first frame
        else:
            since = idx - last_kept_idx
            if since < min_gap:
                keep = False
            elif since >= max_gap:
                keep = True  # periodic anchor frame
            else:
                hist_corr = cv2.compareHist(prev_hist, cur_hist, cv2.HISTCMP_CORREL)
                scene_changed = hist_corr < (1.0 - s.scene_change_threshold)
                motion = float(np.mean(cv2.absdiff(prev_gray, gray)))
                keep = scene_changed or motion > s.motion_threshold

        if keep:
            yield Keyframe(
                frame_number=idx,
                timestamp_sec=elapsed if is_stream else idx / fps,
                image_bgr=frame,
            )
            last_kept_idx = idx
            prev_hist = cur_hist
            prev_gray = gray
            kept += 1
            if max_frames is not None and kept >= max_frames:
                break
        elif prev_hist is None:
            prev_hist = cur_hist
            prev_gray = gray

    cap.release()


def format_timestamp(seconds: float) -> str:
    """Seconds -> HH:MM:SS for the UI / report."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"
