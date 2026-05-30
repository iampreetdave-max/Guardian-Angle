"""CLI helper to ingest a video without the API — handy for demo prep / testing.

Usage (from backend/):
    python -m scripts.ingest path/to/footage.mp4 --camera CAM-Gate-1

It runs the exact same pipeline the API uses, so the resulting index is
identical to what an upload would produce.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# See app/main.py — avoid the Windows torch/faiss OpenMP clash at import time.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# allow `python scripts/ingest.py` as well as `-m scripts.ingest`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_conn, init_db  # noqa: E402
from app.services.pipeline import process_video  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest a video into VisionScan.")
    ap.add_argument("video", help="Path to the video file")
    ap.add_argument("--camera", default="CAM-1", help="Camera id label")
    args = ap.parse_args()

    path = Path(args.video).resolve()
    if not path.exists():
        ap.error(f"File not found: {path}")

    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO videos (filename, path, camera_id, status) "
            "VALUES (?, ?, ?, 'pending')",
            (path.name, str(path), args.camera),
        )
        video_id = cur.lastrowid

    print(f"[VisionScan] Ingesting {path.name} as {args.camera} (id={video_id})…")
    process_video(video_id)
    print("[VisionScan] Done. Start the API and search the footage.")


if __name__ == "__main__":
    main()
