"""Closed-loop incident response — a live CCTV anomaly becomes action.

One detection lights up four modules:
  1. Cases       — the event is auto-converted into a geo-tagged case (same
                   code path complaint->case conversion uses).
  2. City Map    — the case inherits the camera's Ahmedabad locality, so it
                   plots immediately and bumps that area's risk surface.
  3. Patrol      — the nearest patrol unit is dispatched (haversine over the
                   units' latest check-in positions; see patrol.nearest_unit).
  4. Notifications — that officer gets a high-priority DISPATCH ping linking
                   straight to the new case.

Triggered fail-soft from anomaly_events.record_signals(), only for a NEW event
on a LIVE feed, after the existing admin notify. Every step is wrapped so a
failure here can NEVER break ingestion — mirrors the _maybe_notify philosophy.

Env-gated by VISIONSCAN_AUTO_CASE (default ON). Set it to a falsey value
(0/false/no/off) to disable the auto-case/dispatch loop entirely.
"""
from __future__ import annotations

import logging
import os

from ..database import get_conn
from ..platform import service as platform_svc

log = logging.getLogger("visionscan.anomaly")

# type -> case severity (cases.severity enum: low|medium|high|critical).
# Armed/violent threats are critical; fire/accident high; smoke a medium watch.
_SEVERITY_BY_TYPE = {
    "weapon": "critical",
    "violence": "critical",
    "fire": "high",
    "accident": "high",
    "smoke": "medium",
}
# cases.priority is 1 (highest) .. 5; pair it with severity so the dispatch
# queue and case list sort sensibly.
_PRIORITY_BY_SEVERITY = {"critical": 1, "high": 2, "medium": 3, "low": 4}

# Seed-independent system actor for AI-created records (get-or-create at runtime).
_AI_EMAIL = "visionscan-ai@cityshield.local"
_AI_NAME = "VisionScan AI"


def _auto_case_enabled() -> bool:
    """VISIONSCAN_AUTO_CASE gate, default ON. Read from env so we never need to
    touch the shared Settings model another agent owns."""
    raw = os.environ.get("VISIONSCAN_AUTO_CASE")
    if raw is None:
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _get_or_create_ai_user(conn) -> int:
    """Return the id of the system 'visionscan-ai' user, creating it if absent.

    Idempotent and seed-independent: the platform may or may not have seeded
    demo users, so we never assume an admin id. The account is inactive and
    holds a random unusable password hash (it never logs in)."""
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?", (_AI_EMAIL,)
    ).fetchone()
    if row is not None:
        return row["id"]
    # Lazy import keeps this module importable without the security stack.
    from ..platform.security import hash_password
    import secrets

    return conn.execute(
        "INSERT INTO users (name, email, password_hash, role, active) "
        "VALUES (?, ?, ?, 'admin', 0)",
        (_AI_NAME, _AI_EMAIL, hash_password(secrets.token_urlsafe(24))),
    ).lastrowid


def handle_new_event(event_id: int, conn=None) -> int | None:
    """Auto-create a case + dispatch for one freshly created live anomaly event.

    Returns the new case id (or the existing one on a dedupe hit), or None when
    skipped (disabled, no area, etc.). Fully fail-soft: any exception is logged
    and swallowed so the capture loop is never disturbed. ``conn`` is accepted
    for symmetry but the loop manages its own short transactions to keep the
    caller's connection untouched.
    """
    if not _auto_case_enabled():
        return None
    try:
        return _run(event_id)
    except Exception:  # never let the closed loop break ingestion
        log.warning("incident loop failed for event %s", event_id, exc_info=True)
        return None


def _run(event_id: int) -> int | None:
    with get_conn() as conn:
        ev = conn.execute(
            "SELECT a.id, a.type, a.confidence, a.source, a.frame_id, "
            "a.case_id, a.created_at, a.video_id, v.area, v.camera_id, v.filename "
            "FROM anomaly_events a JOIN videos v ON v.id = a.video_id "
            "WHERE a.id = ?",
            (event_id,),
        ).fetchone()
        if ev is None:
            return None

        # Dedupe: grouped updates within the debounce window keep the same row;
        # if it already spawned a case, never create a second one.
        if ev["case_id"]:
            return ev["case_id"]

        area = ev["area"]
        if not area:
            # Untagged camera — nothing to geo-locate against. Skip quietly;
            # the alert still appears in the Live Alerts panel as before.
            log.info("incident loop: event %s on untagged feed %s — no auto-case",
                     event_id, ev["video_id"])
            return None

        atype = ev["type"]
        severity = _SEVERITY_BY_TYPE.get(atype, "medium")
        priority = _PRIORITY_BY_SEVERITY.get(severity, 3)
        ai_id = _get_or_create_ai_user(conn)

        camera = ev["camera_id"] or ev["filename"] or f"feed {ev['video_id']}"
        title = f"AUTO: {atype.upper()} detected at {area}"
        description = (
            f"Automated incident from the always-on CCTV anomaly watch.\n"
            f"Type: {atype} · confidence {ev['confidence'] * 100:.0f}% "
            f"(via {ev['source']})\n"
            f"Camera: {camera} · Area: {area}\n"
            f"Detected: {ev['created_at']} (anomaly event #{event_id})"
        )

        # Same INSERT shape the complaint->case conversion uses (routes.py):
        # cases(title, description, complaint_id, created_by, assigned_team_id,
        #       severity, priority, citizen_id). Origin is AI/system; no
        # complaint, no citizen, no team (officer is dispatched directly).
        case_id = conn.execute(
            "INSERT INTO cases (title, description, complaint_id, created_by, "
            "assigned_team_id, status, severity, priority, citizen_id) "
            "VALUES (?, ?, NULL, ?, NULL, 'open', ?, ?, NULL)",
            (title, description, ai_id, severity, priority),
        ).lastrowid

        # Attach the keyframe as evidence when one exists (schema supports it).
        if ev["frame_id"]:
            conn.execute(
                "INSERT INTO evidence (case_id, kind, ref, caption, visibility, "
                "added_by) VALUES (?, 'frame', ?, ?, 'team', ?)",
                (case_id, str(ev["frame_id"]),
                 f"Anomaly keyframe — {atype} {ev['confidence'] * 100:.0f}%",
                 ai_id),
            )

        # Backfill the link onto the event (dedupe anchor for later updates).
        conn.execute(
            "UPDATE anomaly_events SET case_id = ?, updated_at = datetime('now') "
            "WHERE id = ?",
            (case_id, event_id),
        )

        # Nearest-unit dispatch (runs inside this same transaction).
        from ..platform.patrol import nearest_unit_to_area

        unit = nearest_unit_to_area(area, conn=conn)

    # --- post-commit side effects (own transactions; never abort the case) ---
    platform_svc.audit(ai_id, "anomaly_auto_case", "case", case_id,
                       f"{atype}@{area}")

    if unit:
        dist = (f" ({unit['distance_km']} km away)"
                if unit.get("distance_km") is not None else "")
        platform_svc.notify(
            unit["id"], "dispatch",
            f"DISPATCH: {atype} at {area} — auto-case #{case_id}{dist}",
            case_id=case_id,
            link=f"/?module=cases&case={case_id}",
        )
        # Auto-assign the dispatched officer to the case so it shows on their
        # board immediately (matches create_case's creator-auto-assign).
        with get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO case_assignments (case_id, user_id, "
                "role_on_case) VALUES (?, ?, 'responder')",
                (case_id, unit["id"]),
            )
    else:
        log.info("incident loop: no patrol unit available to dispatch for "
                 "case %s (%s @ %s)", case_id, atype, area)

    return case_id
