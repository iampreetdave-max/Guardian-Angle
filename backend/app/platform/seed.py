"""Seed demo accounts + a team on first run, so the platform is immediately
usable (and judges can log in instantly). Controlled by settings.seed_demo_users.

Demo credentials (DEV ONLY):
    admin@city.gov    / admin123    (Admin / SHO)
    lead@city.gov     / lead123     (Team Lead)
    officer@city.gov  / officer123  (Officer)
    citizen@example.com / citizen123 (Citizen)
"""
from __future__ import annotations

import logging

from ..database import get_conn
from .security import hash_password

log = logging.getLogger("visionscan.platform.seed")

_DEMO = [
    ("Station Admin", "admin@city.gov", "admin123", "admin", "ADM-001"),
    ("Insp. R. Sharma (Lead)", "lead@city.gov", "lead123", "lead", "LD-101"),
    ("Const. A. Patel", "officer@city.gov", "officer123", "officer", "OFF-201"),
    ("Citizen User", "citizen@example.com", "citizen123", "citizen", None),
]


def _seed_synthetic() -> None:
    """Lay down the high-volume, deterministic synthetic incident stream.

    Self-gating (app_settings marker + complaints row-count < ~100 + the
    VISIONSCAN_SEED_SYNTHETIC override), so it is safe to call on every boot.
    """
    try:
        from .seed_synthetic import maybe_seed_synthetic
        maybe_seed_synthetic()
    except Exception:  # never block startup on demo data
        log.warning("synthetic incident seeding skipped", exc_info=True)


def _backfill_synthetic() -> None:
    """Top up a database that has users but no incident volume.

    Deliberately does NOT honour VISIONSCAN_SEED_SYNTHETIC. That flag means
    "force a reseed" and belongs to explicit tooling such as demo_reset, which
    sets it for the whole process — honouring it here would re-seed on every
    subsequent init_db() in that process (demo_reset calls init_db twice and
    then opens a TestClient, which fires startup a third time), stacking
    duplicate streams and inflating every metric derived from them.

    The row-count gate is the only condition that matters for a back-fill.
    """
    try:
        from ..database import get_conn
        from .seed_synthetic import AUTO_SEED_BELOW, seed_synthetic

        with get_conn() as conn:
            n = conn.execute("SELECT COUNT(*) c FROM complaints").fetchone()["c"]
        if n >= AUTO_SEED_BELOW:
            return
        seed_synthetic(force=True)
    except Exception:  # never block startup on demo data
        log.warning("synthetic incident back-fill skipped", exc_info=True)


def seed_demo() -> None:
    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        if n > 0:
            # Accounts exist, but a database created before the synthetic layer
            # landed — an upgraded Docker volume, a redeployed VM, a judge's
            # machine that ran an older build — still has no incident volume,
            # which leaves the map, analytics and backtest empty. The synthetic
            # seed gates itself, so back-filling here is idempotent and costs
            # one COUNT(*) per boot.
            _backfill_synthetic()
            return  # already seeded / has users
        tid = conn.execute(
            "INSERT INTO teams (name, station) VALUES "
            "('Cyber Investigation Unit', 'Ahmedabad Cyber Crime Branch')"
        ).lastrowid
        ids = {}
        for name, email, pw, role, badge in _DEMO:
            team = tid if role in ("officer", "lead") else None
            uid = conn.execute(
                "INSERT INTO users (name, email, password_hash, role, team_id, badge_no) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (name, email, hash_password(pw), role, team, badge),
            ).lastrowid
            ids[role] = uid
        # set the lead as the team's lead
        if "lead" in ids:
            conn.execute("UPDATE teams SET lead_user_id = ? WHERE id = ?", (ids["lead"], tid))
    log.info("Seeded demo accounts (admin/lead/officer/citizen) + 1 team")

    from ..config import get_settings
    if get_settings().seed_demo_data:
        try:
            _seed_incidents(ids.get("citizen"), ids.get("lead"), tid)
        except Exception:  # never block startup on demo data
            log.warning("incident seeding skipped", exc_info=True)


def _seed_incidents(citizen_id: int | None, lead_id: int | None, team_id: int) -> None:
    """Seed ~20 generic Ahmedabad incidents (approximations compiled from
    public NCRB/police/press reporting — see docs/AHMEDABAD_CRIME_DATA.md) as
    complaints, converting the high-severity ones into cases. Gives the City
    Map and analytics a realistic area-wise distribution on first launch."""
    if not citizen_id:
        return
    from ..constants.ahmedabad import area_centroid
    from .seed_ahmedabad import SEED_INCIDENTS

    n_cases = 0
    with get_conn() as conn:
        for i, inc in enumerate(SEED_INCIDENTS):
            centroid = area_centroid(inc["area"])
            lat, lng = centroid if centroid else (None, None)
            make_case = inc["severity"] in ("high", "critical") and lead_id
            # Deterministic spread over the last ~90 days (some fresh, some
            # old) so recency-weighted risk scoring and trend analysis have a
            # realistic time axis instead of a single "today" spike.
            age_days = (i * 11 + 2) % 90
            cid = conn.execute(
                "INSERT INTO complaints (citizen_id, title, description, "
                "category, location, area, lat, lng, severity, status, "
                "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                "datetime('now', ?))",
                (citizen_id, inc["title"], inc["description"], inc["category"],
                 f"{inc['area']}, Ahmedabad ({inc['year']})", inc["area"],
                 lat, lng, inc["severity"],
                 "converted" if make_case else "under_review",
                 f"-{age_days} days"),
            ).lastrowid
            if make_case:
                case_id = conn.execute(
                    "INSERT INTO cases (title, description, complaint_id, "
                    "created_by, assigned_team_id, status, severity, citizen_id) "
                    "VALUES (?, ?, ?, ?, ?, 'active', ?, ?)",
                    (inc["title"], inc["description"], cid, lead_id, team_id,
                     inc["severity"], citizen_id),
                ).lastrowid
                conn.execute(
                    "UPDATE complaints SET case_id = ? WHERE id = ?", (case_id, cid))
                conn.execute(
                    "INSERT INTO case_assignments (case_id, user_id, role_on_case) "
                    "VALUES (?, ?, 'lead')", (case_id, lead_id))
                n_cases += 1
    log.info("Seeded %d demo incidents (%d converted to cases) across Ahmedabad",
             len(SEED_INCIDENTS), n_cases)

    # Lay down the high-volume, deterministic synthetic stream UNDER the ~20
    # labeled incidents above (which stay as the distinguishable overlay).
    _seed_synthetic()
