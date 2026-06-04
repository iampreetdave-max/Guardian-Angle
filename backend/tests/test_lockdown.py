"""Emergency lockdown: citizen requests are 423'd, admins keep operating, and
login + health stay reachable. Toggling off restores normal service."""
from __future__ import annotations


def test_lockdown_blocks_citizen_allows_admin(client, auth_headers):
    admin = auth_headers["admin"]
    citizen = auth_headers["citizen"]

    # Sanity: citizen can hit a normal API route before lockdown.
    assert client.get("/api/notifications", headers=citizen).status_code == 200

    # Engage lockdown via the admin API (exercises the real endpoint + middleware).
    r = client.post("/api/admin/lockdown", headers=admin, json={"enabled": True})
    assert r.status_code == 200 and r.json()["lockdown"] is True, r.text

    try:
        # Citizen is locked out of a normal API route.
        r = client.get("/api/notifications", headers=citizen)
        assert r.status_code == 423, r.text
        assert "lockdown" in r.json()["detail"].lower()

        # Admin JWT bypasses lockdown on a non-/api/admin route.
        r = client.get("/api/notifications", headers=admin)
        assert r.status_code == 200, r.text

        # Login remains reachable so an admin can still sign in.
        r = client.post("/api/auth/login",
                        json={"email": "admin@city.gov", "password": "admin123"})
        assert r.status_code == 200, r.text

        # Health probe is always allowed.
        assert client.get("/api/health").status_code == 200
    finally:
        r = client.post("/api/admin/lockdown", headers=admin, json={"enabled": False})
        assert r.status_code == 200 and r.json()["lockdown"] is False, r.text

    # Toggling off restores the citizen's normal access.
    assert client.get("/api/notifications", headers=citizen).status_code == 200
