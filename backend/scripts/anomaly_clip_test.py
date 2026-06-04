"""Real-footage anomaly check: run actual fire + normal clips from test_clips/
through the FULL ingest pipeline (keyframes -> CLIP -> YOLO -> anomaly watch)
against a throwaway data dir, then assert events fired for fire and stayed
quiet (or near-quiet) for the normal control.

Run from backend/:  python scripts/anomaly_clip_test.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ["VISIONSCAN_DATA_DIR"] = tempfile.mkdtemp(prefix="visionscan_anomtest_")
os.environ["VISIONSCAN_SEED_DEMO_USERS"] = "false"

from app.database import get_conn, init_db
from app.services.pipeline import process_video

CLIPS_DIR = Path(__file__).resolve().parents[2] / "test_clips"


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
    fire_clips = sorted((CLIPS_DIR / "fire").glob("*.*"))
    normal_clips = sorted((CLIPS_DIR / "normal").glob("*.*"))
    if not fire_clips or not normal_clips:
        print("test_clips/fire or test_clips/normal missing — run the clip downloader first")
        sys.exit(2)

    failures = []

    print(f"Ingesting FIRE clip: {fire_clips[0].name}")
    fire_vid = ingest(fire_clips[0], "CAM-FIRE-TEST")
    fire_events = events_for(fire_vid)
    print(f"  events: {fire_events}")
    if not any(e["type"] in ("fire", "smoke") for e in fire_events):
        failures.append("fire clip produced no fire/smoke event")

    print(f"Ingesting NORMAL clip: {normal_clips[0].name}")
    norm_vid = ingest(normal_clips[0], "CAM-NORMAL-TEST")
    norm_events = events_for(norm_vid)
    print(f"  events: {norm_events}")
    # Real street footage may produce an occasional borderline event; what we
    # cannot tolerate is the control firing as much as the positive.
    if len(norm_events) > len(fire_events):
        failures.append("normal clip fired more events than the fire clip")
    high_conf_norm = [e for e in norm_events if e["confidence"] >= 0.70]
    if high_conf_norm:
        failures.append(f"normal clip produced high-confidence events: {high_conf_norm}")

    print("=" * 50)
    if failures:
        print(f"RESULT: {len(failures)} failure(s): {failures}")
        sys.exit(1)
    print("RESULT: real-footage anomaly check passed")


if __name__ == "__main__":
    main()
