"""Assign detections.track_id for every ready video.

Reads only rows the ingest pipeline already wrote: no video is decoded and no
model runs, so this is safe to re-run at any time. Each video is re-tracked from
scratch (its old track ids are cleared first), which makes the script
idempotent: running it twice produces the same ids.

Usage (inside the container, which is where the demo database lives):

    docker compose exec backend sh -c "cd /app && PYTHONPATH=. python scripts/backfill_tracks.py"
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


def main() -> int:
    from app.core.tracking import assign_tracks, track_summary
    from app.database import get_conn, init_db

    init_db()  # ensure the track_id column exists

    with get_conn() as conn:
        videos = conn.execute(
            "SELECT id, camera_id, filename FROM videos WHERE status = 'ready' "
            "ORDER BY camera_id, id"
        ).fetchall()

    if not videos:
        print("No ready videos.")
        return 0

    print(f"{'camera':<8} {'fps':>5} {'quality':<9} {'det':>5} {'trk':>5} "
          f"{'objects':>7} {'peak':>5} {'frag':>5}  top labels (distinct objects)")
    print("-" * 104)

    tot_det = tot_trk = tot_obj = tot_peak = 0
    for v in videos:
        stats = assign_tracks(v["id"])
        summary = track_summary(v["id"])
        peak = _peak_occupancy(v["id"])
        top = ", ".join(f"{k} {n}" for k, n in list(summary["by_label"].items())[:5])
        obj = stats["distinct_objects"]
        print(f"{v['camera_id']:<8} {summary['fps_estimate']:>5.1f} "
              f"{summary['tracking_quality']:<9} {stats['detections']:>5} "
              f"{stats['tracked']:>5} {obj:>7} {peak:>5} "
              f"{obj / peak if peak else 0:>4.1f}x  {top}")
        tot_det += stats["detections"]
        tot_trk += stats["tracked"]
        tot_obj += obj
        tot_peak += peak

    print("-" * 104)
    print(f"{'TOTAL':<8} {'':>5} {'':<9} {tot_det:>5} {tot_trk:>5} {tot_obj:>7} "
          f"{tot_peak:>5} {tot_obj / tot_peak if tot_peak else 0:>4.1f}x")

    dropped = tot_det - tot_trk
    if dropped:
        print(f"\n{dropped} detection(s) ({dropped / tot_det:.1%}) matched no track "
              f"and keep a NULL track_id.")
    if tot_obj:
        print(f"\nMean sightings per object: {tot_trk / tot_obj:.1f}.")
        print("peak = most objects visible in any single keyframe, which is a HARD "
              "lower bound on\ndistinct objects. frag = objects / peak. Some of that "
              "ratio is real throughput (people\ndo walk through a scene), but at "
              "~2 fps most of it is one object breaking into several\ntracks. Read "
              "these counts as an upper bound on distinct objects, not a census.")
    return 0


def _peak_occupancy(video_id: int) -> int:
    """Most detections in any one keyframe: the floor for distinct objects."""
    from app.database import get_conn

    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(n) m FROM (SELECT COUNT(*) n FROM detections d "
            "JOIN frames f ON f.id = d.frame_id WHERE f.video_id = ? "
            "GROUP BY d.frame_id)", (video_id,)
        ).fetchone()
    return row["m"] or 0


if __name__ == "__main__":
    raise SystemExit(main())
