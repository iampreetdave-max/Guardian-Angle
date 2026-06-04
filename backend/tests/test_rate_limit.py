"""Rate limiting: a burst of logins past the per-minute cap yields a 429 with a
Retry-After header, and reset_rate_limits() restores the budget."""
from __future__ import annotations

import uuid

from app import security_mw
from app.config import get_settings


def test_login_burst_triggers_rate_limit(client):
    s = get_settings()
    assert s.enable_rate_limit, "rate limiting must be on for this test"

    # Start from a clean bucket (the autouse fixture already cleared it, but be
    # explicit so this test reads standalone).
    security_mw.reset_rate_limits()

    # Use a distinct email per request so the per-email login LOCKOUT (a
    # different 429) never fires — we want to observe the MIDDLEWARE rate limit.
    n = s.rate_limit_login_per_min + 1
    statuses: list[int] = []
    rate_limited_with_retry = False
    for _ in range(n):
        email = f"rl_{uuid.uuid4().hex[:10]}@example.com"
        r = client.post("/api/auth/login",
                        json={"email": email, "password": "nope-nope-123"})
        statuses.append(r.status_code)
        if r.status_code == 429 and r.headers.get("Retry-After"):
            # Middleware rate-limit response: detail + Retry-After.
            assert r.json()["detail"] == "Too many requests", r.text
            assert int(r.headers["Retry-After"]) >= 1
            rate_limited_with_retry = True

    assert rate_limited_with_retry, f"expected a 429 w/ Retry-After, got {statuses}"

    # After a reset the bucket is full again: the next login is NOT rate-limited
    # (it will be a normal 401 for bad creds).
    security_mw.reset_rate_limits()
    r = client.post("/api/auth/login",
                    json={"email": f"rl_{uuid.uuid4().hex[:10]}@example.com",
                          "password": "nope-nope-123"})
    assert r.status_code == 401, f"after reset expected 401, got {r.status_code}"
