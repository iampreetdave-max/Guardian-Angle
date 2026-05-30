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


def seed_demo() -> None:
    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        if n > 0:
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
