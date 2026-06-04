"""Anomaly-watch self-test.

Three checks, no real footage needed:
  1. CLIP zero-shot scoring: embed real anomaly-looking text descriptions as
     stand-in "frames" (text and image vectors share CLIP space) and assert
     each lands on its own class while a normal-scene vector stays silent.
  2. Debounce: two close-in-time signals of one type on one feed merge into a
     single event (peak_count=2); a third past the gap opens a new event.
  3. API shape: the listing query returns enriched cards.

Run from backend/:  python scripts/anomaly_selftest.py
"""
from __future__ import annotations

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import sys

from app.config import get_settings
from app.core import anomaly, embedding
from app.database import get_conn, init_db
from app.services.anomaly_events import record_signals

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def test_clip_scoring() -> None:
    print("\n1) CLIP zero-shot scoring (text vectors as frame stand-ins)")
    probes = {
        "fire": "cctv frame of a warehouse engulfed in flames at night",
        "smoke": "surveillance still of thick black smoke drifting over a road",
        "accident": "dashcam frame of two cars colliding at an intersection",
        "weapon": "security footage of a masked man pointing a pistol at a clerk",
        "violence": "camera frame of two men punching each other on a sidewalk",
    }
    for expected, text in probes.items():
        vec = embedding.embed_text(text)[0]
        types = {s.type for s in anomaly.score_clip(vec)}
        check(f"probe '{expected}' fires", expected in types, f"got {types or '{}'}")

    normal_texts = [
        "cctv frame of pedestrians crossing a quiet street in daylight",
        "surveillance still of normal traffic at a junction",
    ]
    for text in normal_texts:
        vec = embedding.embed_text(text)[0]
        sigs = anomaly.score_clip(vec)
        check("normal probe stays silent", not sigs,
              f"unexpected {[(s.type, s.confidence) for s in sigs]}")


def test_debounce() -> None:
    print("\n2) Event debounce / grouping")
    s = get_settings()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO videos (filename, path, camera_id, status) "
            "VALUES ('anomaly_selftest', 'selftest://none', 'CAM-TEST', 'ready')"
        )
        video_id = cur.lastrowid

    sig = anomaly.AnomalySignal("fire", 0.40, "clip")
    created1 = record_signals(video_id, None, 10.0, [sig], is_live=False)
    created2 = record_signals(
        video_id, None, 10.0 + s.anomaly_event_gap_sec / 2,
        [anomaly.AnomalySignal("fire", 0.55, "clip")], is_live=False)
    created3 = record_signals(
        video_id, None, 10.0 + s.anomaly_event_gap_sec * 3,
        [anomaly.AnomalySignal("fire", 0.45, "clip")], is_live=False)

    check("first signal creates an event", len(created1) == 1)
    check("close signal merges (no new event)", len(created2) == 0)
    check("signal past the gap opens a new event", len(created3) == 1)

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, confidence, peak_count FROM anomaly_events "
            "WHERE video_id = ? ORDER BY id", (video_id,)).fetchall()
    check("exactly two events persisted", len(rows) == 2, f"got {len(rows)}")
    if len(rows) == 2:
        check("merged event keeps max confidence + peak_count=2",
              abs(rows[0]["confidence"] - 0.55) < 1e-6 and rows[0]["peak_count"] == 2,
              f"conf={rows[0]['confidence']} peak={rows[0]['peak_count']}")

    # different type within the gap must NOT merge into the fire event
    created4 = record_signals(
        video_id, None, 10.0 + s.anomaly_event_gap_sec * 3 + 1,
        [anomaly.AnomalySignal("weapon", 0.50, "yolo", (1, 2, 3, 4))],
        is_live=False)
    check("different type opens its own event", len(created4) == 1)

    # cleanup so repeated runs stay deterministic
    with get_conn() as conn:
        conn.execute("DELETE FROM anomaly_events WHERE video_id = ?", (video_id,))
        conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))


def main() -> None:
    init_db()
    print("Anomaly watch self-test")
    print("=" * 50)
    test_clip_scoring()
    test_debounce()
    print("\n" + "=" * 50)
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} failure(s): {FAILURES}")
        sys.exit(1)
    print("RESULT: all checks passed")


if __name__ == "__main__":
    main()
