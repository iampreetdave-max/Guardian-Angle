"""Anomaly watch API — the admin-facing surface of the always-on detector.

Events are produced by the pipeline (services/anomaly_events.py); this router
lists them as pinned alert cards and lets staff acknowledge or dismiss them.
Staff-only: anomaly alerts are operational intelligence, never citizen-facing.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..database import get_conn
from ..platform import service as platform_svc
from ..platform.security import require_role

anomaly_router = APIRouter()

_STATUSES = {"new", "acknowledged", "dismissed"}

_CARD_SQL = """
SELECT a.id, a.type, a.confidence, a.source, a.status, a.peak_count,
       a.last_ts_sec, a.created_at, a.updated_at,
       a.video_id, a.frame_id, a.x1, a.y1, a.x2, a.y2,
       v.camera_id, v.filename, v.status AS video_status,
       f.thumbnail_path
FROM anomaly_events a
JOIN videos v ON v.id = a.video_id
LEFT JOIN frames f ON f.id = a.frame_id
"""


def _card(row) -> dict:
    d = dict(row)
    d["camera"] = d.get("camera_id") or d.get("filename") or f"feed {d['video_id']}"
    d["thumbnail_url"] = (
        f"/thumbnails/{d['thumbnail_path']}" if d.get("thumbnail_path") else None
    )
    d["is_live"] = d.pop("video_status", None) == "live"
    d.pop("thumbnail_path", None)
    d.pop("filename", None)
    return d


@anomaly_router.get("/anomalies", tags=["anomaly"])
def list_anomalies(
    status_filter: str | None = "new",
    type: str | None = None,
    limit: int = 50,
    user: dict = Depends(require_role("officer")),
) -> list[dict]:
    """Pinned alert cards, newest first. status_filter=all returns everything."""
    limit = max(1, min(limit, 200))
    clauses, params = [], []
    if status_filter and status_filter != "all":
        if status_filter not in _STATUSES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status")
        clauses.append("a.status = ?")
        params.append(status_filter)
    if type:
        clauses.append("a.type = ?")
        params.append(type)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"{_CARD_SQL} {where} ORDER BY a.updated_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
    return [_card(r) for r in rows]


@anomaly_router.get("/anomalies/summary", tags=["anomaly"])
def anomaly_summary(user: dict = Depends(require_role("officer"))) -> dict:
    """Counts for the header ticker badge: new total + per-type breakdown."""
    with get_conn() as conn:
        by_type = {
            r["type"]: r["n"]
            for r in conn.execute(
                "SELECT type, COUNT(*) AS n FROM anomaly_events "
                "WHERE status = 'new' GROUP BY type"
            )
        }
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM anomaly_events"
        ).fetchone()["n"]
    return {"new": sum(by_type.values()), "by_type": by_type, "total": total}


def _set_status(event_id: int, new_status: str, user: dict) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, status FROM anomaly_events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
        conn.execute(
            "UPDATE anomaly_events SET status = ?, updated_at = datetime('now') "
            "WHERE id = ?",
            (new_status, event_id),
        )
    platform_svc.audit(user["id"], f"anomaly_{new_status}", "anomaly_event",
                       event_id)
    return {"id": event_id, "status": new_status}


@anomaly_router.post("/anomalies/{event_id}/ack", tags=["anomaly"])
def acknowledge(event_id: int,
                user: dict = Depends(require_role("officer"))) -> dict:
    return _set_status(event_id, "acknowledged", user)


@anomaly_router.post("/anomalies/{event_id}/dismiss", tags=["anomaly"])
def dismiss(event_id: int,
            user: dict = Depends(require_role("officer"))) -> dict:
    return _set_status(event_id, "dismissed", user)
