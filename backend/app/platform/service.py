"""Cross-cutting platform logic: case access control, audit trail, and
notifications (in-app + hybrid email)."""
from __future__ import annotations

from fastapi import HTTPException, status

from ..database import get_conn
from . import email as email_svc
from .security import role_rank


# ---------------- audit ----------------
def audit(actor_id, action: str, entity: str, entity_id, detail: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (actor_id, action, entity, entity_id, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            (actor_id, action, entity, entity_id, detail),
        )


# ---------------- notifications ----------------
def notify(user_id: int, ntype: str, message: str, case_id=None,
           complaint_id=None, link: str | None = None,
           email: bool = False) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO notifications (user_id, type, message, case_id, "
            "complaint_id, link) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, ntype, message, case_id, complaint_id, link),
        )
        if email:
            row = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
    if email and row:
        email_svc.send_email(row["email"], f"CityShield: {ntype}", message)


def notify_admins(ntype: str, message: str, **kw) -> None:
    with get_conn() as conn:
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM users WHERE role = 'admin' AND active = 1")]
    for uid in ids:
        notify(uid, ntype, message, **kw)


def notify_case_members(case_id: int, ntype: str, message: str, exclude=None,
                        email: bool = False) -> None:
    with get_conn() as conn:
        ids = [r["user_id"] for r in conn.execute(
            "SELECT user_id FROM case_assignments WHERE case_id = ?", (case_id,))]
    for uid in ids:
        if uid != exclude:
            notify(uid, ntype, message, case_id=case_id, email=email)


def notify_team(team_id: int, ntype: str, message: str, **kw) -> None:
    if not team_id:
        return
    with get_conn() as conn:
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM users WHERE team_id = ? AND active = 1", (team_id,))]
    for uid in ids:
        notify(uid, ntype, message, **kw)


# ---------------- case access control ----------------
def can_access_case(user: dict, case: dict) -> bool:
    if user["role"] == "admin":
        return True
    uid = user["id"]
    if role_rank(user["role"]) >= role_rank("officer"):
        # assigned to the case, or member of the case's team
        with get_conn() as conn:
            assigned = conn.execute(
                "SELECT 1 FROM case_assignments WHERE case_id = ? AND user_id = ?",
                (case["id"], uid),
            ).fetchone()
        if assigned:
            return True
        if case.get("assigned_team_id") and user.get("team_id") == case["assigned_team_id"]:
            return True
        return False
    # citizen
    return bool(case.get("citizen_id") == uid and case.get("citizen_visible"))


def get_case_or_403(user: dict, case_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    case = dict(row)
    if not can_access_case(user, case):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this case")
    return case


def evidence_visible_to(user: dict, case: dict, visibility: str) -> bool:
    """Citizens see only citizen-tagged evidence on a citizen-visible case;
    staff with case access see everything."""
    if role_rank(user["role"]) >= role_rank("officer"):
        return True
    return visibility == "citizen" and bool(case.get("citizen_visible"))
