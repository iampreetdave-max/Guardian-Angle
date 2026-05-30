"""Generate a synthetic test video for smoke-testing the pipeline offline.

Creates distinct visual "scenes" (different dominant colors + moving shapes +
on-frame text labels) so we can verify ingestion -> CLIP embedding -> FAISS ->
text search works end-to-end without needing real footage. CLIP can match the
text labels / colors well enough to prove the retrieval path.

Usage (from backend/):
    python scripts/make_test_video.py            # writes data/test_clip.mp4
    python scripts/make_test_video.py out.mp4
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

W, H, FPS = 640, 360, 20

# (label, BGR background, shape color BGR)
SCENES = [
    ("a red car on the road", (40, 40, 40), (40, 40, 200)),
    ("a person in a blue jacket", (90, 70, 30), (200, 120, 40)),
    ("a green truck near the gate", (50, 50, 50), (60, 180, 60)),
    ("a white van in a parking lot", (60, 60, 60), (230, 230, 230)),
    ("a yellow motorcycle at night", (15, 15, 20), (40, 220, 230)),
]
SECONDS_PER_SCENE = 3


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent.parent.parent / "data" / "test_clip.mp4"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, FPS, (W, H))

    for label, bg, shape in SCENES:
        for i in range(FPS * SECONDS_PER_SCENE):
            frame = np.full((H, W, 3), bg, dtype=np.uint8)
            # moving shape to trigger motion-based keyframes
            x = int((i / (FPS * SECONDS_PER_SCENE)) * (W - 120)) + 10
            cv2.rectangle(frame, (x, 160), (x + 100, 240), shape, -1)
            cv2.circle(frame, (x + 50, 150), 28, shape, -1)
            cv2.putText(frame, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (255, 255, 255), 2, cv2.LINE_AA)
            writer.write(frame)

    writer.release()
    print(f"[VisionScan] Wrote synthetic test video -> {out_path}")
    print(f"             {len(SCENES)} scenes x {SECONDS_PER_SCENE}s @ {FPS}fps")


if __name__ == "__main__":
    main()
