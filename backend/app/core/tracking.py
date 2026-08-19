"""Multi-object tracking over detections the ingest pipeline already stored.

Nothing here decodes video or runs a model. It reads `detections` joined to
`frames`, replays them through ByteTrack in timestamp order, and writes the
tracker ids back into `detections.track_id`. That makes it re-runnable and
completely additive: if it fails, the detection pipeline is untouched.

Tuning for keyframes, not video
-------------------------------
ByteTrack defaults assume ~30 fps. Our keyframes land at ~2 fps (median gap
0.47 s across the demo library, but 5 s on the sparsest camera), which breaks
two assumptions:

* `lost_track_buffer` is counted in FRAMES and internally scaled by
  `frame_rate / 30`, so any fixed frame count means a different amount of wall
  time per camera. We think in seconds instead: keep `frame_rate=30` (which
  makes that scale factor exactly 1) and derive the buffer from the measured
  keyframe gap of each camera. See `_lost_frames`.
* IoU between consecutive boxes is small, because half a second is enough for a
  walking person to clear their own width. `minimum_matching_threshold` is
  relaxed accordingly.

Both are env-overridable: the right values depend on the real cadence of a
camera and how fast things move in its field of view, which no default knows.
"""
from __future__ import annotations

import os
from statistics import median

import numpy as np
import supervision as sv
from supervision.detection.utils import box_iou_batch
from supervision.tracker.byte_tracker import matching

from ..database import get_conn

# How long a track may go unseen and still be re-claimed, in SECONDS of wall
# clock (converted to keyframes per camera). Too short fragments one object into
# many; too long lets a departed object adopt a newcomer.
LOST_SECONDS = float(os.getenv("VISIONSCAN_TRACK_LOST_SEC", "3.0"))

# ByteTrack matching cost is `1 - IoU * confidence`, and a match is accepted
# when that cost is <= this threshold. The 0.8 default needs IoU*conf >= 0.2,
# which almost nothing clears at 2 fps. 0.95 needs IoU*conf >= 0.05.
MATCH_THRESHOLD = float(os.getenv("VISIONSCAN_TRACK_MATCH_THRESH", "0.95"))

# Below this confidence ByteTrack will not start a new track (it may still
# extend an existing one). Stored detections all sit above 0.35 today, so this
# is effectively off; it exists so a lower ingest threshold cannot spawn junk.
ACTIVATION_CONF = float(os.getenv("VISIONSCAN_TRACK_MIN_CONF", "0.25"))

# Cost ceiling when mapping a tracker output back onto the detection row that
# produced it — see `_map_rows_to_tracks`. Cost is 1 - IoU, so 0.99 accepts any
# overlap at all. This is a bookkeeping step, not an association decision.
REMAP_MAX_COST = float(os.getenv("VISIONSCAN_TRACK_REMAP_COST", "0.99"))

_DET_SQL = """
SELECT d.id, d.label, d.confidence, d.x1, d.y1, d.x2, d.y2, f.timestamp_sec
FROM detections d JOIN frames f ON f.id = d.frame_id
WHERE f.video_id = ? ORDER BY f.timestamp_sec, d.id
"""


def _median_gap(times: list[float]) -> float:
    """Median seconds between consecutive keyframes (0.0 if fewer than two)."""
    gaps = [b - a for a, b in zip(times, times[1:]) if b > a]
    return median(gaps) if gaps else 0.0


def _lost_frames(gap: float) -> int:
    """Seconds of tolerated absence -> keyframes, for this camera cadence."""
    return max(1, round(LOST_SECONDS / gap)) if gap > 0 else 1


def _new_tracker(lost_frames: int) -> sv.ByteTrack:
    """Build a tracker. Isolated so tests can prove one is made per video."""
    return sv.ByteTrack(
        track_activation_threshold=ACTIVATION_CONF,
        minimum_matching_threshold=MATCH_THRESHOLD,
        # frame_rate is only ever used as the `frame_rate / 30` scale on
        # lost_track_buffer, so pinning it to 30 makes the buffer mean exactly
        # what we computed: N keyframes.
        frame_rate=30,
        lost_track_buffer=lost_frames,
        # One sighting is enough to open a track. At 2 fps, demanding two
        # consecutive frames would silently discard everything that crosses the
        # scene quickly, which is most of the traffic footage.
        minimum_consecutive_frames=1,
    )


def _to_detections(rows: list, class_id: int) -> sv.Detections:
    """Stored boxes -> sv.Detections, carrying the row id through as data."""
    if not rows:
        return sv.Detections(
            xyxy=np.empty((0, 4), dtype=np.float32),
            confidence=np.empty(0, dtype=np.float32),
            class_id=np.empty(0, dtype=int),
            data={"row": np.empty(0, dtype=int)},
        )
    return sv.Detections(
        xyxy=np.array([[r["x1"], r["y1"], r["x2"], r["y2"]] for r in rows],
                      dtype=np.float32),
        confidence=np.array([r["confidence"] for r in rows], dtype=np.float32),
        class_id=np.full(len(rows), class_id, dtype=int),
        data={"row": np.array([r["id"] for r in rows], dtype=int)},
    )


