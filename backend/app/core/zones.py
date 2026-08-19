"""Zone occupancy and line-crossing counts over already-stored detections.

Nothing here re-runs a model or re-decodes video: every number comes from rows
the ingest pipeline already wrote (`detections` joined to `frames`), so these
features are purely additive and cannot disturb the detection path.

Anchor point
------------
A detection is "in the zone" when the **bottom-centre** of its box —
((x1+x2)/2, y2) — is inside the polygon. That is the object's ground-contact
point, which is what "standing in this area" actually means. The box centre
floats at chest/roof height and, on the elevated CCTV angles this system uses,
sits well *behind* where the person is really standing.

Coordinates
-----------
Boxes are stored in the video's native pixel space; everything crossing the API
is a 0..1 fraction of the frame (same convention as `match_bbox`). We normalise
the boxes with `videos.width/height` and test containment in fraction space.

ponytail: plain ray-casting instead of `sv.PolygonZone`. supervision's zone
wants a pixel polygon plus a `sv.Detections` object constructed per frame and
keeps its own trigger state; we already have the rows in SQL and need exactly
one predicate. Fifteen lines of stdlib beat rebuilding a supervision object 417
times. Same for the crossing test — a segment/segment orientation check is both
shorter and stricter than sv.LineZone's anchor bookkeeping.
"""
from __future__ import annotations

from collections import defaultdict

from ..database import get_conn

NO_TRACKS = (
    "no track_id on these detections — run object tracking for this video "
    "first; line crossing needs to follow the same object across frames"
)


