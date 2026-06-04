"""Admin data export: a WAL-safe SQLite backup (optionally bundling
thumbnails) and CSV dumps of cases, complaints, and the audit log.

Admin-only; every download is recorded in the audit trail with
``action='export'`` so exfiltration of the case database leaves a footprint.
The backup uses sqlite3's online ``.backup()`` API so it is consistent even
while the app is writing (WAL mode), and the temp copy is cleaned up after the
response is streamed.
"""
from __future__ import annotations

import csv
import io
import logging
import os
import sqlite3
import tempfile
import zipfile

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask

from ..config import get_settings
from ..database import get_conn
from ..platform import service as platform_svc
from ..platform.security import require_role

log = logging.getLogger("visionscan.export")

export_router = APIRouter(prefix="/admin/export", tags=["admin-export"])

# Skip bundling the thumbnails dir when it is larger than this (a backup is
# meant to be downloadable, not a multi-GB blob); a note file records the skip.
_THUMBS_MAX_BYTES = 500 * 1024 * 1024


def _audit_export(user: dict, what: str) -> None:
    platform_svc.audit(user["id"], "export", "system", None, what)


def _audit_export_failed(user: dict, what: str, err: Exception) -> None:
    """Record a failed/aborted export so the audit trail has no blind spot —
    an attacker can't hide bulk-export attempts behind operations that error
    out (disk full, SQL error, temp-file race, etc.)."""
    try:
        platform_svc.audit(
            user["id"], "export", "system", None,
            f"{what} FAILED: {type(err).__name__}: {err}",
        )
    except Exception:  # pragma: no cover - never mask the original error
        log.warning("could not audit failed export %s", what, exc_info=True)


def _dir_size(path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


# ------------------------------------------------------------------- backup
@export_router.get("/backup.zip")
def export_backup(
    thumbs: int = 0, user: dict = Depends(require_role("admin"))
) -> FileResponse:
    what = "backup.zip" + ("+thumbs" if thumbs else "")
    try:
        return _build_backup(thumbs, user, what)
    except Exception as e:
        _audit_export_failed(user, what, e)
        raise


def _build_backup(thumbs: int, user: dict, what: str) -> FileResponse:
    settings = get_settings()
    db_path = settings.db_path

    # WAL-safe online backup into a temp .db file.
    tmp_db_fd, tmp_db_path = tempfile.mkstemp(suffix=".db", prefix="vs-backup-")
    os.close(tmp_db_fd)
    src = sqlite3.connect(str(db_path))
    try:
        dst = sqlite3.connect(tmp_db_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    # Zip the snapshot (+ optionally the thumbnails dir, size-guarded).
    tmp_zip_fd, tmp_zip_path = tempfile.mkstemp(suffix=".zip", prefix="vs-backup-")
    os.close(tmp_zip_fd)
    try:
        with zipfile.ZipFile(tmp_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmp_db_path, "visionscan.db")
            if thumbs:
                thumbs_dir = settings.thumbnails_dir
                if thumbs_dir.is_dir() and _dir_size(thumbs_dir) <= _THUMBS_MAX_BYTES:
                    for root, _dirs, files in os.walk(thumbs_dir):
                        for name in files:
                            full = os.path.join(root, name)
                            rel = os.path.relpath(full, thumbs_dir)
                            zf.write(full, os.path.join("thumbnails", rel))
                else:
                    zf.writestr(
                        "thumbnails/SKIPPED.txt",
                        "Thumbnails were omitted from this backup because the "
                        "directory exceeds the 500MB export cap (or is "
                        "unavailable). Copy the data/thumbnails directory "
                        "directly if you need the images.\n",
                    )
    finally:
        # The snapshot .db is no longer needed once it is inside the zip.
        try:
            os.remove(tmp_db_path)
        except OSError:
            pass

    _audit_export(user, what)

    def _cleanup() -> None:
        try:
            os.remove(tmp_zip_path)
        except OSError:
            pass

    return FileResponse(
        tmp_zip_path,
        media_type="application/zip",
        filename="visionscan-backup.zip",
        background=BackgroundTask(_cleanup),
    )


# --------------------------------------------------------------------- CSVs
def _csv_response(rows, header: list[str], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@export_router.get("/cases.csv")
def export_cases(user: dict = Depends(require_role("admin"))) -> StreamingResponse:
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT c.id, c.title, c.status, c.severity, c.priority, "
                "c.citizen_visible, c.verdict, c.created_at, c.updated_at, "
                "u.name AS creator, t.name AS team "
                "FROM cases c "
                "LEFT JOIN users u ON u.id = c.created_by "
                "LEFT JOIN teams t ON t.id = c.assigned_team_id "
                "ORDER BY c.id"
            ).fetchall()
        header = [
            "id", "title", "status", "severity", "priority", "citizen_visible",
            "verdict", "created_at", "updated_at", "creator", "team",
        ]
        resp = _csv_response((tuple(r) for r in rows), header, "cases.csv")
    except Exception as e:
        _audit_export_failed(user, "cases.csv", e)
        raise
    _audit_export(user, "cases.csv")
    return resp


@export_router.get("/complaints.csv")
def export_complaints(
    user: dict = Depends(require_role("admin"))
) -> StreamingResponse:
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id, title, category, location, area, lat, lng, "
                "severity, priority, status, case_id, created_at, updated_at "
                "FROM complaints ORDER BY id"
            ).fetchall()
        header = [
            "id", "title", "category", "location", "area", "lat", "lng",
            "severity", "priority", "status", "case_id", "created_at", "updated_at",
        ]
        resp = _csv_response((tuple(r) for r in rows), header, "complaints.csv")
    except Exception as e:
        _audit_export_failed(user, "complaints.csv", e)
        raise
    _audit_export(user, "complaints.csv")
    return resp


@export_router.get("/audit.csv")
def export_audit(user: dict = Depends(require_role("admin"))) -> StreamingResponse:
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id, actor_id, action, entity, entity_id, detail, created_at "
                "FROM audit_log ORDER BY id"
            ).fetchall()
        header = [
            "id", "actor_id", "action", "entity", "entity_id", "detail", "created_at",
        ]
        resp = _csv_response((tuple(r) for r in rows), header, "audit.csv")
    except Exception as e:
        _audit_export_failed(user, "audit.csv", e)
        raise
    _audit_export(user, "audit.csv")
    return resp


