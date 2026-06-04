"""Phase 4 smoke test — risk scoring, temporal analytics, patrol routing,
patrol logs, and map layer filters, over the real API with a throwaway DB.

Run from backend/:  python scripts/predictive_smoketest.py
"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ["VISIONSCAN_DATA_DIR"] = tempfile.mkdtemp(prefix="visionscan_pred_")
os.environ["VISIONSCAN_ENABLE_ANOMALY"] = "false"

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
    assert r.status_code == 200, f"login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['token']}"}


def main() -> None:
    print("Predictive policing smoke test")
    print("=" * 50)
    with TestClient(app) as client:
        officer = login(client, "officer@city.gov", "officer123")
        citizen = login(client, "citizen@example.com", "citizen123")

        # ---- risk scores ----
        r = client.get("/api/predict/risk", headers=citizen)
        check("citizen blocked from risk (403)", r.status_code == 403)
        r = client.get("/api/predict/risk", headers=officer)
        check("officer gets risk scores", r.status_code == 200)
        risk = r.json()
        areas = risk["areas"]
        check("all localities scored", len(areas) >= 25, f"got {len(areas)}")
        top = areas[0]
        check("scores normalized 0..100",
              all(0 <= a["risk_score"] <= 100 for a in areas))
        check("top hotspot is a known high-intensity area",
              top["risk_band"] in ("high", "elevated"), str(top))
        check("predictions present",
              all("predicted_score" in a and a["trend"] in
                  ("rising", "stable", "falling") for a in areas))
        spread = {a["risk_band"] for a in areas}
        check("risk bands differentiate the city", len(spread) >= 2, str(spread))

        # ---- temporal patterns ----
        r = client.get("/api/predict/temporal", headers=officer)
        check("temporal patterns load", r.status_code == 200)
        t = r.json()
        check("24 hour bins + 7 day bins",
              len(t["by_hour"]) == 24 and len(t["by_day"]) == 7)
        check("seeded data appears in temporal counts",
              sum(b["count"] for b in t["by_day"]) >= 20)

        # ---- patrol routes ----
        r = client.get("/api/predict/patrol-routes?units=2", headers=officer)
        check("patrol routes computed", r.status_code == 200)
        routes = r.json()["routes"]
        check("two units routed", len(routes) == 2, f"got {len(routes)}")
        if routes:
            wps = [w["area"] for rt in routes for w in rt["waypoints"]]
            check("no hotspot visited twice", len(wps) == len(set(wps)))
            check("routes carry distance + ETA",
                  all(rt["distance_km"] > 0 and rt["eta_min"] > 0 for rt in routes))
            top_areas = {a["area"] for a in areas[:5]}
            check("top-risk areas are covered",
                  len(top_areas & set(wps)) >= 3,
                  f"top5={top_areas} routed={set(wps) & top_areas}")
        r1 = client.get("/api/predict/patrol-routes?units=1&max_stops=6",
                        headers=officer).json()["routes"]
        check("single unit covers all selected stops",
              len(r1) == 1 and len(r1[0]["waypoints"]) == 6, str(len(r1)))

        # ---- patrol logs ----
        r = client.post("/api/predict/patrol-logs", headers=officer,
                        json={"area": "Naroda", "note": "Round complete", "status": "clear"})
        check("officer can log a check-in", r.status_code == 200, r.text[:60])
        r = client.post("/api/predict/patrol-logs", headers=officer,
                        json={"area": "Atlantis", "note": "?", "status": "clear"})
        check("unknown area rejected", r.status_code == 400)
        r = client.post("/api/predict/patrol-logs", headers=citizen,
                        json={"area": "Naroda", "note": "", "status": "clear"})
        check("citizen cannot log patrols (403)", r.status_code == 403)
        r = client.get("/api/predict/patrol-logs?area=Naroda", headers=officer)
        check("patrol log listed with officer name",
              r.status_code == 200 and r.json() and r.json()[0]["officer"])

        # ---- map layer filters ----
        all_total = sum(a["complaints"] for a in client.get(
            "/api/analytics/map", headers=officer).json()["areas"])
        cyber = client.get("/api/analytics/map?category=cyber_fraud",
                           headers=officer).json()
        cyber_total = sum(a["complaints"] for a in cyber["areas"])
        check("category filter narrows the map",
              0 < cyber_total < all_total, f"{cyber_total}/{all_total}")
        check("category list returned for the filter UI",
              "cyber_fraud" in cyber["categories"])
        recent = client.get("/api/analytics/map?days=30", headers=officer).json()
        recent_total = sum(a["complaints"] for a in recent["areas"])
        check("time-window filter narrows the map",
              0 < recent_total < all_total, f"{recent_total}/{all_total}")

    print("\n" + "=" * 50)
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} failure(s): {FAILURES}")
        sys.exit(1)
    print("RESULT: all checks passed")


if __name__ == "__main__":
    main()
