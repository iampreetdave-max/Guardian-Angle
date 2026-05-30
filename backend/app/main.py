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
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    settings.ensure_dirs()
    init_db()
    logging.getLogger("visionscan").info(
        "VisionScan ready · device=%s · data=%s",
        settings.resolve_device(), settings.data_dir,
    )


# Serve keyframe thumbnails as static files (referenced by SearchHit.thumbnail_url)
app.mount(
    "/thumbnails",
    StaticFiles(directory=str(settings.thumbnails_dir)),
    name="thumbnails",
)

app.include_router(router, prefix="/api")


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
