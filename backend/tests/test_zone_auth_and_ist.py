"""Two regressions this suite previously could not catch:

1. /videos/{id}/zone-analytics and /line-crossings served per-camera movement
   analytics to anonymous callers — they had no auth dependency at all, unlike
   every sibling route.
2. The 14-day complaints trend bucketed by UTC date while the data and the
   readers are in IST, so "today" was empty between 05:30 IST (UTC rollover)
   and the first complaint filed after it.
"""
from __future__ import annotations

import pytest

from app.config import get_settings
from app.database import get_conn

ZONE = {"polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]}
LINE = {"line": [[0.1, 0.5], [0.9, 0.5]]}
GATED = [("zone-analytics", ZONE), ("line-crossings", LINE)]


@pytest.fixture
def require_auth():
    """Flip VISIONSCAN_REQUIRE_AUTH on for one test (settings is a singleton)."""
    s = get_settings()
    before = s.require_auth
    s.require_auth = True
    yield
    s.require_auth = before


@pytest.mark.parametrize("path,body", GATED)
def test_open_when_flag_off(client, path, body):
    """The demo runs with the flag off; these must stay reachable."""
    assert get_settings().require_auth is False
    assert client.post(f"/api/videos/1/{path}", json=body).status_code != 401


@pytest.mark.parametrize("path,body", GATED)
def test_closed_when_flag_on(client, auth_headers, require_auth, path, body):
    r = client.post(f"/api/videos/1/{path}", json=body)
    assert r.status_code == 401, f"{path} leaks analytics to anonymous callers"
    assert client.post(f"/api/videos/1/{path}", json=body,
                       headers={"Authorization": "Bearer garbage"}).status_code == 401
    # A real token still gets through (404 here = auth passed, video absent).
    assert client.post(f"/api/videos/1/{path}", json=body,
                       headers=auth_headers["admin"]).status_code != 401


def test_trend_buckets_by_ist_not_utc(client, auth_headers):
    """A complaint filed just after IST midnight belongs in today's bar.

    Its UTC timestamp is 18:30 on the *previous* UTC date, so UTC bucketing
    always drops it into yesterday — this fails year-round if the shift is lost.
    """
    with get_conn() as conn:
        uid = conn.execute("SELECT id FROM users LIMIT 1").fetchone()["id"]
        ist_today, just_after_ist_midnight = conn.execute(
            "SELECT date('now','+330 minutes'), "
            "datetime('now','+330 minutes','start of day','-330 minutes','+5 minutes')"
        ).fetchone()
        conn.execute(
            "INSERT INTO complaints (citizen_id, title, description, created_at) "
            "VALUES (?, 'ist bucket probe', 'ist bucket probe', ?)",
            (uid, just_after_ist_midnight),
        )

    series = client.get("/api/analytics/summary",
                        headers=auth_headers["admin"]).json()["complaints_over_time"]
    dates = [d["date"] for d in series]
    assert len(dates) == 14 and dates == sorted(set(dates))
    assert dates[-1] == ist_today, "window boundary must agree with the buckets"
    assert series[-1]["count"] >= 1, "today's bar is empty — bucketed in UTC again"
