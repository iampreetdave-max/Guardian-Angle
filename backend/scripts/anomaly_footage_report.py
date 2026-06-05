"""Run every clip in test_clips/ through the full anomaly pipeline and print a
per-clip report: which anomaly class(es) fired, at what confidence, plus a
pass/fail against the expected class for the folder.

Run from backend/:  python scripts/anomaly_footage_report.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ["VISIONSCAN_DATA_DIR"] = tempfile.mkdtemp(prefix="visionscan_footage_")
os.environ["VISIONSCAN_SEED_DEMO_USERS"] = "false"

from app.database import get_conn, init_db
from app.services.pipeline import process_video

CLIPS_DIR = Path(__file__).resolve().parents[2] / "test_clips"

# Folder -> the anomaly class(es) we'd consider a correct detection.
EXPECTED = {
    "fire": {"fire", "smoke"},
    "smoke": {"smoke", "fire"},
    "accident": {"accident"},
    "weapon": {"weapon"},
    "violence": {"violence"},
    "normal": set(),  # control: ideally nothing high-confidence
}


def ingest(path: Path, camera: str) -> int:
    with get_conn() as conn:
        vid = conn.execute(
            "INSERT INTO videos (filename, path, camera_id, status) "
            "VALUES (?, ?, ?, 'pending')",
            (path.name, str(path), camera),
        ).lastrowid
    process_video(vid)
    return vid


def events_for(video_id: int) -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT type, confidence, source, peak_count FROM anomaly_events "
            "WHERE video_id = ? ORDER BY confidence DESC", (video_id,))]


def main() -> None:
    init_db()
    categories = sys.argv[1:] or list(EXPECTED)
    rows = []
    for cat in categories:
        folder = CLIPS_DIR / cat
        clips = sorted(p for p in folder.glob("*.*") if p.suffix.lower() in
                       {".webm", ".ogv", ".mp4", ".mkv", ".mov", ".avi"})
        if not clips:
            print(f"[skip] no clips in test_clips/{cat} — run test_clips/fetch_all.py")
            continue
        for clip in clips:
            print(f"… ingesting {cat}/{clip.name}")
            vid = ingest(clip, f"CAM-{cat.upper()}")
            evs = events_for(vid)
            fired = {e["type"] for e in evs}
            top = max((e["confidence"] for e in evs), default=0.0)
            expected = EXPECTED.get(cat, set())
            if cat == "normal":
                ok = not any(e["confidence"] >= 0.70 for e in evs)
            else:
                ok = bool(fired & expected)
            rows.append((cat, clip.name, fired, top, ok, evs))

    print("\n" + "=" * 78)
    print(f"{'category':<10}{'clip':<40}{'fired':<22}{'top':>5}  ok")
    print("-" * 78)
    passes = 0
    for cat, name, fired, top, ok, _ in rows:
        fireds = ",".join(sorted(fired)) or "—"
        print(f"{cat:<10}{name[:38]:<40}{fireds:<22}{top:>5.2f}  {'PASS' if ok else 'FAIL'}")
        passes += ok
    print("-" * 78)
    print(f"{passes}/{len(rows)} clips matched expectation "
          f"(normal = no high-confidence event).")
    # Detail for any miss.
    for cat, name, fired, top, ok, evs in rows:
        if not ok:
            print(f"\n  MISS {cat}/{name}: events = {evs}")


if __name__ == "__main__":
    main()
