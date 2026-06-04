"""Phase 2 smoke test — broadcasts + city map, end to end over the real API.

Uses FastAPI's TestClient against a THROWAWAY data dir (set before importing
the app) so the developer database is never touched.

Run from backend/:  python scripts/broadcast_map_smoketest.py
"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
_tmp = tempfile.mkdtemp(prefix="visionscan_smoke_")
os.environ["VISIONSCAN_DATA_DIR"] = _tmp
os.environ["VISIONSCAN_ENABLE_ANOMALY"] = "false"   # no model loads needed here

import sys

from fastapi.testclient import TestClient

from app.main import app

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def login(client: TestClient, email: str, password: str) -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['token']}"}


def main() -> None:
    print("Broadcast + City Map smoke test")
    print("=" * 50)
    with TestClient(app) as client:
        admin = login(client, "admin@city.gov", "admin123")
        citizen = login(client, "citizen@example.com", "citizen123")
        officer = login(client, "officer@city.gov", "officer123")

        # ---- areas endpoint ----
        r = client.get("/api/analytics/areas", headers=citizen)
        check("citizen can list areas", r.status_code == 200, str(r.status_code))
        areas = r.json()["areas"]
        check("areas include Navrangpura with centroid",
              any(a["name"] == "Navrangpura" and a["lat"] for a in areas))

        # ---- complaint with area -> lat/lng ----
        baseline = next(
            a for a in client.get("/api/analytics/map", headers=officer)
            .json()["areas"] if a["area"] == "Vastrapur")["complaints"]
        r = client.post("/api/complaints", headers=citizen, json={
            "title": "Streetlight outage near lake",
            "description": "Dark stretch attracting trouble at night.",
            "category": "public-safety", "area": "Vastrapur",
        })
        check("complaint with area accepted", r.status_code == 200, r.text[:80])

        # ---- broadcast: citizen forbidden, admin ok ----
        payload = {
            "kind": "disaster", "title": "Flood warning",
            "message": "Low-lying areas near the riverfront may flood tonight.",
            "area": "Sabarmati", "severity": "critical",
        }
        r = client.post("/api/notifications/broadcast", headers=citizen, json=payload)
        check("citizen broadcast rejected (403)", r.status_code == 403, str(r.status_code))
        r = client.post("/api/notifications/broadcast", headers=admin, json=payload)
        check("admin broadcast accepted", r.status_code == 200, r.text[:80])
        recipients = r.json().get("recipients", 0)
        check("fan-out reached all 4 demo users", recipients == 4, f"got {recipients}")

        # ---- everyone sees the active banner; citizen got the notification ----
        r = client.get("/api/notifications/broadcasts/active", headers=citizen)
        check("citizen sees active broadcast", r.status_code == 200 and len(r.json()) == 1)
        r = client.get("/api/notifications", headers=citizen)
        msgs = [n["message"] for n in r.json()["items"]]
        check("citizen notification delivered",
              any("Flood warning" in m for m in msgs), str(msgs[:2]))

        # ---- invalid inputs rejected ----
        r = client.post("/api/notifications/broadcast", headers=admin,
                        json={**payload, "severity": "apocalyptic"})
        check("invalid severity rejected", r.status_code == 400)
        r = client.post("/api/notifications/broadcast", headers=admin,
                        json={**payload, "expires_at": "not-a-date"})
        check("invalid expires_at rejected", r.status_code == 400)

        # ---- deactivate clears the banner ----
        bid = client.get("/api/notifications/broadcasts", headers=admin).json()[0]["id"]
        r = client.post(f"/api/notifications/broadcasts/{bid}/deactivate", headers=admin)
        check("deactivate works", r.status_code == 200)
        r = client.get("/api/notifications/broadcasts/active", headers=citizen)
        check("banner cleared after deactivate", len(r.json()) == 0)

        # ---- map aggregates ----
        r = client.get("/api/analytics/map", headers=citizen)
        check("citizen blocked from map (403)", r.status_code == 403, str(r.status_code))
        r = client.get("/api/analytics/map", headers=officer)
        check("officer can load map", r.status_code == 200)
        data = r.json()
        vast = next(a for a in data["areas"] if a["area"] == "Vastrapur")
        check("Vastrapur gained the new complaint",
              vast["complaints"] == baseline + 1, str(vast))
        check("seeded incidents populate the map",
              sum(a["complaints"] for a in data["areas"]) >= 20,
              f"total={sum(a['complaints'] for a in data['areas'])}")
        check("seeded cases populate the map",
              sum(a["cases"] for a in data["areas"]) >= 5,
              f"cases={sum(a['cases'] for a in data['areas'])}")
        check("all areas returned zeros-safe",
              len(data["areas"]) >= 25 and all("lat" in a for a in data["areas"]))

    print("\n" + "=" * 50)
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} failure(s): {FAILURES}")
        sys.exit(1)
    print("RESULT: all checks passed")


if __name__ == "__main__":
    main()
