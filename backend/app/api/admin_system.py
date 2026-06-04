"""Admin system console: live host/model telemetry, emergency lockdown switch,
and a security-event review feed. Admin-only.

Every endpoint requires the `admin` role. The system snapshot is fail-soft:
optional dependencies (psutil, the security middleware module, the FAISS index)
are imported lazily inside try/except so a missing piece degrades to ``null``
fields rather than a 500.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..config import get_settings
from ..core import detection, embedding
from ..database import get_conn
from ..platform import service as platform_svc
from ..platform.security import require_role

log = logging.getLogger("visionscan.admin")

admin_system_router = APIRouter(prefix="/admin", tags=["admin-system"])


# --------------------------------------------------------------- system status
def _host_metrics() -> dict:
    """CPU / RAM / disk via psutil, or nulls when psutil is unavailable."""
    out: dict = {
        "cpu_percent": None,
        "mem_percent": None,
        "mem_used_mb": None,
        "mem_total_mb": None,
        "disk_used_gb": None,
        "disk_total_gb": None,
        "disk_percent": None,
    }
    try:
        import psutil  # type: ignore

        settings = get_settings()
        out["cpu_percent"] = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        out["mem_percent"] = vm.percent
        out["mem_used_mb"] = round(vm.used / (1024 * 1024), 1)
        out["mem_total_mb"] = round(vm.total / (1024 * 1024), 1)
        du = psutil.disk_usage(str(settings.data_dir))
        out["disk_used_gb"] = round(du.used / (1024 ** 3), 2)
        out["disk_total_gb"] = round(du.total / (1024 ** 3), 2)
        out["disk_percent"] = du.percent
    except Exception:  # pragma: no cover - psutil optional / platform quirks
        log.debug("psutil metrics unavailable", exc_info=True)
    return out


def _db_size_mb() -> float | None:
    try:
        return round(get_settings().db_path.stat().st_size / (1024 * 1024), 2)
    except Exception:
        return None


def _index_size() -> int | None:
    try:
        from ..core.index import get_clip_index

        return int(get_clip_index().ntotal)
    except Exception:
        return None


def _runtime_metrics() -> dict:
    """Uptime + request/error counters from the security middleware, fail-soft."""
    try:
        from ..security_mw import get_metrics

        return dict(get_metrics())
    except Exception:
        return {}


def _lockdown_state() -> bool:
    try:
        from ..security_mw import is_lockdown

        return bool(is_lockdown())
    except Exception:
        return False


@admin_system_router.get("/system")
def system_status(_user: dict = Depends(require_role("admin"))) -> dict:
    with get_conn() as conn:
        videos = conn.execute("SELECT COUNT(*) c FROM videos").fetchone()["c"]
        cases = conn.execute("SELECT COUNT(*) c FROM cases").fetchone()["c"]
        complaints = conn.execute(
            "SELECT COUNT(*) c FROM complaints").fetchone()["c"]
        users = conn.execute(
            "SELECT COUNT(*) c FROM users WHERE active = 1").fetchone()["c"]

    return {
        "host": _host_metrics(),
        "db_size_mb": _db_size_mb(),
        "metrics": _runtime_metrics(),
        "models": {
            "clip": embedding.is_loaded(),
            "yolo": detection.yolo_available(),
            "face": detection.face_available(),
        },
        "indexed_frames": _index_size(),
        "counts": {
            "videos": videos,
            "cases": cases,
            "complaints": complaints,
            "users": users,
        },
        "lockdown": _lockdown_state(),
    }


# ------------------------------------------------------------------- lockdown
class LockdownIn(BaseModel):
    enabled: bool


@admin_system_router.post("/lockdown")
def set_lockdown_state(
    body: LockdownIn, user: dict = Depends(require_role("admin"))
) -> dict:
    enabled = bool(body.enabled)
    try:
        from ..security_mw import set_lockdown

        set_lockdown(enabled)
    except Exception:  # pragma: no cover - middleware optional / fail-soft
        log.warning("lockdown toggle could not reach middleware", exc_info=True)
    platform_svc.audit(
        user["id"],
        "lockdown_on" if enabled else "lockdown_off",
        "system",
        None,
        "emergency lockdown " + ("enabled" if enabled else "disabled"),
    )
    return {"lockdown": enabled}


# ------------------------------------------------------------ security events
_AUDIT_ACTIONS = (
    "lockdown_on", "lockdown_off", "broadcast", "logout_all", "export",
)


@admin_system_router.get("/security-events")
def security_events(_user: dict = Depends(require_role("admin"))) -> dict:
    placeholders = ",".join("?" for _ in _AUDIT_ACTIONS)
    with get_conn() as conn:
        attempts = conn.execute(
            "SELECT id, email, ip, ok, created_at FROM login_attempts "
            "ORDER BY id DESC LIMIT 100"
        ).fetchall()
        audit_rows = conn.execute(
            "SELECT a.id, a.actor_id, a.action, a.entity, a.entity_id, "
            "a.detail, a.created_at, u.name AS actor_name "
            "FROM audit_log a LEFT JOIN users u ON u.id = a.actor_id "
            f"WHERE a.action IN ({placeholders}) "
            "ORDER BY a.id DESC LIMIT 100",
            _AUDIT_ACTIONS,
        ).fetchall()
    return {
        "login_attempts": [dict(r) for r in attempts],
        "audit": [dict(r) for r in audit_rows],
    }
