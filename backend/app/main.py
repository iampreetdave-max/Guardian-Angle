"""VisionScan FastAPI application entrypoint.

Run (dev):  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

# On Windows, torch (Intel OpenMP) and faiss (LLVM OpenMP) each link their own
# OpenMP runtime, which aborts at import with "OMP: Error #15". Allowing the
# duplicate is the accepted workaround; it does not occur on the Linux Docker
# build. Must be set before torch/faiss are imported.
import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .config import get_settings
from .database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

settings = get_settings()

app = FastAPI(
    title="VisionScan API",
    description="AI-powered CCTV analysis system for investigation.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Security middleware stack. FastAPI runs the LAST add_middleware first, so
# adding Lockdown → RateLimit → Metrics → SecurityHeaders yields the intended
# onion: SecurityHeaders outermost (headers on every response, including 429s
# and 423s), then Metrics, RateLimit, Lockdown innermost.
from .security_mw import (  # noqa: E402
    LockdownMiddleware, MetricsMiddleware, RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
app.add_middleware(LockdownMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


@app.on_event("startup")
def _startup() -> None:
    settings.assert_secure()  # refuse prod auth mode on the dev JWT secret
    settings.ensure_dirs()
    init_db()
    log = logging.getLogger("visionscan")
    log.info("VisionScan ready · device=%s · data=%s",
             settings.resolve_device(), settings.data_dir)

    # Warm models in the background so the first search / live frame is fast
    # rather than stalling ~30s on lazy load.
    def _warm() -> None:
        from .core import anomaly, detection, embedding
        try:
            embedding.warmup()
        except Exception:
            log.warning("CLIP warmup failed", exc_info=True)
        try:
            detection.warmup()
        except Exception:
            log.warning("detector warmup failed", exc_info=True)
        try:
            anomaly.warmup()  # pre-embed the anomaly prompt bank
        except Exception:
            log.warning("anomaly warmup failed", exc_info=True)
        log.info("Model warmup complete")

    import threading
    threading.Thread(target=_warm, daemon=True).start()

    # Opt-in: poll the free government RSS feeds hourly so subscribers get
    # fresh GR/notification alerts without a manual refresh. Off by default
    # (no surprise network calls); the admin "Refresh feeds" button always works.
    if getattr(settings, "govintel_auto_refresh", False):
        def _gov_poll() -> None:
            import time
            from .govintel import service as gov_service
            while True:
                try:
                    gov_service.refresh()
                except Exception:
                    log.warning("GovIntel auto-refresh failed", exc_info=True)
                time.sleep(3600)
        threading.Thread(target=_gov_poll, daemon=True).start()
        log.info("GovIntel hourly auto-refresh enabled")


# Serve keyframe thumbnails as static files (referenced by SearchHit.thumbnail_url)
app.mount(
    "/thumbnails",
    StaticFiles(directory=str(settings.thumbnails_dir)),
    name="thumbnails",
)

app.include_router(router, prefix="/api")

# Anomaly watch — always-on incident alerts from the CCTV pipeline
from .api.anomaly_routes import anomaly_router  # noqa: E402
app.include_router(anomaly_router, prefix="/api")

# Scene analytics: tracking, zone occupancy, line crossings.
from .api.analytics_routes import router as scene_router  # noqa: E402
app.include_router(scene_router, prefix="/api")

# Admin ops: server monitoring + emergency lockdown, and data export/backup
from .api.admin_system import admin_system_router  # noqa: E402
from .api.export_routes import export_router  # noqa: E402
app.include_router(admin_system_router, prefix="/api")
app.include_router(export_router, prefix="/api")

# Arbiter legal-intelligence module (CityShield) — modular, under /api/legal/*
from .arbiter.routes import router as legal_router  # noqa: E402
app.include_router(legal_router, prefix="/api/legal")

# GovIntel — Unified Legal & Government Intelligence, modular, under /api/gov/*
from .govintel.routes import router as gov_router  # noqa: E402
app.include_router(gov_router, prefix="/api/gov")

# CrimeGPT — AI crime documentation automation, modular, under /api/crimegpt/*
from .crimegpt.routes import router as crimegpt_router  # noqa: E402
app.include_router(crimegpt_router, prefix="/api/crimegpt")

# CityShield platform: auth, users/teams, complaints, cases, notifications
from .platform.routes import (  # noqa: E402
    admin_router, auth_router, cases_router, complaints_router, notif_router,
)
from .platform.analytics import analytics_router  # noqa: E402
from .platform.predictive import predict_router  # noqa: E402
from .platform.patrol import patrol_router  # noqa: E402
app.include_router(predict_router, prefix="/api/predict")
app.include_router(patrol_router, prefix="/api/predict")
app.include_router(auth_router, prefix="/api/auth")
app.include_router(admin_router, prefix="/api")
app.include_router(complaints_router, prefix="/api/complaints")
app.include_router(cases_router, prefix="/api/cases")
app.include_router(notif_router, prefix="/api/notifications")
app.include_router(analytics_router, prefix="/api/analytics")


# ---- Optional: serve the built React frontend from the same container ----
# In single-container deployments (Hugging Face Spaces, `docker run` of the
# combined image) the Vite build is copied to backend/app/static. When present,
# we serve it at "/"; otherwise the root returns a small JSON banner and the
# frontend is expected to run separately (local dev via Vite on :5173).
import os
from pathlib import Path as _Path

_STATIC_DIR = _Path(os.getenv("VISIONSCAN_STATIC_DIR", _Path(__file__).parent / "static"))

if _STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="frontend")
else:
    @app.get("/")
    def root() -> dict:
        return {"service": "VisionScan", "docs": "/docs", "api": "/api"}
