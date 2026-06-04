"""Admin broadcast fan-out + the anomaly-event debounce, exercised directly."""
from __future__ import annotations

from app.config import get_settings
from app.core.anomaly import AnomalySignal
from app.database import get_conn
from app.services.anomaly_events import record_signals


# ----------------------------------------------------------------- broadcast
def test_admin_broadcast_fanout_and_active_list(client, auth_headers):
    admin = auth_headers["admin"]
    citizen = auth_headers["citizen"]

    payload = {
        "kind": "disaster",
        "title": "Flood warning",
        "message": "Low-lying areas near the riverfront may flood tonight.",
        "area": "Sabarmati",
        "severity": "critical",
    }

    # Citizen cannot broadcast.
    r = client.post("/api/notifications/broadcast", headers=citizen, json=payload)
    assert r.status_code == 403, r.text

    # Admin can; fan-out reaches every active user (>= the 4 seeded demo users).
    r = client.post("/api/notifications/broadcast", headers=admin, json=payload)
    assert r.status_code == 200, r.text
    recipients = r.json()["recipients"]
    assert recipients >= 4, f"expected fan-out to all active users, got {recipients}"
    bid = r.json()["id"]

    # The broadcast appears in the active list for any role.
    r = client.get("/api/notifications/broadcasts/active", headers=citizen)
    assert r.status_code == 200, r.text
    assert any(b["id"] == bid for b in r.json())

    # The citizen actually received the notification.
    r = client.get("/api/notifications", headers=citizen)
    msgs = [n["message"] for n in r.json()["items"]]
    assert any("Flood warning" in m for m in msgs), msgs[:3]

    # Invalid severity is rejected.
    r = client.post("/api/notifications/broadcast", headers=admin,
                    json={**payload, "severity": "apocalyptic"})
    assert r.status_code == 400, r.text

    # Clean up so the active banner doesn't leak into other tests.
    client.post(f"/api/notifications/broadcasts/{bid}/deactivate", headers=admin)


# ------------------------------------------------------------------- anomaly
def test_record_signals_debounce_merges_then_splits():
    """Two close-in-time fire signals merge into one event (peak_count=2); a
    third past the gap opens a fresh event. Uses a directly-inserted videos row
    so no models are needed."""
    s = get_settings()
    gap = s.anomaly_event_gap_sec

    with get_conn() as conn:
        video_id = conn.execute(
            "INSERT INTO videos (filename, path, camera_id, status) "
            "VALUES ('pytest_anomaly', 'pytest://none', 'CAM-PYTEST', 'ready')"
        ).lastrowid

    try:
        created1 = record_signals(
            video_id, None, 10.0,
            [AnomalySignal("fire", 0.40, "clip")], is_live=False)
        created2 = record_signals(
            video_id, None, 10.0 + gap / 2,
            [AnomalySignal("fire", 0.55, "clip")], is_live=False)
        created3 = record_signals(
            video_id, None, 10.0 + gap * 3,
            [AnomalySignal("fire", 0.45, "clip")], is_live=False)

        assert len(created1) == 1, "first signal should open an event"
        assert len(created2) == 0, "close signal should merge, not create"
        assert len(created3) == 1, "signal past the gap should open a new event"

        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id, confidence, peak_count FROM anomaly_events "
                "WHERE video_id = ? ORDER BY id", (video_id,)
            ).fetchall()
        assert len(rows) == 2, f"expected two events, got {len(rows)}"
        # Merged (first) event: peak_count 2, confidence kept at the max (0.55).
        assert rows[0]["peak_count"] == 2, rows[0]["peak_count"]
        assert abs(rows[0]["confidence"] - 0.55) < 1e-6, rows[0]["confidence"]
    finally:
        with get_conn() as conn:
            conn.execute("DELETE FROM anomaly_events WHERE video_id = ?", (video_id,))
            conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
