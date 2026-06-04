"""Auth hardening: role gating, brute-force lockout, token revocation, register."""
from __future__ import annotations

import uuid

from app.config import get_settings
from app.database import get_conn


# --------------------------------------------------------------- role gating
def test_citizen_blocked_from_staff_routes(client, auth_headers):
    """A citizen token must be 403'd on staff/admin-only routes."""
    citizen = auth_headers["citizen"]
    # admin-only
    r = client.get("/api/users", headers=citizen)
    assert r.status_code == 403, r.text
    # officer+ analytics map
    r = client.get("/api/analytics/map", headers=citizen)
    assert r.status_code == 403, r.text
    # admin system console
    r = client.get("/api/admin/system", headers=citizen)
    assert r.status_code == 403, r.text


def test_staff_can_reach_their_routes(client, auth_headers):
    r = client.get("/api/analytics/map", headers=auth_headers["officer"])
    assert r.status_code == 200, r.text
    r = client.get("/api/admin/system", headers=auth_headers["admin"])
    assert r.status_code == 200, r.text


# ------------------------------------------------------------------ register
def test_register_creates_citizen(client):
    email = f"newcitizen_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={
        "name": "New Citizen", "email": email, "password": "pw-abc12345",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["role"] == "citizen"
    assert body["token"]
    # token actually works
    me = client.get("/api/auth/me",
                    headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200 and me.json()["email"] == email


def test_register_rejects_duplicate_email(client):
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"name": "Dup", "email": email, "password": "pw-abc12345"}
    r1 = client.post("/api/auth/register", json=payload)
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/auth/register", json=payload)
    assert r2.status_code == 409, r2.text


# ------------------------------------------------------------------- lockout
def test_login_lockout_after_max_attempts(client):
    """5 wrong-password attempts lock the account for the window; further
    attempts return 429 even with the CORRECT password."""
    # Register a throwaway account so we never lock out the demo logins the
    # cached fixtures depend on.
    email = f"lockme_{uuid.uuid4().hex[:8]}@example.com"
    good_pw = "correct-horse-9"
    reg = client.post("/api/auth/register", json={
        "name": "Lock Me", "email": email, "password": good_pw,
    })
    assert reg.status_code == 200, reg.text

    s = get_settings()
    try:
        # Hammer with the wrong password up to the limit.
        for i in range(s.login_max_attempts):
            r = client.post("/api/auth/login",
                            json={"email": email, "password": "wrong-pw"})
            assert r.status_code == 401, f"attempt {i}: {r.status_code} {r.text}"

        # Now the lockout window is open: even the RIGHT password is 429'd.
        r = client.post("/api/auth/login",
                        json={"email": email, "password": good_pw})
        assert r.status_code == 429, r.text
        assert "many failed" in r.json()["detail"].lower()
    finally:
        # Clear this email's attempt rows so the window can't bleed into other
        # tests (login_attempts is not reset by the autouse fixture).
        with get_conn() as conn:
            conn.execute("DELETE FROM login_attempts WHERE email = ?", (email,))

    # After clearing, the good password works again — proves it was the lockout
    # window, not a corrupted account.
    r = client.post("/api/auth/login", json={"email": email, "password": good_pw})
    assert r.status_code == 200, r.text


# --------------------------------------------------------------- logout-all
def test_logout_all_revokes_old_token(client):
    """logout-all bumps token_version; the caller's existing token is rejected
    with 401 'Token revoked' on the next request."""
    email = f"revoke_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/auth/register", json={
        "name": "Revoke Me", "email": email, "password": "pw-abc12345",
    })
    assert reg.status_code == 200, reg.text
    token = reg.json()["token"]
    hdr = {"Authorization": f"Bearer {token}"}

    # Token works first.
    assert client.get("/api/auth/me", headers=hdr).status_code == 200

    r = client.post("/api/auth/logout-all", headers=hdr)
    assert r.status_code == 200, r.text

    # Same token now revoked.
    r = client.get("/api/auth/me", headers=hdr)
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "Token revoked"
