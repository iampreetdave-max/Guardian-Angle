"""Phase 3 security pytest suite — shared fixtures.

Mirrors the smoke-test bootstrap: a throwaway data dir is set in os.environ
BEFORE app.main is ever imported, so the developer database is never touched and
no models load. bcrypt logins are deliberately slow, so we log in once per role
per session and cache the resulting auth headers.
"""
from __future__ import annotations

import os
import tempfile

# ---- environment MUST be set before any `app.*` import ----------------------
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ["VISIONSCAN_DATA_DIR"] = tempfile.mkdtemp(prefix="visionscan_phase3_")
os.environ["VISIONSCAN_ENABLE_ANOMALY"] = "false"

import pytest
from fastapi.testclient import TestClient

# Importing app.main triggers init_db() + demo seeding against the temp dir.
from app.main import app

# Demo credentials (seeded on first run) — see backend/app/platform/seed.py.
_CREDS = {
    "admin": ("admin@city.gov", "admin123"),
    "lead": ("lead@city.gov", "lead123"),
    "officer": ("officer@city.gov", "officer123"),
    "citizen": ("citizen@example.com", "citizen123"),
}


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    """Ensure the schema + demo seed exist before any test runs.

    The app normally runs init_db() in its startup event, which only fires when
    a TestClient context is entered. Pure unit tests (arbiter/upload/ssrf) never
    open a client, yet the autouse reset fixture below touches app_settings, so
    initialise the DB once up-front. init_db() is idempotent.
    """
    from app.database import init_db

    init_db()
    yield


@pytest.fixture(scope="session")
def client() -> TestClient:
    """One TestClient for the whole session (cheaper than per-test setup)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client: TestClient) -> dict[str, dict[str, str]]:
    """Log in once per role and cache the Authorization headers.

    bcrypt verification is slow, so doing this a single time per session keeps
    the suite fast. Returns {role: {"Authorization": "Bearer …"}}.
    """
    headers: dict[str, dict[str, str]] = {}
    for role, (email, password) in _CREDS.items():
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, f"login failed for {role}: {r.text}"
        headers[role] = {"Authorization": f"Bearer {r.json()['token']}"}
    return headers


@pytest.fixture(autouse=True)
def _reset_security_state():
    """Before each test: clear rate-limit buckets and lift any lockdown.

    Imported lazily so this module's import never pulls in app.security_mw
    before the env bootstrap above has run.
    """
    from app import security_mw

    security_mw.reset_rate_limits()
    security_mw.set_lockdown(False)
    yield
    # Be a good neighbour on the way out too, so a test that flips lockdown or
    # exhausts a bucket can never bleed into the next one.
    security_mw.reset_rate_limits()
    security_mw.set_lockdown(False)
