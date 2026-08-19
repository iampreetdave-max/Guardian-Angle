"""Zone occupancy + line crossing, on a hand-built video in the temp test DB.

Boxes below are written in the fixture video's pixel space (100x100), so the
normalised coordinates the API speaks are just /100.
"""
from __future__ import annotations

import pytest

from app.core.zones import line_crossings, zone_analytics
from app.database import get_conn

FULL = [[0, 0], [1, 0], [1, 1], [0, 1]]          # whole frame
NOWHERE = [[0.9, 0.0], [1.0, 0.0], [1.0, 0.05]]  # top-right sliver, empty


def _add(conn, camera: str, dets):
    """dets = {timestamp: [(label, x1, y1, x2, y2, track_id), ...]} in pixels."""
    vid = conn.execute(
        "INSERT INTO videos (filename, path, camera_id, width, height, status) "
        "VALUES (?, ?, ?, 100, 100, 'ready')",
        (f"{camera}.mp4", f"/tmp/{camera}.mp4", camera),
    ).lastrowid
    for i, (ts, boxes) in enumerate(sorted(dets.items())):
        fid = conn.execute(
            "INSERT INTO frames (video_id, frame_number, timestamp_sec, "
            "thumbnail_path) VALUES (?, ?, ?, ?)",
            (vid, i, ts, f"{camera}_{i}.jpg"),
        ).lastrowid
        for label, x1, y1, x2, y2, tid in boxes:
            conn.execute(
                "INSERT INTO detections (frame_id, label, confidence, "
                "x1, y1, x2, y2, track_id) VALUES (?, ?, 0.9, ?, ?, ?, ?, ?)",
                (fid, label, x1, y1, x2, y2, tid),
            )
    return vid


@pytest.fixture(scope="module")
def video_ids():
    """Two videos: one with track ids, one without."""
    with get_conn() as conn:
        tracked = _add(conn, "TEST-ZONE", {
            # t=0: two people bottom-left area, one car right
            0.0: [("person", 10, 10, 20, 40, 1), ("person", 30, 20, 40, 50, 2),
                  ("car", 70, 30, 90, 60, 3)],
            # t=0.5: person 1 has walked right, person 2 gone
            0.5: [("person", 55, 10, 65, 40, 1), ("car", 70, 30, 90, 60, 3)],
            1.0: [("person", 80, 10, 90, 40, 1)],
        })
        untracked = _add(conn, "TEST-ZONE-NT", {
            0.0: [("person", 10, 10, 20, 40, None)],
            0.5: [("person", 12, 10, 22, 40, None)],
        })
    return tracked, untracked


def test_polygon_containing_everything(video_ids):
    r = zone_analytics(video_ids[0], FULL)
    assert [e["count"] for e in r["timeline"]] == [3, 2, 1]
    assert r["peak_occupancy"] == 3 and r["peak_at_sec"] == 0.0
    assert r["mean_occupancy"] == 2.0
    assert r["distinct_objects_entered"] == 3


def test_labels_filter(video_ids):
    r = zone_analytics(video_ids[0], FULL, labels=["person"])
    assert [e["count"] for e in r["timeline"]] == [2, 1, 1]
    assert r["distinct_objects_entered"] == 2


def test_polygon_containing_nothing(video_ids):
    r = zone_analytics(video_ids[0], NOWHERE)
    assert r["peak_occupancy"] == 0
    assert r["peak_at_sec"] is None
    assert r["mean_occupancy"] == 0.0
    assert [e["count"] for e in r["timeline"]] == [0, 0, 0]
    # 0, not None: tracking IS available here, nobody just ever entered
    assert r["distinct_objects_entered"] == 0


def test_bottom_centre_anchor_not_box_centre(video_ids):
    """A band that only the feet fall into: box centres would miss it."""
    band = [[0.0, 0.38], [1.0, 0.38], [1.0, 0.55], [0.0, 0.55]]
    r = zone_analytics(video_ids[0], band, labels=["person"])
    # feet at y=0.40 and y=0.50 are in; the box centres (0.25, 0.35) are not
    assert r["peak_occupancy"] == 2


def test_degenerate_polygon_rejected(client):
    for bad in ([[0.1, 0.1], [0.9, 0.9]],                    # only 2 points
                [[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]],        # collinear
                [[0.1, 0.1], [1.5, 0.5], [0.9, 0.9]]):       # out of range
        r = client.post("/api/videos/1/zone-analytics", json={"polygon": bad})
        assert r.status_code == 400, (bad, r.text)
    # core itself must fail soft rather than raise
    assert zone_analytics(1, [[0.0, 0.0], [1.0, 1.0]])["timeline"] == []


def test_line_crossed_once(video_ids):
    """Track 1 walks left->right across a vertical line at x=0.5.

    The line runs top->bottom, so "left of the direction vector" is the right
    of the screen: a left-to-right walker is right->left in line terms = "out".
    """
    r = line_crossings(video_ids[0], [[0.5, 0.0], [0.5, 1.0]], labels=["person"])
    assert len(r["events"]) == 1
    ev = r["events"][0]
    assert ev["track_id"] == 1 and ev["label"] == "person" and ev["t"] == 0.5
    assert ev["direction"] == "out"
    assert (r["crossings_in"], r["crossings_out"], r["net"]) == (0, 1, -1)
    # Same line drawn the other way flips the polarity.
    flipped = line_crossings(video_ids[0], [[0.5, 1.0], [0.5, 0.0]],
                             labels=["person"])
    assert flipped["events"][0]["direction"] == "in"
    assert (flipped["crossings_in"], flipped["net"]) == (1, 1)


def test_line_not_reached_is_not_a_crossing(video_ids):
    """A short line stub the track never passes through counts nothing."""
    r = line_crossings(video_ids[0], [[0.5, 0.8], [0.5, 1.0]], labels=["person"])
    assert r["events"] == [] and r["net"] == 0


def test_line_without_tracks_fails_soft(video_ids):
    r = line_crossings(video_ids[1], [[0.5, 0.0], [0.5, 1.0]])
    assert r["events"] == []
    assert (r["crossings_in"], r["crossings_out"], r["net"]) == (0, 0, 0)
    assert "track_id" in r["reason"]
    # and the zone route still works on the same video
    assert zone_analytics(video_ids[1], FULL)["distinct_objects_entered"] is None


def test_line_validation(client):
    for bad in ([[0.1, 0.1]], [[0.1, 0.1], [0.1, 0.1]],
                [[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]], [[0.1, 0.1], [2.0, 0.2]]):
        r = client.post("/api/videos/1/line-crossings", json={"line": bad})
        assert r.status_code == 400, (bad, r.text)


def test_route_end_to_end(client, video_ids):
    r = client.post(f"/api/videos/{video_ids[0]}/zone-analytics",
                    json={"polygon": FULL, "labels": ["person"]})
    assert r.status_code == 200
    assert r.json()["peak_occupancy"] == 2
    r = client.post(f"/api/videos/{video_ids[0]}/line-crossings",
                    json={"line": [[0.5, 0.0], [0.5, 1.0]]})
    assert r.status_code == 200 and r.json()["crossings_out"] == 1


def test_unknown_video_fails_soft():
    assert zone_analytics(999999, FULL)["timeline"] == []
    assert line_crossings(999999, [[0, 0], [1, 1]])["reason"]