# ---------------------------------------------------------------- geometry --
def _inside(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    """Ray casting (crossing number). Points exactly on an edge are undefined."""
    inside = False
    j = len(poly) - 1
    for i, (xi, yi) in enumerate(poly):
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _cross(ax, ay, bx, by, px, py) -> float:
    """2D cross product of (b-a) x (p-a). Sign = which side of a->b p lies on."""
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


# -------------------------------------------------------------------- data --
def _rows(conn, video_id: int, labels: list[str] | None):
    sql = (
        "SELECT f.id AS frame_id, f.timestamp_sec AS t, d.label, d.track_id, "
        "       d.x1, d.y1, d.x2, d.y2 "
        "FROM detections d JOIN frames f ON f.id = d.frame_id "
        "WHERE f.video_id = ?"
    )
    args: list = [video_id]
    if labels:
        sql += f" AND d.label IN ({','.join('?' * len(labels))})"
        args += labels
    return conn.execute(sql + " ORDER BY f.timestamp_sec, d.id", args).fetchall()


def _dims(conn, video_id: int) -> tuple[float, float] | None:
    v = conn.execute(
        "SELECT width, height FROM videos WHERE id = ?", (video_id,)
    ).fetchone()
    if not v or not v["width"] or not v["height"]:
        return None
    return float(v["width"]), float(v["height"])


def _anchor(r, w: float, h: float) -> tuple[float, float]:
    """Bottom-centre of the box, normalised to 0..1."""
    return ((r["x1"] + r["x2"]) / 2.0 / w, r["y2"] / h)


# ---------------------------------------------------------------- features --
def zone_analytics(
    video_id: int, polygon: list[list[float]], labels: list[str] | None = None
) -> dict:
    """Per-frame occupancy of a normalised polygon.

    Returns the full timeline (one entry per keyframe, including empty ones),
    peak occupancy and when it happened, and mean occupancy over all keyframes.
    `distinct_objects_entered` counts unique track ids ever inside, or is None
    when the detections carry no track ids.
    """
    poly = [(float(p[0]), float(p[1])) for p in polygon]
    empty = {
        "video_id": video_id,
        "peak_occupancy": 0,
        "peak_at_sec": None,
        "mean_occupancy": 0.0,
        "timeline": [],
        "distinct_objects_entered": None,
    }
    if len(poly) < 3:
        return empty

    with get_conn() as conn:
        dims = _dims(conn, video_id)
        if dims is None:  # unknown video, or dimensions never backfilled
            return empty
        w, h = dims
        frames = conn.execute(
            "SELECT id, timestamp_sec FROM frames WHERE video_id = ? "
            "ORDER BY timestamp_sec",
            (video_id,),
        ).fetchall()
        rows = _rows(conn, video_id, labels)

    counts: dict[int, int] = defaultdict(int)
    tracks: set[int] = set()
    any_track = False
    for r in rows:
        if r["track_id"] is not None:
            any_track = True
        x, y = _anchor(r, w, h)
        if _inside(x, y, poly):
            counts[r["frame_id"]] += 1
            if r["track_id"] is not None:
                tracks.add(r["track_id"])

    timeline = [{"t": round(f["timestamp_sec"], 2),
                 "count": counts.get(f["id"], 0)} for f in frames]
    if not timeline:
        return empty
    peak = max(timeline, key=lambda e: e["count"])
    return {
        "video_id": video_id,
        "peak_occupancy": peak["count"],
        "peak_at_sec": peak["t"] if peak["count"] else None,
        "mean_occupancy": round(
            sum(e["count"] for e in timeline) / len(timeline), 2),
        "timeline": timeline,
        "distinct_objects_entered": len(tracks) if any_track else None,
    }


def line_crossings(
    video_id: int, line: list[list[float]], labels: list[str] | None = None
) -> dict:
    """Directional crossing counts for a normalised line segment a->b.

    Each track's bottom-centre points are walked in time order; a step p1->p2
    that properly intersects the segment a->b is one crossing.

    Direction convention (image coordinates, y grows downward, so "left of the
    direction vector" is the side that looks *above* a left-to-right line):
        side(p) = sign( (b-a) x (p-a) );  side < 0 is left, side > 0 is right.
        "in"  = left -> right  (side goes negative -> positive)
        "out" = right -> left
    So for a horizontal line drawn left-to-right, "in" means moving downward on
    screen — flip the two endpoints to flip the polarity.

    Needs track ids. Without them this returns zeroed counts, an empty event
    list and a `reason`, never an error.

    ponytail: no hysteresis — every sign flip counts. At ~2 fps the stored boxes
    jitter, so a track sitting on the line can be counted more than once (seen
    on CAM-04: one car scored in/out/in over 2.2 s). Add a hysteresis band
    (ignore flips while |distance to line| < eps) if the real tracker's jitter
    shows up in the counts; tuning eps against noisy 2 fps boxes before then is
    guesswork.
    """
    out = {
        "video_id": video_id,
        "crossings_in": 0,
        "crossings_out": 0,
        "net": 0,
        "events": [],
        "reason": None,
    }
    if len(line) != 2 or tuple(line[0]) == tuple(line[1]):
        out["reason"] = "line needs two distinct points"
        return out
    (ax, ay), (bx, by) = [(float(p[0]), float(p[1])) for p in line]

    with get_conn() as conn:
        dims = _dims(conn, video_id)
        if dims is None:
            out["reason"] = "unknown video, or its frame size was never recorded"
            return out
        w, h = dims
        rows = _rows(conn, video_id, labels)

    paths: dict[int, list] = defaultdict(list)
    for r in rows:
        if r["track_id"] is not None:
            paths[r["track_id"]].append(r)
    if not paths:
        out["reason"] = NO_TRACKS
        return out

    events = []
    for tid, pts in paths.items():
        for prev, cur in zip(pts, pts[1:]):
            x1, y1 = _anchor(prev, w, h)
            x2, y2 = _anchor(cur, w, h)
            d1 = _cross(ax, ay, bx, by, x1, y1)
            d2 = _cross(ax, ay, bx, by, x2, y2)
            # Proper intersection only: the track must change sides AND the
            # line's endpoints must straddle the track step, so a track passing
            # beyond the end of a short line is not counted.
            if d1 * d2 >= 0:
                continue
            if _cross(x1, y1, x2, y2, ax, ay) * _cross(x1, y1, x2, y2, bx, by) >= 0:
                continue
            events.append({
                "track_id": tid,
                "label": cur["label"],
                "t": round(cur["t"], 2),
                "direction": "in" if d1 < 0 else "out",
            })

    events.sort(key=lambda e: (e["t"], e["track_id"]))
    out["events"] = events
    out["crossings_in"] = sum(1 for e in events if e["direction"] == "in")
    out["crossings_out"] = len(events) - out["crossings_in"]
    out["net"] = out["crossings_in"] - out["crossings_out"]
    return out
