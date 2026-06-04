"""Predictive policing analytics — locality risk scoring, hotspot forecasting,
and temporal crime-pattern analysis.

Model (transparent and explainable by design — judges and officers can audit
every term):

    risk(area) = prior(area)
               + Σ over reports  w_severity · w_category · decay(age)
               + anomaly_boost · active anomaly events on area-tagged cameras

  * decay(age)   : exponential, half-life RECENCY_HALF_LIFE_DAYS — yesterday's
                   snatching matters more than last quarter's.
  * w_severity   : low 1 → critical 4. w_category: violent crime weighs more.
  * prior(area)  : baseline from AREA_CRIME_PROFILE (compiled from public
                   NCRB/police/press reporting) so a fresh deployment still
                   ranks localities sensibly before live data accumulates.

Forecast: the recent-vs-previous window load ratio gives each area a trend
(rising/stable/falling); predicted risk extrapolates the same growth one
window ahead, capped to keep outliers honest.

Scores are min-max normalized to 0–100 across the city for the heatmap legend.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from ..constants.ahmedabad import AHMEDABAD_CENTER, AREAS
from ..database import get_conn
from .security import require_role
from .seed_ahmedabad import AREA_CRIME_PROFILE

predict_router = APIRouter()

RECENCY_HALF_LIFE_DAYS = 14.0
TREND_WINDOW_DAYS = 7.0
ANOMALY_BOOST = 1.5

SEVERITY_W = {"low": 1.0, "medium": 2.0, "high": 3.0, "critical": 4.0}
# violent/body offences threaten life — weigh above property/cyber crime
CATEGORY_W = {
    "murder": 2.0, "body_offences": 1.6, "assault": 1.5,
    "chain_snatching": 1.3, "burglary": 1.2, "vehicle_theft": 1.1,
    "narcotics": 1.2, "prohibition": 1.0, "cyber_fraud": 1.0, "theft": 1.0,
}
PRIOR_W = {"low": 1.0, "medium": 3.0, "high": 6.0}

RISK_BANDS = ((75, "high"), (50, "elevated"), (25, "guarded"), (0, "low"))


def _age_days(created_at: str, now: datetime) -> float:
    try:
        dt = datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return 365.0
    return max((now - dt).total_seconds() / 86400.0, 0.0)


def _decay(age_days: float) -> float:
    return math.pow(0.5, age_days / RECENCY_HALF_LIFE_DAYS)


def _band(score: float) -> str:
    for floor, name in RISK_BANDS:
        if score >= floor:
            return name
    return "low"


def compute_risk() -> list[dict]:
    """Score every known locality. Pure read; cheap enough to compute on
    demand (a few hundred rows)."""
    now = datetime.now(timezone.utc)
    with get_conn() as conn:
        reports = conn.execute(
            "SELECT area, severity, category, created_at FROM complaints "
            "WHERE area IS NOT NULL AND area != ''").fetchall()
        anomalies = {
            r["area"]: r["n"]
            for r in conn.execute(
                "SELECT v.area area, COUNT(*) n FROM anomaly_events a "
                "JOIN videos v ON v.id = a.video_id "
                "WHERE v.area IS NOT NULL AND v.area != '' "
                "AND a.status = 'new' GROUP BY v.area")
        }

    raw: dict[str, float] = {}
    recent: dict[str, float] = {}
    previous: dict[str, float] = {}
    for name in AREAS:
        prior = PRIOR_W.get(
            AREA_CRIME_PROFILE.get(name, {}).get("intensity", ""), 1.0)
        raw[name] = prior
        recent[name] = 0.0
        previous[name] = 0.0

    for r in reports:
        name = r["area"]
        if name not in raw:
            continue
        w = (SEVERITY_W.get(r["severity"] or "medium", 2.0)
             * CATEGORY_W.get(r["category"] or "", 1.0))
        age = _age_days(r["created_at"], now)
        raw[name] += w * _decay(age)
        if age <= TREND_WINDOW_DAYS:
            recent[name] += w
        elif age <= 2 * TREND_WINDOW_DAYS:
            previous[name] += w

    for name, n in anomalies.items():
        if name in raw:
            raw[name] += ANOMALY_BOOST * n

    lo, hi = min(raw.values()), max(raw.values())
    span = max(hi - lo, 1e-9)

    out = []
    for name, (lat, lng) in AREAS.items():
        score = round(100.0 * (raw[name] - lo) / span, 1)
        # growth ratio with +1 smoothing so empty windows don't explode
        growth = (recent[name] + 1.0) / (previous[name] + 1.0)
        trend = "rising" if growth > 1.25 else "falling" if growth < 0.8 else "stable"
        predicted = round(min(score * min(growth, 2.0), 100.0), 1)
        out.append({
            "area": name, "lat": lat, "lng": lng,
            "risk_score": score, "risk_band": _band(score),
            "predicted_score": predicted, "predicted_band": _band(predicted),
            "trend": trend,
            "active_anomalies": anomalies.get(name, 0),
        })
    out.sort(key=lambda a: a["risk_score"], reverse=True)
    return out


@predict_router.get("/risk", tags=["predictive"])
def risk_scores(_: dict = Depends(require_role("officer"))) -> dict:
    """Current + one-window-ahead predicted risk per locality (0–100)."""
    return {
        "center": {"lat": AHMEDABAD_CENTER[0], "lng": AHMEDABAD_CENTER[1]},
        "model": {
            "half_life_days": RECENCY_HALF_LIFE_DAYS,
            "trend_window_days": TREND_WINDOW_DAYS,
        },
        "areas": compute_risk(),
    }


@predict_router.get("/temporal", tags=["predictive"])
def temporal_patterns(area: str | None = None,
                      _: dict = Depends(require_role("officer"))) -> dict:
    """Crime-load distribution by hour of day and day of week (optionally for
    one locality) — the temporal half of hotspot intelligence."""
    where, params = "", []
    if area:
        where = "WHERE area = ?"
        params.append(area)
    with get_conn() as conn:
        by_hour = {int(r["h"]): r["n"] for r in conn.execute(
            f"SELECT strftime('%H', created_at) h, COUNT(*) n FROM complaints "
            f"{where} GROUP BY h", params)}
        by_dow = {int(r["d"]): r["n"] for r in conn.execute(
            f"SELECT strftime('%w', created_at) d, COUNT(*) n FROM complaints "
            f"{where} GROUP BY d", params)}
        by_category = [
            {"label": r["category"] or "unspecified", "count": r["n"]}
            for r in conn.execute(
                f"SELECT category, COUNT(*) n FROM complaints {where} "
                f"GROUP BY category ORDER BY n DESC LIMIT 8", params)]
    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    return {
        "area": area,
        "by_hour": [{"hour": h, "count": by_hour.get(h, 0)} for h in range(24)],
        "by_day": [{"day": days[d], "count": by_dow.get(d, 0)} for d in range(7)],
        "by_category": by_category,
    }
