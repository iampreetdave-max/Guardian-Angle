"""Regression: concurrent detection on the shared YOLO model must not crash.

Uploading several videos at once puts every ingest worker on one shared
ultralytics model. The first predict() call lazily builds a predictor and fuses
Conv+BatchNorm *in place*; two threads arriving together both call fuse(), and
the second dies with "'Conv' object has no attribute 'bn'" because the first
already deleted it. The video row is then marked status='error' and the clip is
silently missing from every search result.

Guarded by the same import skip the rest of the vision tests use, so the suite
still runs in environments without ultralytics installed.
"""
from __future__ import annotations

import threading

import numpy as np
import pytest

ultralytics = pytest.importorskip("ultralytics")


def test_concurrent_detect_objects_does_not_race():
    from app.core import detection

    # Force a cold model so the unsafe first-predict setup happens under load.
    detection._yolo = None
    detection._yolo_failed = False

    if not detection.yolo_available():
        pytest.skip("YOLO weights unavailable in this environment")

    frames = [
        np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) for _ in range(8)
    ]
    errors: list[BaseException] = []
    barrier = threading.Barrier(len(frames))

    def worker(frame):
        try:
            barrier.wait(timeout=120)  # maximize overlap on the first call
            detection.detect_objects(frame)
        except BaseException as exc:  # noqa: BLE001 - the point is to record it
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(f,)) for f in frames]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=300)

    assert not errors, f"concurrent detection raised: {errors[:3]}"


if __name__ == "__main__":  # pragma: no cover - manual run
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