def _live(tracker: sv.ByteTrack) -> list:
    """Tracks holding a detection from the frame just fed to `tracker`.

    We read `tracked_tracks` rather than what `update_with_tensors` returns,
    because that return value is filtered by `STrack.is_activated`, which
    `STrack.activate` only ever sets on frame 1 of the video — a track born on
    any later frame is withheld until its SECOND sighting. On 30 fps video that
    costs one frame; on our ~2 fps keyframes it dropped every object's first
    appearance and every object seen exactly once, which was 38% of all stored
    detections. `minimum_consecutive_frames=1` already declares that one
    sighting is enough, and supervision assigns `external_track_id` at that
    moment, so these ids are real and complete.
    """
    return [t for t in tracker.tracked_tracks if t.external_track_id is not None]


def _map_rows_to_tracks(dets: sv.Detections, tracks: list) -> list[tuple[int, int]]:
    """Pair each detection row with the tracker id that consumed it.

    `ByteTrack.update_with_detections` does this itself, but re-matches the raw
    boxes against the Kalman-SMOOTHED track boxes at IoU >= 0.5 and silently
    drops whatever falls short. At 2 fps the smoothing correction is large, so
    that discarded ~42% of our detections even though the tracker pool showed
    every one of them had extended a track. We run the same Hungarian pairing
    with a gate loose enough to be pure bookkeeping.
    """
    if not len(dets) or not tracks:
        return []
    track_boxes = np.array([t.tlbr for t in tracks], dtype=np.float32)
    cost = 1.0 - box_iou_batch(dets.xyxy.astype(np.float32), track_boxes)
    matches, _, _ = matching.linear_assignment(cost, REMAP_MAX_COST)
    rows = dets.data["row"]
    return [(int(rows[i]), int(tracks[j].external_track_id)) for i, j in matches]


def assign_tracks(video_id: int) -> dict:
    """(Re)assign `detections.track_id` for one video. Idempotent."""
    with get_conn() as conn:
        rows = conn.execute(_DET_SQL, (video_id,)).fetchall()
        conn.execute(
            "UPDATE detections SET track_id = NULL WHERE frame_id IN "
            "(SELECT id FROM frames WHERE video_id = ?)",
            (video_id,),
        )
        if not rows:
            return {"video_id": video_id, "detections": 0, "tracked": 0,
                    "distinct_objects": 0, "by_label": {}, "lost_frames": 0}

        times = sorted({float(r["timestamp_sec"]) for r in rows})
        lost = _lost_frames(_median_gap(times))

        by_frame: dict[float, list] = {t: [] for t in times}
        for r in rows:
            by_frame[float(r["timestamp_sec"])].append(r)

        labels = sorted({r["label"] for r in rows})
        # One tracker per label. ByteTrack in supervision 0.25 matches purely on
        # box geometry and ignores class_id, so a single tracker will happily
        # hand the id of a departing car to the pedestrian who walks into its
        # box. Splitting by label is what makes the class actually bind.
        # Fresh instances on every call: leaking tracker state across videos
        # would merge all 16 cameras into one id space.
        trackers = {lb: _new_tracker(lost) for lb in labels}
        class_ids = {lb: i for i, lb in enumerate(labels)}

        assigned: dict[int, int] = {}          # detection row id -> track id
        seq: dict[tuple[str, int], int] = {}   # (label, tracker id) -> track id

        for t in times:
            frame_rows = by_frame[t]
            for label, tracker in trackers.items():
                mine = [r for r in frame_rows if r["label"] == label]
                # Every tracker is stepped on every keyframe, even when its
                # label is absent from it: the update call is what ages lost
                # tracks. Skip it and a track survives an arbitrary absence.
                dets = _to_detections(mine, class_ids[label])
                tracker.update_with_tensors(
                    np.hstack((dets.xyxy, dets.confidence[:, np.newaxis])))
                for row_id, tid in _map_rows_to_tracks(dets, _live(tracker)):
                    assigned[row_id] = seq.setdefault(
                        (label, tid), len(seq) + 1)

        conn.executemany(
            "UPDATE detections SET track_id = ? WHERE id = ?",
            [(tid, did) for did, tid in assigned.items()],
        )

    by_label: dict[str, int] = {}
    for label, _tid in seq:
        by_label[label] = by_label.get(label, 0) + 1
    return {
        "video_id": video_id,
        "detections": len(rows),
        "tracked": len(assigned),
        "distinct_objects": len(seq),
        "by_label": dict(sorted(by_label.items(), key=lambda kv: -kv[1])),
        "lost_frames": lost,
    }


