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


def test_static_thumbnails_do_not_spend_the_api_budget(client):
    """A search grid loads up to 60 thumbnails per page; those static requests
    must not consume the API bucket (they used to, and 429'd the demo)."""
    s = get_settings()
    security_mw.reset_rate_limits()

    n = s.rate_limit_default_per_min * 2
    statuses = {client.get("/thumbnails/nope.jpg").status_code for _ in range(n)}
    assert 429 not in statuses, f"thumbnails were rate limited: {statuses}"

    # And the API budget is untouched afterwards.
    assert client.get("/api/health").status_code == 200


def test_buckets_are_per_user_not_per_ip(client, auth_headers):
    """Every browser behind the nginx proxy shares one client IP, so buckets
    key on the authenticated user: one operator cannot starve another."""
    s = get_settings()
    security_mw.reset_rate_limits()

    admin, officer = auth_headers["admin"], auth_headers["officer"]
    got_429 = False
    for _ in range(s.rate_limit_default_per_min + 40):
        if client.get("/api/health", headers=admin).status_code == 429:
            got_429 = True
            break
    assert got_429, "admin should have exhausted its own default bucket"

    # Same IP, different user -> untouched bucket.
    assert client.get("/api/health", headers=officer).status_code == 200
