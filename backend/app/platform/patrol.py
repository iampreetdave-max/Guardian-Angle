"""Patrol route optimization + patrol logs.

Routing: take the highest-risk localities from the predictive model, split
them between the available patrol units (greedy balanced assignment by
proximity), then order each unit's stops with nearest-neighbour and polish
with 2-opt — the classic small-TSP recipe. Distances are haversine; for a
~30-node city graph this is exact enough and needs no external routing API,
so it works fully offline.

Patrol logs: lightweight check-ins (officer, area, note) that close the loop
— planned routes in, ground-truth presence out. Feeds the "patrol logs" data
source the integration story expects.
"""
from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..constants.ahmedabad import AREAS
from ..database import get_conn
from . import service as svc
from .predictive import compute_risk
from .security import get_current_user, require_role

patrol_router = APIRouter()

# Ahmedabad Cyber Crime Branch (Shahibaug) — default depot for route starts.
STATION = {"name": "Cyber Crime Branch HQ", "lat": 23.0530, "lng": 72.5930}
AVG_PATROL_SPEED_KMH = 25.0   # city patrol pace incl. observation stops


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _route_length(points: list[tuple[float, float]]) -> float:
    return sum(_haversine_km(points[i], points[i + 1])
               for i in range(len(points) - 1))


def _nearest_neighbour(start: tuple[float, float],
                       stops: list[int],
                       coords: list[tuple[float, float]]) -> list[int]:
    order, remaining, cur = [], set(stops), start
    while remaining:
        nxt = min(remaining, key=lambda i: _haversine_km(cur, coords[i]))
        order.append(nxt)
        remaining.remove(nxt)
        cur = coords[nxt]
    return order


def _two_opt(order: list[int], start: tuple[float, float],
             coords: list[tuple[float, float]]) -> list[int]:
    """Standard 2-opt: keep reversing segments while it shortens the tour."""
    def tour_len(o: list[int]) -> float:
        return _route_length([start] + [coords[i] for i in o])

    best, best_len, improved = order[:], tour_len(order), True
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                cand_len = tour_len(cand)
                if cand_len < best_len - 1e-9:
                    best, best_len, improved = cand, cand_len, True
    return best


@patrol_router.get("/patrol-routes", tags=["predictive"])
def patrol_routes(units: int = 2, max_stops: int = 12,
                  _: dict = Depends(require_role("officer"))) -> dict:
    """Optimized patrol routes over the current top-risk localities.

    units: patrol teams available (1–6). max_stops: hotspots covered overall.
    """
    units = max(1, min(units, 6))
    max_stops = max(units, min(max_stops, 20))

    risk = compute_risk()
    hotspots = [a for a in risk if a["risk_score"] > 0][:max_stops]
    if not hotspots:
        return {"station": STATION, "routes": []}

    coords = [(a["lat"], a["lng"]) for a in hotspots]
    start = (STATION["lat"], STATION["lng"])

    # Balanced greedy assignment: walk hotspots by risk rank, give each to the
    # unit whose current centroid is closest, but never let one unit hold more
    # than ceil(n/units) stops — keeps workloads even AND clusters compact.
    cap = math.ceil(len(hotspots) / units)
    assignment: list[list[int]] = [[] for _ in range(units)]
    centroids: list[tuple[float, float]] = [start] * units
    for idx in range(len(hotspots)):
        open_units = [u for u in range(units) if len(assignment[u]) < cap]
        u = min(open_units, key=lambda u: _haversine_km(centroids[u], coords[idx]))
        assignment[u].append(idx)
        pts = [coords[i] for i in assignment[u]]
        centroids[u] = (sum(p[0] for p in pts) / len(pts),
                        sum(p[1] for p in pts) / len(pts))

    routes = []
    for u, stops in enumerate(assignment):
        if not stops:
            continue
        order = _two_opt(_nearest_neighbour(start, stops, coords), start, coords)
        waypoints = [{
            "area": hotspots[i]["area"],
            "lat": hotspots[i]["lat"], "lng": hotspots[i]["lng"],
            "risk_score": hotspots[i]["risk_score"],
            "risk_band": hotspots[i]["risk_band"],
            "trend": hotspots[i]["trend"],
        } for i in order]
        km = _route_length([start] + [coords[i] for i in order])
        routes.append({
            "unit": u + 1,
            "waypoints": waypoints,
            "distance_km": round(km, 1),
            "eta_min": round(km / AVG_PATROL_SPEED_KMH * 60),
        })
    return {"station": STATION, "units": units, "routes": routes}


# ---------------- patrol logs (check-ins) ----------------
class PatrolLogIn(BaseModel):
    area: str
    note: str = Field("", max_length=500)
    status: str = Field("clear", description="clear|incident|followup")


@patrol_router.post("/patrol-logs", tags=["predictive"])
def add_patrol_log(body: PatrolLogIn,
                   user: dict = Depends(require_role("officer"))) -> dict:
    if body.area not in AREAS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown area")
    if body.status not in ("clear", "incident", "followup"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status")
    with get_conn() as conn:
        pid = conn.execute(
            "INSERT INTO patrol_logs (officer_id, area, note, status) "
            "VALUES (?, ?, ?, ?)",
            (user["id"], body.area, body.note, body.status),
        ).lastrowid
    svc.audit(user["id"], "patrol_checkin", "patrol_log", pid, body.area)
    return {"id": pid}


@patrol_router.get("/patrol-logs", tags=["predictive"])
def list_patrol_logs(area: str | None = None, limit: int = 50,
                     _: dict = Depends(require_role("officer"))) -> list[dict]:
    limit = max(1, min(limit, 200))
    where, params = "", []
    if area:
        where = "WHERE p.area = ?"
        params.append(area)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT p.*, u.name AS officer, u.badge_no FROM patrol_logs p "
            f"JOIN users u ON u.id = p.officer_id {where} "
            f"ORDER BY p.created_at DESC LIMIT ?", (*params, limit)).fetchall()
    return [dict(r) for r in rows]