def track_summary(video_id: int) -> dict:
    """Per-track paths and counts for one video, shaped like the GET response.

    Fails soft: an unknown or detection-free video yields an empty-but-valid
    payload rather than raising.
    """
    with get_conn() as conn:
        vid = conn.execute(
            "SELECT camera_id, width, height FROM videos WHERE id = ?", (video_id,)
        ).fetchone()
        total = conn.execute(
            "SELECT COUNT(*) n FROM detections d JOIN frames f ON f.id = d.frame_id "
            "WHERE f.video_id = ?", (video_id,)
        ).fetchone()["n"]
        times = [r["timestamp_sec"] for r in conn.execute(
            "SELECT timestamp_sec FROM frames WHERE video_id = ? "
            "ORDER BY timestamp_sec", (video_id,))]
        rows = conn.execute(
            _DET_SQL.replace("SELECT d.id,", "SELECT d.id, d.track_id,").replace(
                "WHERE f.video_id = ?", "WHERE f.video_id = ? AND d.track_id IS NOT NULL"),
            (video_id,),
        ).fetchall()

    gap = _median_gap(times)
    # Boxes are stored in native pixels; everything crossing the API is a
    # fraction of the frame. Without the source size we cannot convert, so the
    # path is left empty rather than emitted wrong.
    w = (vid["width"] or 0) if vid else 0
    h = (vid["height"] or 0) if vid else 0

    tracks: dict[int, dict] = {}
    for r in rows:
        tr = tracks.setdefault(r["track_id"], {
            "track_id": r["track_id"], "label": r["label"], "n_frames": 0,
            "first_seen_sec": r["timestamp_sec"], "last_seen_sec": r["timestamp_sec"],
            "best_confidence": 0.0, "path": [],
        })
        tr["n_frames"] += 1
        tr["last_seen_sec"] = max(tr["last_seen_sec"], r["timestamp_sec"])
        tr["first_seen_sec"] = min(tr["first_seen_sec"], r["timestamp_sec"])
        tr["best_confidence"] = max(tr["best_confidence"], round(r["confidence"], 3))
        if w and h:
            tr["path"].append({
                "t": round(r["timestamp_sec"], 2),
                "cx": round(min(max((r["x1"] + r["x2"]) / 2 / w, 0.0), 1.0), 4),
                "cy": round(min(max((r["y1"] + r["y2"]) / 2 / h, 0.0), 1.0), 4),
            })

    out = []
    for tr in tracks.values():
        tr["path"].sort(key=lambda p: p["t"])
        tr["first_seen_sec"] = round(tr["first_seen_sec"], 2)
        tr["last_seen_sec"] = round(tr["last_seen_sec"], 2)
        tr["duration_sec"] = round(tr["last_seen_sec"] - tr["first_seen_sec"], 2)
        out.append(tr)
    out.sort(key=lambda t: (t["first_seen_sec"], t["track_id"]))

    by_label: dict[str, int] = {}
    for tr in out:
        by_label[tr["label"]] = by_label.get(tr["label"], 0) + 1

    # Quality must reflect the tracking we actually achieved, not just how often
    # we sampled. Keyframe cadence sets the ceiling, but it is only half the
    # story: on a highway a car clears its own length between two 0.46s frames,
    # so IoU association fails and the track shatters into singletons even
    # though the cadence looks "good". Reporting "good" there would flatter a
    # number the footage does not support.
    #
    # Fragmentation = the share of detections stranded in tracks seen at most
    # twice. High fragmentation caps the grade regardless of cadence.
    stranded = sum(t["n_frames"] for t in out if t["n_frames"] <= 2)
    frag = (stranded / total) if total else 0.0

    if gap <= 0:
        quality = "poor"          # one keyframe or none: nothing to track across
    elif gap <= 0.6:
        quality = "good"
    elif gap <= 1.5:
        quality = "degraded"
    else:
        quality = "poor"

    if frag >= 0.40:
        quality = "poor"
    elif frag >= 0.20 and quality == "good":
        quality = "degraded"

    return {
        "video_id": video_id,
        "camera_id": vid["camera_id"] if vid else None,
        "total_detections": total,
        "distinct_objects": len(out),
        "by_label": dict(sorted(by_label.items(), key=lambda kv: -kv[1])),
        "fps_estimate": round(1.0 / gap, 1) if gap else 0.0,
        "tracking_quality": quality,
        # Share of detections stranded in tracks seen at most twice — the honest
        # reason a grade was capped. Surfaced so the UI can explain itself.
        "fragmentation": round(frag, 3),
        "tracks": out,
    }
