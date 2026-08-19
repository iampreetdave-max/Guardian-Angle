"""Scene analytics: aggregates the tracking and zone routers.

Everything under here is computed from detections the ingest pipeline already
stored — no video is re-decoded and no model is re-run — so these routes are
cheap and cannot disturb the detection path.

This module only composes; the two feature routers are developed independently.
"""
from __future__ import annotations

from fastapi import APIRouter

from .tracking_routes import router as tracking_router
from .zone_routes import router as zone_router

router = APIRouter()
router.include_router(tracking_router)
router.include_router(zone_router)
