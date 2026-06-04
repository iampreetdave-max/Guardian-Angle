"""Anomaly event persistence — debounced incident records + admin alerting.

A burning car produces dozens of consecutive "fire" keyframes; the admin wants
ONE pinned alert that grows, not a flood. So signals are grouped per
(video_id, type): a new signal lands on the most recent open event when its
last grouped frame is within anomaly_event_gap_sec, otherwise it opens a new
event. This is the persisted twin of the temporal event grouping the search
layer does in query_router.

Only a NEWLY created event on a LIVE feed pings the admins (and only above
anomaly_notify_threshold) — uploads of historical footage are reviewed in the
Live Alerts panel without notification noise.
"""
from __future__ import annotations

import logging

from ..config import get_settings
from ..core.anomaly import AnomalySignal
from ..database import get_conn
from ..platform import service as platform_svc

log = logging.getLogger("visionscan.anomaly")


def record_signals(video_id: int, frame_id: int, timestamp_sec: float,
                   signals: list[AnomalySignal], is_live: bool) -> list[int]:
    """Persist signals with debouncing. Returns ids of newly created events."""
    if not signals:
        return []
    settings = get_settings()
    created: list[int] = []

    for sig in signals:
        with get_conn() as conn:
            recent = conn.execute(
                "SELECT id, confidence, last_ts_sec FROM anomaly_events "
                "WHERE video_id = ? AND type = ? "
                "ORDER BY id DESC LIMIT 1",
                (video_id, sig.type),
            ).fetchone()

            grouped = (
                recent is not None
                and recent["last_ts_sec"] is not None
                and 0 <= timestamp_sec - recent["last_ts_sec"]
                       <= settings.anomaly_event_gap_sec
            )
            if grouped:
                conn.execute(
                    "UPDATE anomaly_events SET "
                    "confidence = MAX(confidence, ?), "
                    "peak_count = peak_count + 1, "
                    "last_ts_sec = ?, frame_id = ?, "
                    "updated_at = datetime('now') WHERE id = ?",
                    (sig.confidence, timestamp_sec, frame_id, recent["id"]),
                )
            else:
                bbox = sig.bbox or (None, None, None, None)
                cur = conn.execute(
                    "INSERT INTO anomaly_events (video_id, frame_id, type, "
                    "confidence, source, x1, y1, x2, y2, last_ts_sec) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (video_id, frame_id, sig.type, sig.confidence, sig.source,
                     *bbox, timestamp_sec),
                )
                created.append(cur.lastrowid)
                event_id = cur.lastrowid

        if not grouped:
            _maybe_notify(event_id, video_id, sig, is_live, settings)
            # Closed-loop response: a NEW event on a LIVE feed auto-spawns a
            # geo-tagged case + dispatches the nearest unit. Fail-soft and
            # env-gated (VISIONSCAN_AUTO_CASE) inside the loop; ingestion is
            # never blocked. Historical uploads (is_live=False) are unaffected.
            if is_live:
                try:
                    from .incident_loop import handle_new_event

                    handle_new_event(event_id)
                except Exception:  # never let the closed loop break capture
                    log.warning("incident loop dispatch failed", exc_info=True)
    return created


def _maybe_notify(event_id: int, video_id: int, sig: AnomalySignal,
                  is_live: bool, settings) -> None:
    if not is_live or sig.confidence < settings.anomaly_notify_threshold:
        return
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT camera_id, filename FROM videos WHERE id = ?",
                (video_id,),
            ).fetchone()
        camera = (row["camera_id"] or row["filename"]) if row else f"feed {video_id}"
        platform_svc.notify_admins(
            "anomaly",
            f"{sig.type.upper()} detected on {camera} "
            f"({sig.confidence * 100:.0f}% · {sig.source})",
            link=f"/?module=alerts&event={event_id}",
        )
    except Exception:  # never let alerting break the capture loop
        log.warning("anomaly admin notification failed", exc_info=True)
