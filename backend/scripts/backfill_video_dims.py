"""Fill in videos.width / videos.height for rows ingested before those columns.

Detection boxes are stored in the video's native pixel space. The search API
needs the frame size to convert them into fractions of the frame, which is what
lets the UI draw a box over a scaled thumbnail. Rows ingested before the columns
existed have NULL dimensions, so their matches come back without a box.

This reads the size straight from each video file's header — it does not decode
frames and does not re-run the pipeline, so it takes about a second for a whole
library.

Usage (inside the container, which is where the demo database lives):

    docker compose exec backend sh -c "cd /app && PYTHONPATH=. python scripts/backfill_video_dims.py"
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


def main() -> int:
    import cv2

    from app.database import get_conn, init_db

    init_db()  # ensure the width/height columns exist

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, filename, path FROM videos "
            "WHERE width IS NULL OR width = 0 OR height IS NULL OR height = 0"
        ).fetchall()

    if not rows:
        print("Nothing to backfill — every video already has its dimensions.")
        return 0

    fixed = skipped = 0
    for r in rows:
        path = r["path"]
        # Live/stream rows hold a URL, not a local file; there is nothing to probe.
        if not isinstance(path, str) or path.split("://", 1)[0] in (
                "http", "https", "rtsp", "rtmp"):
            print(f"  skip  {r['filename']}: not a local file")
            skipped += 1
            continue
        if not os.path.exists(path):
            print(f"  skip  {r['filename']}: file missing")
            skipped += 1
            continue

        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print(f"  skip  {r['filename']}: cannot open")
            skipped += 1
            continue
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        cap.release()

        if not (w and h):
            print(f"  skip  {r['filename']}: no dimensions in header")
            skipped += 1
            continue

        with get_conn() as conn:
            conn.execute("UPDATE videos SET width = ?, height = ? WHERE id = ?",
                         (w, h, r["id"]))
        print(f"  ok    {r['filename']}: {w}x{h}")
        fixed += 1

    print(f"\nBackfilled {fixed} video(s), skipped {skipped}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