# ----------------------------------------- predictive-policing CSVs (officer)
# These two are operational artefacts an officer takes into the field: the
# ranked risk table and the optimized patrol plan. They are officer-gated
# (lower bar than the admin DB dumps above) but still leave an audit footprint.
def _top_contributions(contrib: dict, k: int = 3) -> str:
    """Render an area's score decomposition into one human-readable cell:
    "prior 4; murder 66; assault 23". Picks the prior + top-k recent categories
    + any anomaly boost, biggest-first."""
    parts: list[tuple[str, float]] = []
    if contrib.get("prior"):
        parts.append(("prior", float(contrib["prior"])))
    for cat, val in (contrib.get("recent_by_category") or {}).items():
        parts.append((cat, float(val)))
    if contrib.get("anomaly_boost"):
        parts.append(("anomaly_boost", float(contrib["anomaly_boost"])))
    parts.sort(key=lambda kv: -kv[1])
    return "; ".join(f"{name} {round(val)}" for name, val in parts[:k] if val)


@export_router.get("/risk.csv")
def export_risk(user: dict = Depends(require_role("officer"))) -> StreamingResponse:
    """Ranked locality risk table (area, risk, band, trend, top contributions)."""
    try:
        # Imported lazily so the predictive module never loads at export import.
        from ..platform.predictive import compute_risk

        areas = compute_risk()
        header = ["rank", "area", "lat", "lng", "risk_score", "risk_band",
                  "predicted_score", "trend", "n_reports_used",
                  "top_contributions"]
        rows = [
            (i + 1, a["area"], a["lat"], a["lng"], a["risk_score"],
             a["risk_band"], a["predicted_score"], a["trend"],
             a.get("n_reports_used", 0),
             _top_contributions(a.get("contributions") or {}))
            for i, a in enumerate(areas)
        ]
        resp = _csv_response(rows, header, "risk.csv")
    except Exception as e:
        _audit_export_failed(user, "risk.csv", e)
        raise
    _audit_export(user, "risk.csv")
    return resp


@export_router.get("/patrol-plan.csv")
def export_patrol_plan(
    units: int = 2, max_stops: int = 12,
    user: dict = Depends(require_role("officer")),
) -> StreamingResponse:
    """Optimized patrol plan flattened to one stop per row
    (unit, stop order, area, lat, lng, risk, eta)."""
    try:
        # Lazy import: reuse the live route optimizer, never duplicate the TSP.
        from ..platform.patrol import patrol_routes

        plan = patrol_routes(units=units, max_stops=max_stops)
        station = plan.get("station") or {}
        header = ["unit", "stop_order", "area", "lat", "lng", "risk_score",
                  "risk_band", "unit_distance_km", "unit_eta_min"]
        rows = []
        for rt in plan.get("routes", []):
            for order, wp in enumerate(rt.get("waypoints", []), start=1):
                rows.append((
                    rt["unit"], order, wp["area"], wp["lat"], wp["lng"],
                    wp.get("risk_score"), wp.get("risk_band"),
                    rt.get("distance_km"), rt.get("eta_min"),
                ))
        # Leading station row gives the plan an explicit depot/origin.
        if station:
            rows.insert(0, (
                0, 0, station.get("name", "Station"),
                station.get("lat"), station.get("lng"), "", "", "", "",
            ))
        resp = _csv_response(rows, header, "patrol-plan.csv")
    except Exception as e:
        _audit_export_failed(user, "patrol-plan.csv", e)
        raise
    _audit_export(user, "patrol-plan.csv")
    return resp
