"""Tracking assigns per-video ids from already-stored detections.

Runs against the throwaway database conftest.py points the app at, so it never
touches the demo library.
"""
from __future__ import annotations

import pytest

from app.core import tracking
from app.database import get_conn


def _make_video(camera_id: str, boxes_per_frame: list[list[tuple]], gap: float = 0.5) -> int:
    """Insert a video whose frames hold the given (label, x1, y1, x2, y2) boxes."""
    with get_conn() as conn:
        vid = conn.execute(
            "INSERT INTO videos (filename, path, camera_id, status, width, height) "
            "VALUES (?, ?, ?, 'ready', 640, 480)",
            (f"{camera_id}.mp4", f"/tmp/{camera_id}.mp4", camera_id),
        ).lastrowid
        for i, boxes in enumerate(boxes_per_frame):
            fid = conn.execute(
                "INSERT INTO frames (video_id, frame_number, timestamp_sec, thumbnail_path) "
                "VALUES (?, ?, ?, ?)",
                (vid, i, round(i * gap, 2), f"/tmp/{camera_id}_{i}.jpg"),
            ).lastrowid
            for label, x1, y1, x2, y2 in boxes:
                conn.execute(
                    "INSERT INTO detections (frame_id, label, confidence, x1, y1, x2, y2) "
                    "VALUES (?, ?, 0.9, ?, ?, ?, ?)",
                    (fid, label, x1, y1, x2, y2),
                )
    return vid


def _walker(steps: int, x0: float = 50.0, label: str = "person") -> list[list[tuple]]:
    """One object drifting slowly to the right, one box per frame."""
    return [[(label, x0 + 6 * i, 100.0, x0 + 46 + 6 * i, 260.0)] for i in range(steps)]


def _track_ids(video_id: int) -> list[int]:
    with get_conn() as conn:
        return [r["track_id"] for r in conn.execute(
            "SELECT d.track_id FROM detections d JOIN frames f ON f.id = d.frame_id "
            "WHERE f.video_id = ? ORDER BY d.id", (video_id,))]


def test_tracker_state_never_leaks_between_videos(monkeypatch):
    """Each video must get its own tracker AND its own id space.

    A shared tracker would carry ids (and Kalman state) from one camera into the
    next, so all 16 cameras would share one continuous numbering.
    """
    built = []
    real = tracking._new_tracker
    monkeypatch.setattr(tracking, "_new_tracker",
                        lambda lost: built.append(t := real(lost)) or t)

    a = _make_video("T-A", _walker(4))
    b = _make_video("T-B", _walker(4))  # identical geometry: worst case for a leak
    tracking.assign_tracks(a)
    n_after_a = len(built)
    tracking.assign_tracks(b)

    # a fresh tracker object per video, never reused
    assert len(built) > n_after_a
    assert len({id(t) for t in built}) == len(built)

    # both videos number their objects from 1 — no shared counter
    assert set(_track_ids(a)) == {1}
    assert set(_track_ids(b)) == {1}
    assert tracking.track_summary(a)["distinct_objects"] == 1
    assert tracking.track_summary(b)["distinct_objects"] == 1

    # and tracking B did not disturb A
    assert _track_ids(a) == [1, 1, 1, 1]


def test_video_without_detections_returns_empty_summary():
    """No detections (or no frames at all) must degrade, not raise."""
    empty = _make_video("T-EMPTY", [[], [], []])
    stats = tracking.assign_tracks(empty)
    assert stats["distinct_objects"] == 0

    s = tracking.track_summary(empty)
    assert s["video_id"] == empty
    assert s["camera_id"] == "T-EMPTY"
    assert s["total_detections"] == 0
    assert s["distinct_objects"] == 0
    assert s["by_label"] == {}
    assert s["tracks"] == []
    assert s["tracking_quality"] in {"good", "degraded", "poor"}

    # a video id that does not exist at all is also survivable
    ghost = tracking.track_summary(10**9)
    assert ghost["distinct_objects"] == 0 and ghost["tracks"] == []


def test_repeated_assignment_is_idempotent():
    vid = _make_video("T-IDEM", _walker(5))
    tracking.assign_tracks(vid)
    first = _track_ids(vid)
    tracking.assign_tracks(vid)
    assert _track_ids(vid) == first


def test_classes_do_not_share_ids_and_paths_are_normalized():
    """A person and a car in overlapping boxes must stay separate objects."""
    frames = [[("person", 100.0, 100.0, 160.0, 300.0),
               ("car", 90.0, 120.0, 300.0, 280.0)] for _ in range(4)]
    vid = _make_video("T-MIX", frames)
    tracking.assign_tracks(vid)
    s = tracking.track_summary(vid)

    assert s["by_label"] == {"person": 1, "car": 1}
    assert s["distinct_objects"] == 2
    for tr in s["tracks"]:
        assert tr["n_frames"] == 4
        assert tr["duration_sec"] == pytest.approx(1.5)
        # centroids are fractions of the 640x480 frame, never pixels
        assert all(0.0 <= p["cx"] <= 1.0 and 0.0 <= p["cy"] <= 1.0 for p in tr["path"])
        assert [p["t"] for p in tr["path"]] == sorted(p["t"] for p in tr["path"])


def test_endpoint_computes_on_demand(client, auth_headers):
    vid = _make_video("T-API", _walker(4))
    r = client.get(f"/api/videos/{vid}/tracks", headers=auth_headers["officer"])
    assert r.status_code == 200
    body = r.json()
    assert body["camera_id"] == "T-API"
    assert body["distinct_objects"] == 1
    assert body["total_detections"] == 4
    assert body["fps_estimate"] == pytest.approx(2.0)
    assert client.get(f"/api/videos/{10**9}/tracks",
                      headers=auth_headers["officer"]).status_code == 404
