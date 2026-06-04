"""CityShield analytics — aggregate stats for the command dashboard.

Read-only GROUP BY queries over the shared SQLite DB (complaints, cases,
ratings, evidence) plus live VisionScan index size. Staff-only. Every figure is
empty-safe so a fresh database returns zeros instead of erroring.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..constants.ahmedabad import AHMEDABAD_CENTER, AREAS
from ..constants.cyber import CYBER_CATEGORIES, FRAUD_CHANNELS
from ..database import get_conn
from .security import get_current_user, require_role

analytics_router = APIRouter()


def _counts(conn, sql: str, params: tuple = ()) -> list[dict]:
    """Run a `SELECT <label>, COUNT(*) ...` and return [{label, count}]."""
    rows = conn.execute(sql, params).fetchall()
    return [
        {"label": (r[0] if r[0] not in (None, "") else "unspecified"), "count": r[1]}
        for r in rows
    ]


def _scalar(conn, sql: str, params: tuple = (), default=0):
    val = conn.execute(sql, params).fetchone()[0]
    return val if val is not None else default


@analytics_router.get("/summary", tags=["analytics"])
def summary(_: dict = Depends(require_role("officer"))) -> dict:
    """One-shot snapshot for the analytics dashboard (staff only)."""
    with get_conn() as conn:
        total_complaints = _scalar(conn, "SELECT COUNT(*) FROM complaints")
        open_cases = _scalar(
            conn, "SELECT COUNT(*) FROM cases WHERE status IN ('open','active')"
        )
        closed_cases = _scalar(
            conn, "SELECT COUNT(*) FROM cases WHERE status = 'closed'"
        )
        total_cases = _scalar(conn, "SELECT COUNT(*) FROM cases")
        total_evidence = _scalar(conn, "SELECT COUNT(*) FROM evidence")
        total_users = _scalar(conn, "SELECT COUNT(*) FROM users")

        # Average resolution time (hours) over closed cases that have a closed_at.
        avg_resolution_hours = _scalar(
            conn,
            "SELECT AVG((julianday(closed_at) - julianday(created_at)) * 24.0) "
            "FROM cases WHERE status = 'closed' AND closed_at IS NOT NULL",
        )
        avg_rating = _scalar(conn, "SELECT AVG(stars) FROM ratings")
        n_ratings = _scalar(conn, "SELECT COUNT(*) FROM ratings")

        complaints_by_status = _counts(
            conn,
            "SELECT status, COUNT(*) FROM complaints GROUP BY status "
            "ORDER BY COUNT(*) DESC",
        )
        complaints_by_category = _counts(
            conn,
            "SELECT category, COUNT(*) FROM complaints GROUP BY category "
            "ORDER BY COUNT(*) DESC LIMIT 8",
        )
        cases_by_status = _counts(
            conn, "SELECT status, COUNT(*) FROM cases GROUP BY status"
        )
        cases_by_severity = _counts(
            conn, "SELECT severity, COUNT(*) FROM cases GROUP BY severity"
        )
        top_locations = _counts(
            conn,
            "SELECT location, COUNT(*) FROM complaints "
            "WHERE location IS NOT NULL AND location != '' "
            "GROUP BY location ORDER BY COUNT(*) DESC LIMIT 6",
        )

        # Complaints per day for the last 14 days (dense — fill gaps with 0).
        raw = {
            r[0]: r[1]
            for r in conn.execute(
                "SELECT date(created_at) d, COUNT(*) FROM complaints "
                "WHERE created_at >= date('now','-13 days') GROUP BY d"
            ).fetchall()
        }
        complaints_over_time = []
        for offset in range(13, -1, -1):
            day = conn.execute(
                "SELECT date('now', ?)", (f"-{offset} days",)
            ).fetchone()[0]
            complaints_over_time.append({"date": day, "count": raw.get(day, 0)})

        n_videos = _scalar(conn, "SELECT COUNT(*) FROM videos")

    # Live index size from the running FAISS index (not the DB).
    try:
        from ..core.index import get_clip_index

        indexed_frames = get_clip_index().ntotal
    except Exception:
        indexed_frames = 0

    return {
        "kpis": {
            "total_complaints": total_complaints,
            "open_cases": open_cases,
            "closed_cases": closed_cases,
            "total_cases": total_cases,
            "total_evidence": total_evidence,
            "total_users": total_users,
            "avg_resolution_hours": round(avg_resolution_hours, 1)
            if avg_resolution_hours else 0,
            "avg_rating": round(avg_rating, 2) if avg_rating else 0,
            "n_ratings": n_ratings,
            "total_videos": n_videos,
            "indexed_frames": indexed_frames,
        },
        "complaints_by_status": complaints_by_status,
        "complaints_by_category": complaints_by_category,
        "cases_by_status": cases_by_status,
        "cases_by_severity": cases_by_severity,
        "top_locations": top_locations,
        "complaints_over_time": complaints_over_time,
    }


@analytics_router.get("/areas", tags=["analytics"])
def list_areas(_: dict = Depends(get_current_user)) -> dict:
    """Ahmedabad locality names + centroids for dropdowns and the map.
    Available to every authenticated role (citizens pick an area when filing)."""
    return {
        "center": {"lat": AHMEDABAD_CENTER[0], "lng": AHMEDABAD_CENTER[1]},
        "areas": [
            {"name": name, "lat": lat, "lng": lng}
            for name, (lat, lng) in AREAS.items()
        ],
    }


@analytics_router.get("/map", tags=["analytics"])
def map_aggregates(category: str | None = None, days: int | None = None,
                   _: dict = Depends(require_role("officer"))) -> dict:
    """Per-locality aggregates for the City Map: complaint/case density,
    severity mix, top category, and anomaly counts (via camera area tags).
    Every known area is returned (zeros included) so the map is always full.
    Optional layer filters: category (exact match) and days (lookback window)."""
    flt, params = "", []
    if category:
        flt += " AND category = ?"
        params.append(category)
    if days and days > 0:
        flt += " AND created_at >= datetime('now', ?)"
        params.append(f"-{int(days)} days")

    with get_conn() as conn:
        complaints = {
            r["area"]: r["n"]
            for r in conn.execute(
                "SELECT area, COUNT(*) n FROM complaints "
                f"WHERE area IS NOT NULL AND area != ''{flt} GROUP BY area",
                params)
        }
        case_flt = flt.replace("category", "cp.category").replace(
            "created_at", "cp.created_at")
        cases = {
            r["area"]: r["n"]
            for r in conn.execute(
                "SELECT cp.area area, COUNT(*) n FROM cases c "
                "JOIN complaints cp ON cp.id = c.complaint_id "
                f"WHERE cp.area IS NOT NULL AND cp.area != ''{case_flt} "
                "GROUP BY cp.area", params)
        }
        severity_rows = conn.execute(
            "SELECT area, severity, COUNT(*) n FROM complaints "
            "WHERE area IS NOT NULL AND area != '' AND severity IS NOT NULL"
            f"{flt} GROUP BY area, severity", params).fetchall()
        by_severity: dict[str, dict[str, int]] = {}
        for r in severity_rows:
            by_severity.setdefault(r["area"], {})[r["severity"]] = r["n"]

        top_category: dict[str, str] = {}
        for r in conn.execute(
            "SELECT area, category, COUNT(*) n FROM complaints "
            "WHERE area IS NOT NULL AND area != '' AND category IS NOT NULL"
            f"{flt} GROUP BY area, category ORDER BY n ASC", params
        ):
            # ascending order means the last write per area is the max count
            top_category[r["area"]] = r["category"]

        categories = [r["category"] for r in conn.execute(
            "SELECT DISTINCT category FROM complaints "
            "WHERE category IS NOT NULL AND category != '' ORDER BY category")]

        anomalies = {
            r["area"]: r["n"]
            for r in conn.execute(
                "SELECT v.area area, COUNT(*) n FROM anomaly_events a "
                "JOIN videos v ON v.id = a.video_id "
                "WHERE v.area IS NOT NULL AND v.area != '' "
                "AND a.status != 'dismissed' GROUP BY v.area")
        }

    areas = []
    for name, (lat, lng) in AREAS.items():
        areas.append({
            "area": name, "lat": lat, "lng": lng,
            "complaints": complaints.get(name, 0),
            "cases": cases.get(name, 0),
            "by_severity": by_severity.get(name, {}),
            "top_category": top_category.get(name),
            "anomalies": anomalies.get(name, 0),
        })
    return {
        "center": {"lat": AHMEDABAD_CENTER[0], "lng": AHMEDABAD_CENTER[1]},
        "areas": areas,
        "categories": categories,
        "filters": {"category": category, "days": days},
    }


# A cyber complaint is anything on the cyber-fraud track: the broad category OR
# any structured NCRP/1930 cyber_category tag (set via the cybercrime intake).
_CYBER_WHERE = "(category = 'cyber_fraud' OR cyber_category IS NOT NULL)"


@analytics_router.get("/map/cyber", tags=["analytics"])
def map_cyber(days: int | None = 90,
              _: dict = Depends(require_role("officer"))) -> dict:
    """Per-locality cyber-fraud aggregates for the Cyber Fraud map layer:
    victim count, total ₹ lost, top cyber_category (with its taxonomy label)
    and fraud-channel mix — plus citywide totals. This is *victim-location*
    density (where victims live), not where the fraudsters operate.

    Mirrors /map: officer-only, same `days` lookback window, and every known
    area is returned (zeros included) so the layer is always full. Areas join
    to centroids via the same constants/ahmedabad AREAS table /map uses.

    NB: synthetic rows predate the amount_lost column (it is NULL there), so the
    frontend falls back to victim_count sizing when amounts are absent — the
    aggregates here stay correct either way (total_amount_lost is COALESCE'd)."""
    flt, params = "", []
    if days and days > 0:
        flt += " AND created_at >= datetime('now', ?)"
        params.append(f"-{int(days)} days")

    with get_conn() as conn:
        victims = {
            r["area"]: r["n"]
            for r in conn.execute(
                "SELECT area, COUNT(*) n FROM complaints "
                f"WHERE area IS NOT NULL AND area != '' AND {_CYBER_WHERE}{flt} "
                "GROUP BY area", params)
        }
        amounts = {
            r["area"]: (r["amt"] or 0)
            for r in conn.execute(
                "SELECT area, COALESCE(SUM(amount_lost), 0) amt FROM complaints "
                f"WHERE area IS NOT NULL AND area != '' AND {_CYBER_WHERE}{flt} "
                "GROUP BY area", params)
        }

        # Top cyber_category per area (ascending so the last write wins = max).
        top_cat: dict[str, str] = {}
        for r in conn.execute(
            "SELECT area, cyber_category, COUNT(*) n FROM complaints "
            "WHERE area IS NOT NULL AND area != '' "
            f"AND cyber_category IS NOT NULL AND cyber_category != ''{flt} "
            "GROUP BY area, cyber_category ORDER BY n ASC", params
        ):
            top_cat[r["area"]] = r["cyber_category"]

        # Fraud-channel counts per area.
        channels_by_area: dict[str, dict[str, int]] = {}
        for r in conn.execute(
            "SELECT area, fraud_channel, COUNT(*) n FROM complaints "
            "WHERE area IS NOT NULL AND area != '' "
            f"AND fraud_channel IS NOT NULL AND fraud_channel != ''{flt} "
            f"AND {_CYBER_WHERE} GROUP BY area, fraud_channel", params
        ):
            channels_by_area.setdefault(r["area"], {})[r["fraud_channel"]] = r["n"]

        # Citywide totals over the same window.
        city_victims = _scalar(
            conn,
            "SELECT COUNT(*) FROM complaints "
            f"WHERE {_CYBER_WHERE}{flt}", tuple(params))
        city_amount = _scalar(
            conn,
            "SELECT COALESCE(SUM(amount_lost), 0) FROM complaints "
            f"WHERE {_CYBER_WHERE}{flt}", tuple(params))
        top_channels = _counts(
            conn,
            "SELECT fraud_channel, COUNT(*) FROM complaints "
            f"WHERE {_CYBER_WHERE} AND fraud_channel IS NOT NULL "
            f"AND fraud_channel != ''{flt} "
            "GROUP BY fraud_channel ORDER BY COUNT(*) DESC LIMIT 3", tuple(params))

    areas = []
    for name, (lat, lng) in AREAS.items():
        cat_key = top_cat.get(name)
        cat_label = (
            CYBER_CATEGORIES.get(cat_key, {}).get("label") if cat_key else None)
        areas.append({
            "area": name, "lat": lat, "lng": lng,
            "victim_count": victims.get(name, 0),
            "total_amount_lost": round(amounts.get(name, 0) or 0, 2),
            "top_category": cat_key,
            "top_category_label": cat_label,
            "fraud_channels": channels_by_area.get(name, {}),
        })

    return {
        "center": {"lat": AHMEDABAD_CENTER[0], "lng": AHMEDABAD_CENTER[1]},
        "areas": areas,
        "channels": list(FRAUD_CHANNELS),
        "citywide": {
            "total_amount_lost": round(city_amount or 0, 2),
            "total_victims": city_victims,
            "top_channels": top_channels,
        },
        "filters": {"days": days},
    }
