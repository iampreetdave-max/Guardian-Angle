"""Closed-loop incident response — a live anomaly auto-spawns a geo-tagged case
and dispatches the nearest unit.

Exercises services/incident_loop.handle_new_event via record_signals(), the
same path the live capture loop hits. No models are loaded: we insert a videos
row tagged 'live' with an area and feed AnomalySignals directly.
"""
from __future__ import annotations

import os

import pytest

from app.config import get_settings
from app.core.anomaly import AnomalySignal
from app.database import get_conn
from app.services.anomaly_events import record_signals


def _make_live_feed(area: str = "Navrangpura") -> int:
    with get_conn() as conn:
        return conn.execute(
            "INSERT INTO videos (filename, path, camera_id, status, area) "
            "VALUES ('[LIVE] pytest', 'pytest://live', 'CAM-LOOP', 'live', ?)",
            (area,),
        ).lastrowid


def _cleanup(video_id: int) -> None:
    with get_conn() as conn:
        case_ids = [r["case_id"] for r in conn.execute(
            "SELECT DISTINCT case_id FROM anomaly_events "
            "WHERE video_id = ? AND case_id IS NOT NULL", (video_id,))]
        for cid in case_ids:
            conn.execute("DELETE FROM case_assignments WHERE case_id = ?", (cid,))
            conn.execute("DELETE FROM evidence WHERE case_id = ?", (cid,))
            conn.execute("DELETE FROM notifications WHERE case_id = ?", (cid,))
            conn.execute("DELETE FROM cases WHERE id = ?", (cid,))
        conn.execute("DELETE FROM anomaly_events WHERE video_id = ?", (video_id,))
        conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))


@pytest.fixture(autouse=True)
def _auto_case_on(monkeypatch):
    # The loop defaults ON, but pin it explicitly so an inherited env can't
    # flip the default tests below depend on.
    monkeypatch.setenv("VISIONSCAN_AUTO_CASE", "1")


def test_live_weapon_event_spawns_critical_case_and_dispatch():
    """A live 'weapon' detection in a tagged area -> critical AUTO case, the
    keyframe attached as evidence, case_id backfilled, and a DISPATCH
    notification to an officer."""
    video_id = _make_live_feed("Navrangpura")
    try:
        with get_conn() as conn:
            frame_id = conn.execute(
                "INSERT INTO frames (video_id, frame_number, timestamp_sec, "
                "thumbnail_path) VALUES (?, 0, 1.0, 'pytest/loop.jpg')",
                (video_id,),
            ).lastrowid

        created = record_signals(
            video_id, frame_id, 1.0,
            [AnomalySignal("weapon", 0.91, "clip+yolo")], is_live=True)
        assert len(created) == 1
        event_id = created[0]

        with get_conn() as conn:
            ev = conn.execute(
                "SELECT case_id FROM anomaly_events WHERE id = ?", (event_id,)
            ).fetchone()
            assert ev["case_id"] is not None, "case_id must be backfilled"
            case = conn.execute(
                "SELECT * FROM cases WHERE id = ?", (ev["case_id"],)
            ).fetchone()
            assert case is not None
            assert case["severity"] == "critical", case["severity"]
            assert case["priority"] == 1, case["priority"]
            assert case["title"] == "AUTO: WEAPON detected at Navrangpura"
            assert "91%" in case["description"]
            assert str(event_id) in case["description"]
            # keyframe attached as evidence
            ev_rows = conn.execute(
                "SELECT * FROM evidence WHERE case_id = ?", (case["id"],)
            ).fetchall()
            assert len(ev_rows) == 1 and ev_rows[0]["kind"] == "frame"
            assert ev_rows[0]["ref"] == str(frame_id)
            # dispatch notification exists, links to the case, high-signal text
            notif = conn.execute(
                "SELECT * FROM notifications WHERE case_id = ? AND type = 'dispatch'",
                (case["id"],),
            ).fetchone()
            assert notif is not None, "officer dispatch notification missing"
            assert "DISPATCH" in notif["message"]
            assert f"#{case['id']}" in notif["message"]
            assert notif["link"] == f"/?module=cases&case={case['id']}"
            # dispatched officer is auto-assigned to the case
            assigned = conn.execute(
                "SELECT user_id FROM case_assignments WHERE case_id = ?",
                (case["id"],),
            ).fetchone()
            assert assigned is not None
            assert assigned["user_id"] == notif["user_id"]
    finally:
        _cleanup(video_id)


def test_severity_mapping_fire_is_high():
    """Type->severity map: fire -> high (vs critical for armed/violent)."""
    video_id = _make_live_feed("Maninagar")
    try:
        created = record_signals(
            video_id, None, 1.0,
            [AnomalySignal("fire", 0.80, "clip")], is_live=True)
        with get_conn() as conn:
            ev = conn.execute(
                "SELECT case_id FROM anomaly_events WHERE id = ?", (created[0],)
            ).fetchone()
            case = conn.execute(
                "SELECT severity, title FROM cases WHERE id = ?", (ev["case_id"],)
            ).fetchone()
        assert case["severity"] == "high", case["severity"]
        assert case["title"] == "AUTO: FIRE detected at Maninagar"
    finally:
        _cleanup(video_id)


def test_dedupe_no_second_case_within_debounce_gap():
    """A grouped update (second signal within the gap merges onto the same
    event) must NOT spawn a second case; case_id stays put."""
    s = get_settings()
    video_id = _make_live_feed("Satellite")
    try:
        created1 = record_signals(
            video_id, None, 5.0,
            [AnomalySignal("fire", 0.75, "clip")], is_live=True)
        assert len(created1) == 1
        with get_conn() as conn:
            first_case = conn.execute(
                "SELECT case_id FROM anomaly_events WHERE id = ?", (created1[0],)
            ).fetchone()["case_id"]
        assert first_case is not None

        # Second signal within the debounce window merges (no new event),
        # so handle_new_event is not even re-invoked — but assert hard anyway.
        created2 = record_signals(
            video_id, None, 5.0 + s.anomaly_event_gap_sec / 2,
            [AnomalySignal("fire", 0.85, "clip")], is_live=True)
        assert len(created2) == 0, "merge should not open a new event"

        with get_conn() as conn:
            cases = conn.execute(
                "SELECT DISTINCT case_id FROM anomaly_events "
                "WHERE video_id = ? AND case_id IS NOT NULL", (video_id,)
            ).fetchall()
        assert len(cases) == 1, "exactly one auto-case for the merged event"
        assert cases[0]["case_id"] == first_case
    finally:
        _cleanup(video_id)


def test_untagged_feed_creates_no_case():
    """A live feed with no area can't be geo-located -> no auto-case, but the
    event is still recorded (Live Alerts panel keeps working)."""
    with get_conn() as conn:
        video_id = conn.execute(
            "INSERT INTO videos (filename, path, camera_id, status) "
            "VALUES ('[LIVE] noarea', 'pytest://noarea', 'CAM-NOAREA', 'live')"
        ).lastrowid
    try:
        created = record_signals(
            video_id, None, 1.0,
            [AnomalySignal("smoke", 0.78, "clip")], is_live=True)
        assert len(created) == 1
        with get_conn() as conn:
            ev = conn.execute(
                "SELECT case_id FROM anomaly_events WHERE id = ?", (created[0],)
            ).fetchone()
        assert ev["case_id"] is None, "untagged feed must not auto-create a case"
    finally:
        _cleanup(video_id)


def test_disabled_flag_creates_nothing(monkeypatch):
    """VISIONSCAN_AUTO_CASE off -> the loop no-ops: event recorded, no case."""
    monkeypatch.setenv("VISIONSCAN_AUTO_CASE", "false")
    video_id = _make_live_feed("Bopal")
    try:
        created = record_signals(
            video_id, None, 1.0,
            [AnomalySignal("weapon", 0.95, "clip")], is_live=True)
        assert len(created) == 1
        with get_conn() as conn:
            ev = conn.execute(
                "SELECT case_id FROM anomaly_events WHERE id = ?", (created[0],)
            ).fetchone()
        assert ev["case_id"] is None, "disabled flag must skip auto-case"
    finally:
        _cleanup(video_id)


def test_uploaded_event_not_live_no_case():
    """is_live=False (historical upload) never triggers the closed loop, even
    on a tagged feed."""
    video_id = _make_live_feed("Thaltej")
    try:
        created = record_signals(
            video_id, None, 1.0,
            [AnomalySignal("weapon", 0.92, "clip")], is_live=False)
        assert len(created) == 1
        with get_conn() as conn:
            ev = conn.execute(
                "SELECT case_id FROM anomaly_events WHERE id = ?", (created[0],)
            ).fetchone()
        assert ev["case_id"] is None, "uploads must not auto-create a case"
    finally:
        _cleanup(video_id)
