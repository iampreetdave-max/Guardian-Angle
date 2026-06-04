"""CityShield platform API — auth, users/teams, complaints, cases, evidence,
documents, messages, notifications. All additive under their own prefixes.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from ..config import get_settings
from ..database import get_conn
from . import service as svc
from ..constants.ahmedabad import area_centroid
from .models import (
    AssignIn, BroadcastIn, CaseIn, ChangePasswordIn, CloseCaseIn, ComplaintIn,
    CreateUserIn, DocumentIn, EvidenceIn, ForgotPasswordIn, LoginIn, MeetingIn,
    MessageIn, RatingIn, RegisterIn, ResetPasswordIn, TeamIn, TriageIn,
    UpdateUserIn, VisibilityIn,
)
from .security import (
    create_token, get_current_user, hash_password, require_role, role_rank,
    verify_password,
)

auth_router = APIRouter()
admin_router = APIRouter()
complaints_router = APIRouter()
cases_router = APIRouter()
notif_router = APIRouter()


def _public_user(row) -> dict:
    d = dict(row)
    d.pop("password_hash", None)
    d.pop("reset_token", None)
    d.pop("reset_expires", None)
    return d


# ============================================================= AUTH
@auth_router.post("/register", tags=["auth"])
def register(body: RegisterIn) -> dict:
    """Citizen self-registration. Staff accounts are created by an admin."""
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE email = ?", (body.email,)).fetchone()
        if exists:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, role, phone) "
            "VALUES (?, ?, ?, 'citizen', ?)",
            (body.name, body.email, hash_password(body.password), body.phone),
        )
        uid = cur.lastrowid
    svc.audit(uid, "register", "user", uid, "citizen self-registration")
    # A freshly-inserted row has token_version = 0 (column default); pass it
    # explicitly so token minting stays consistent with the user's tv state.
    token = create_token(uid, "citizen", token_version=0)
    return {"token": token, "user": {"id": uid, "name": body.name,
            "email": body.email, "role": "citizen"}}


@auth_router.post("/login", tags=["auth"])
def login(body: LoginIn, request: Request) -> dict:
    s = get_settings()
    ip = request.client.host if request.client else None
    with get_conn() as conn:
        # Serialize concurrent attempts for the same email: take the DB write
        # lock up front so the count-then-insert below is atomic. Without this,
        # two requests could both read N-1 failures, both pass the check, and
        # both record a failure — overshooting the lockout threshold.
        conn.execute("BEGIN IMMEDIATE")
        # Brute-force lockout: count recent failures for this email within the
        # lockout window before doing any password work.
        recent_fails = conn.execute(
            "SELECT COUNT(*) c FROM login_attempts WHERE email = ? AND ok = 0 "
            "AND created_at >= datetime('now', ?)",
            (body.email, f"-{s.login_lockout_minutes} minutes"),
        ).fetchone()["c"]
        if recent_fails >= s.login_max_attempts:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                "Too many failed logins; try again later.")

        row = conn.execute("SELECT * FROM users WHERE email = ?", (body.email,)).fetchone()
        ok = bool(row) and verify_password(body.password, row["password_hash"])
        # Journal every attempt (success or failure) for lockout + audit review.
        conn.execute(
            "INSERT INTO login_attempts (email, ip, ok) VALUES (?, ?, ?)",
            (body.email, ip, 1 if ok else 0),
        )
        if ok:
            # Clear this email's failed rows to reset the window on success.
            conn.execute("DELETE FROM login_attempts WHERE email = ? AND ok = 0",
                         (body.email,))

    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not row["active"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    token = create_token(row["id"], row["role"], row["token_version"])
    return {"token": token, "user": _public_user(row)}


@auth_router.post("/logout", tags=["auth"])
def logout(user: dict = Depends(get_current_user)) -> dict:
    # Stateless JWT: the client discards the token. Endpoint exists for symmetry
    # and audit. (A token blocklist can be added if hard revocation is needed.)
    svc.audit(user["id"], "logout", "user", user["id"])
    return {"ok": True}


@auth_router.post("/logout-all", tags=["auth"])
def logout_all(user: dict = Depends(get_current_user)) -> dict:
    """Revoke every existing session for the caller (including the current
    token) by bumping their token_version."""
    with get_conn() as conn:
        conn.execute("UPDATE users SET token_version = token_version + 1 WHERE id = ?",
                     (user["id"],))
    svc.audit(user["id"], "logout_all", "user", user["id"])
    return {"ok": True}


@auth_router.get("/me", tags=["auth"])
def me(user: dict = Depends(get_current_user)) -> dict:
    return user


@auth_router.post("/change-password", tags=["auth"])
def change_password(body: ChangePasswordIn, user: dict = Depends(get_current_user)) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user["id"],)).fetchone()
        if not verify_password(body.current_password, row["password_hash"]):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
        # Bump token_version so any other sessions (incl. a leaked token) are
        # revoked the moment the password changes — same as reset_password.
        conn.execute(
            "UPDATE users SET password_hash = ?, "
            "token_version = token_version + 1 WHERE id = ?",
            (hash_password(body.new_password), user["id"]))
    svc.audit(user["id"], "change_password", "user", user["id"])
    return {"ok": True}


@auth_router.post("/forgot-password", tags=["auth"])
def forgot_password(body: ForgotPasswordIn, background: BackgroundTasks) -> dict:
    token = secrets.token_urlsafe(24)
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (body.email,)).fetchone()
        if row:
            conn.execute(
                "UPDATE users SET reset_token = ?, reset_expires = ? WHERE id = ?",
                (token, (datetime.utcnow() + timedelta(hours=1)).isoformat(), row["id"]),
            )
    # Always 200 (don't reveal whether the email exists). Deliver the link only
    # when the email exists, but do it AFTER the response is sent (background
    # task) so the response latency is identical in both branches — otherwise
    # the extra send_email() work leaks account existence via a timing side
    # channel.
    if row:
        from . import email as email_svc
        background.add_task(
            email_svc.send_email,
            body.email, "CityShield password reset",
            f"Use this token to reset your password (valid 1 hour): {token}",
        )
    return {"ok": True, "message": "If the email exists, a reset link has been sent."}


@auth_router.post("/reset-password", tags=["auth"])
def reset_password(body: ResetPasswordIn) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, reset_expires FROM users WHERE reset_token = ?", (body.token,)
        ).fetchone()
        if row is None or not row["reset_expires"] or \
                datetime.fromisoformat(row["reset_expires"]) < datetime.utcnow():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token")
        conn.execute(
            "UPDATE users SET password_hash = ?, reset_token = NULL, "
            "reset_expires = NULL, token_version = token_version + 1 WHERE id = ?",
            (hash_password(body.new_password), row["id"]),
        )
    svc.audit(row["id"], "reset_password", "user", row["id"])
    return {"ok": True}


# ============================================================= ADMIN: users & teams
@admin_router.get("/users", tags=["admin"])
def list_users(user: dict = Depends(require_role("admin"))) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY role DESC, name").fetchall()
    return [_public_user(r) for r in rows]


@admin_router.post("/users", tags=["admin"])
def create_user(body: CreateUserIn, user: dict = Depends(require_role("admin"))) -> dict:
    if body.role not in ("officer", "lead", "admin"):
        raise HTTPException(400, "role must be officer|lead|admin")
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (body.email,)).fetchone():
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, role, team_id, badge_no, phone) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (body.name, body.email, hash_password(body.password), body.role,
             body.team_id, body.badge_no, body.phone),
        )
        uid = cur.lastrowid
    svc.audit(user["id"], "create_user", "user", uid, f"{body.role} {body.email}")
    svc.notify(uid, "account_created",
               f"Your CityShield {body.role} account was created.", email=True)
    return {"id": uid}


@admin_router.patch("/users/{user_id}", tags=["admin"])
def update_user(user_id: int, body: UpdateUserIn,
                user: dict = Depends(require_role("admin"))) -> dict:
    """Assign/move a user to a team, change their role, and/or activate /
    deactivate the account. Only the fields sent in the body are touched;
    team_id=null removes them from any team."""
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(400, "Nothing to update")
    if "role" in fields and fields["role"] not in ("officer", "lead", "admin"):
        raise HTTPException(400, "role must be officer|lead|admin")
    with get_conn() as conn:
        target = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if target is None:
            raise HTTPException(404, "User not found")
        if "team_id" in fields and fields["team_id"] is not None:
            if conn.execute("SELECT 1 FROM teams WHERE id = ?",
                            (fields["team_id"],)).fetchone() is None:
                raise HTTPException(404, "Team not found")
        sets, params = [], []
        if "team_id" in fields:
            sets.append("team_id = ?"); params.append(fields["team_id"])
        if "role" in fields:
            sets.append("role = ?"); params.append(fields["role"])
        if "active" in fields:
            sets.append("active = ?"); params.append(1 if fields["active"] else 0)
        # A role change alters permissions and a deactivation must immediately
        # cut off access: in either case revoke the user's existing sessions so
        # outstanding tokens stop working (bump token_version exactly once).
        if "role" in fields or "active" in fields:
            sets.append("token_version = token_version + 1")
        params.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params)
    svc.audit(user["id"], "update_user", "user", user_id, str(fields))
    if "team_id" in fields and fields["team_id"]:
        svc.notify(user_id, "team_assigned", "You have been added to a team.")
    return {"ok": True}


@admin_router.get("/teams", tags=["admin"])
def list_teams(user: dict = Depends(get_current_user)) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT t.*, (SELECT COUNT(*) FROM users u WHERE u.team_id = t.id) AS members "
            "FROM teams t ORDER BY t.name"
        ).fetchall()
    return [dict(r) for r in rows]


@admin_router.get("/teams/{team_id}/members", tags=["admin"])
def list_team_members(team_id: int, user: dict = Depends(get_current_user)) -> list[dict]:
    """Members of a team, with a flag marking the team lead. Visible to any
    authenticated staff member (the Admin UI gates the view to admins itself)."""
    with get_conn() as conn:
        team = conn.execute("SELECT lead_user_id FROM teams WHERE id = ?", (team_id,)).fetchone()
        if team is None:
            raise HTTPException(404, "Team not found")
        rows = conn.execute(
            "SELECT id, name, email, role, badge_no FROM users "
            "WHERE team_id = ? ORDER BY role DESC, name", (team_id,)
        ).fetchall()
    lead_id = team["lead_user_id"]
    return [{**dict(r), "is_lead": r["id"] == lead_id} for r in rows]


@admin_router.post("/teams", tags=["admin"])
def create_team(body: TeamIn, user: dict = Depends(require_role("admin"))) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO teams (name, station, lead_user_id) VALUES (?, ?, ?)",
            (body.name, body.station, body.lead_user_id),
        )
        tid = cur.lastrowid
        if body.lead_user_id:
            conn.execute("UPDATE users SET team_id = ?, role = 'lead' WHERE id = ?",
                         (tid, body.lead_user_id))
    svc.audit(user["id"], "create_team", "team", tid, body.name)
    return {"id": tid}


# ============================================================= COMPLAINTS
@complaints_router.post("", tags=["complaints"])
def create_complaint(body: ComplaintIn, user: dict = Depends(get_current_user)) -> dict:
    centroid = area_centroid(body.area)
    lat, lng = centroid if centroid else (None, None)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO complaints (citizen_id, title, description, category, "
            "location, area, lat, lng) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], body.title, body.description, body.category,
             body.location, body.area, lat, lng),
        )
        cid = cur.lastrowid
    svc.audit(user["id"], "file_complaint", "complaint", cid, body.title)
    svc.notify_admins("new_complaint", f"New complaint filed: {body.title}",
                      complaint_id=cid)
    return {"id": cid, "status": "submitted"}


@complaints_router.get("", tags=["complaints"])
def list_complaints(user: dict = Depends(get_current_user)) -> list[dict]:
    with get_conn() as conn:
        if user["role"] == "citizen":
            rows = conn.execute(
                "SELECT * FROM complaints WHERE citizen_id = ? ORDER BY created_at DESC",
                (user["id"],)).fetchall()
        elif user["role"] == "admin":
            rows = conn.execute("SELECT * FROM complaints ORDER BY created_at DESC").fetchall()
        else:  # officer/lead — their team's assigned complaints + unassigned
            rows = conn.execute(
                "SELECT * FROM complaints WHERE assigned_team_id = ? OR assigned_team_id "
                "IS NULL ORDER BY created_at DESC", (user.get("team_id"),)).fetchall()
    return [dict(r) for r in rows]


@complaints_router.post("/{complaint_id}/triage", tags=["complaints"])
def triage_complaint(complaint_id: int, body: TriageIn,
                     user: dict = Depends(require_role("lead"))) -> dict:
    with get_conn() as conn:
        c = conn.execute("SELECT * FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if c is None:
            raise HTTPException(404, "Complaint not found")
        conn.execute(
            "UPDATE complaints SET severity=?, priority=?, response_message=?, "
            "assigned_team_id=?, status='assigned', updated_at=datetime('now') WHERE id=?",
            (body.severity, body.priority, body.response_message,
             body.assigned_team_id, complaint_id),
        )
        case_id = None
        if body.create_case:
            cur = conn.execute(
                "INSERT INTO cases (title, description, complaint_id, created_by, "
                "assigned_team_id, severity, priority, citizen_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (c["title"], c["description"], complaint_id, user["id"],
                 body.assigned_team_id, body.severity, body.priority, c["citizen_id"]),
            )
            case_id = cur.lastrowid
            conn.execute("UPDATE complaints SET status='converted', case_id=? WHERE id=?",
                         (case_id, complaint_id))

    svc.audit(user["id"], "triage_complaint", "complaint", complaint_id,
              f"severity={body.severity} priority={body.priority}")
    # notify the citizen with the response message (email)
    if body.response_message:
        svc.notify(c["citizen_id"], "complaint_update",
                   f"Update on your complaint '{c['title']}': {body.response_message}",
                   complaint_id=complaint_id, email=True)
    if body.assigned_team_id:
        svc.notify_team(body.assigned_team_id, "complaint_assigned",
                        f"Complaint assigned to your team: {c['title']}",
                        complaint_id=complaint_id, case_id=case_id)
    return {"ok": True, "case_id": case_id}


# ============================================================= CASES
@cases_router.post("", tags=["cases"])
def create_case(body: CaseIn, user: dict = Depends(require_role("lead"))) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO cases (title, description, complaint_id, created_by, "
            "assigned_team_id, severity, priority, citizen_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (body.title, body.description, body.complaint_id, user["id"],
             body.assigned_team_id or user.get("team_id"), body.severity,
             body.priority, body.citizen_id),
        )
        cid = cur.lastrowid
        # creator is auto-assigned
        conn.execute("INSERT OR IGNORE INTO case_assignments (case_id, user_id, "
                     "role_on_case) VALUES (?, ?, 'lead')", (cid, user["id"]))
    svc.audit(user["id"], "create_case", "case", cid, body.title)
    svc.notify_admins("new_case", f"New case opened: {body.title}", case_id=cid)
    return {"id": cid}


@cases_router.get("", tags=["cases"])
def list_cases(user: dict = Depends(get_current_user),
               status_filter: str | None = None) -> list[dict]:
    with get_conn() as conn:
        base = ("SELECT c.*, (SELECT COUNT(*) FROM evidence e WHERE e.case_id=c.id) "
                "AS evidence_count FROM cases c")
        if user["role"] == "admin":
            sql, params = base + " ORDER BY c.created_at DESC", []
        elif role_rank(user["role"]) >= role_rank("officer"):
            sql = (base + " WHERE c.assigned_team_id = ? OR c.id IN "
                   "(SELECT case_id FROM case_assignments WHERE user_id = ?) "
                   "ORDER BY c.created_at DESC")
            params = [user.get("team_id"), user["id"]]
        else:  # citizen — only their citizen-visible cases
            sql = (base + " WHERE c.citizen_id = ? AND c.citizen_visible = 1 "
                   "ORDER BY c.created_at DESC")
            params = [user["id"]]
        rows = conn.execute(sql, params).fetchall()
    out = [dict(r) for r in rows]
    if status_filter:
        out = [c for c in out if c["status"] == status_filter]
    return out


@cases_router.get("/{case_id}", tags=["cases"])
def get_case(case_id: int, user: dict = Depends(get_current_user)) -> dict:
    case = svc.get_case_or_403(user, case_id)
    with get_conn() as conn:
        members = [dict(r) for r in conn.execute(
            "SELECT u.id, u.name, u.role, ca.role_on_case FROM case_assignments ca "
            "JOIN users u ON u.id = ca.user_id WHERE ca.case_id = ?", (case_id,))]
    case["members"] = members
    return case


@cases_router.post("/{case_id}/assign", tags=["cases"])
def assign_case(case_id: int, body: AssignIn,
                user: dict = Depends(require_role("lead"))) -> dict:
    svc.get_case_or_403(user, case_id)
    with get_conn() as conn:
        for uid in body.user_ids:
            conn.execute("INSERT OR REPLACE INTO case_assignments (case_id, user_id, "
                         "role_on_case) VALUES (?, ?, ?)", (case_id, uid, body.role_on_case))
    for uid in body.user_ids:
        svc.notify(uid, "case_assigned", "You have been assigned to a case.",
                   case_id=case_id, email=True)
    svc.audit(user["id"], "assign_case", "case", case_id, str(body.user_ids))
    return {"ok": True}


@cases_router.post("/{case_id}/evidence", tags=["cases"])
def add_evidence(case_id: int, body: EvidenceIn,
                 user: dict = Depends(require_role("officer"))) -> dict:
    svc.get_case_or_403(user, case_id)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO evidence (case_id, kind, ref, caption, visibility, added_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (case_id, body.kind, body.ref, body.caption, body.visibility, user["id"]),
        )
        eid = cur.lastrowid
    svc.audit(user["id"], "add_evidence", "case", case_id, f"{body.kind} #{eid}")
    svc.notify_case_members(case_id, "new_evidence",
                            f"New evidence added to case #{case_id}.", exclude=user["id"])
    return {"id": eid}


@cases_router.get("/{case_id}/evidence", tags=["cases"])
def list_evidence(case_id: int, user: dict = Depends(get_current_user)) -> list[dict]:
    case = svc.get_case_or_403(user, case_id)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT e.*, u.name AS added_by_name FROM evidence e "
            "JOIN users u ON u.id = e.added_by WHERE e.case_id = ? ORDER BY e.created_at",
            (case_id,)).fetchall()
    return [dict(r) for r in rows
            if svc.evidence_visible_to(user, case, r["visibility"])]


@cases_router.post("/{case_id}/documents", tags=["cases"])
def add_document(case_id: int, body: DocumentIn,
                 user: dict = Depends(require_role("officer"))) -> dict:
    svc.get_case_or_403(user, case_id)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO case_documents (case_id, doc_type, title, content, created_by) "
            "VALUES (?, ?, ?, ?, ?)",
            (case_id, body.doc_type, body.title, body.content, user["id"]),
        )
        did = cur.lastrowid
    svc.audit(user["id"], "add_document", "case", case_id, f"{body.doc_type}: {body.title}")
    return {"id": did}


@cases_router.get("/{case_id}/documents", tags=["cases"])
def list_documents(case_id: int, user: dict = Depends(get_current_user)) -> list[dict]:
    case = svc.get_case_or_403(user, case_id)
    # citizens don't see internal documents unless explicitly shared as evidence
    if role_rank(user["role"]) < role_rank("officer"):
        return []
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT d.*, u.name AS created_by_name FROM case_documents d "
            "JOIN users u ON u.id = d.created_by WHERE d.case_id = ? ORDER BY d.created_at",
            (case_id,)).fetchall()
    return [dict(r) for r in rows]


@cases_router.get("/{case_id}/messages", tags=["cases"])
def list_messages(case_id: int, user: dict = Depends(get_current_user)) -> list[dict]:
    svc.get_case_or_403(user, case_id)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT m.*, u.name AS sender_name FROM case_messages m "
            "JOIN users u ON u.id = m.sender_id WHERE m.case_id = ? ORDER BY m.created_at",
            (case_id,)).fetchall()
    return [dict(r) for r in rows]


@cases_router.post("/{case_id}/messages", tags=["cases"])
def post_message(case_id: int, body: MessageIn,
                 user: dict = Depends(get_current_user)) -> dict:
    case = svc.get_case_or_403(user, case_id)
    # citizens are capped at a single message per case
    if user["role"] == "citizen":
        with get_conn() as conn:
            n = conn.execute("SELECT COUNT(*) c FROM case_messages WHERE case_id = ? "
                             "AND sender_id = ?", (case_id, user["id"])).fetchone()["c"]
        if n >= 1:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "Citizens may send only one message per case")
    with get_conn() as conn:
        conn.execute("INSERT INTO case_messages (case_id, sender_id, sender_role, body) "
                     "VALUES (?, ?, ?, ?)", (case_id, user["id"], user["role"], body.body))
    if user["role"] == "citizen":
        svc.notify_case_members(case_id, "citizen_message",
                                f"Citizen sent a message on case #{case_id}.")
    elif case.get("citizen_id"):
        svc.notify(case["citizen_id"], "case_message",
                   f"New message from the investigating team on your case.",
                   case_id=case_id, email=True)
    return {"ok": True}


@cases_router.post("/{case_id}/citizen-visibility", tags=["cases"])
def set_visibility(case_id: int, body: VisibilityIn,
                   user: dict = Depends(require_role("officer"))) -> dict:
    case = svc.get_case_or_403(user, case_id)
    with get_conn() as conn:
        conn.execute("UPDATE cases SET citizen_visible = ?, updated_at=datetime('now') "
                     "WHERE id = ?", (1 if body.citizen_visible else 0, case_id))
    svc.audit(user["id"], "citizen_visibility", "case", case_id, str(body.citizen_visible))
    if body.citizen_visible and case.get("citizen_id"):
        svc.notify(case["citizen_id"], "case_shared",
                   "You can now view progress on your case.", case_id=case_id, email=True)
    return {"ok": True}


@cases_router.post("/{case_id}/close", tags=["cases"])
def close_case(case_id: int, body: CloseCaseIn,
               user: dict = Depends(require_role("lead"))) -> dict:
    case = svc.get_case_or_403(user, case_id)
    with get_conn() as conn:
        conn.execute(
            "UPDATE cases SET status='closed', verdict=?, closed_by=?, "
            "closed_at=datetime('now'), updated_at=datetime('now') WHERE id=?",
            (body.verdict, user["id"], case_id))
    svc.audit(user["id"], "close_case", "case", case_id, body.verdict[:120])
    svc.notify_case_members(case_id, "case_closed",
                            f"Case #{case_id} has been closed.", email=False)
    if case.get("citizen_id") and case.get("citizen_visible"):
        svc.notify(case["citizen_id"], "case_closed",
                   "Your case has been closed. You may now rate your experience.",
                   case_id=case_id, email=True)
    return {"ok": True}


@cases_router.post("/{case_id}/rate", tags=["cases"])
def rate_case(case_id: int, body: RatingIn,
              user: dict = Depends(get_current_user)) -> dict:
    case = svc.get_case_or_403(user, case_id)
    if case.get("citizen_id") != user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the complainant can rate")
    if case["status"] != "closed":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Case is not closed yet")
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO ratings (case_id, citizen_id, stars, comment) "
                     "VALUES (?, ?, ?, ?)", (case_id, user["id"], body.stars, body.comment))
    svc.audit(user["id"], "rate_case", "case", case_id, f"{body.stars} stars")
    return {"ok": True}


@cases_router.get("/{case_id}/meetings", tags=["cases"])
def list_meetings(case_id: int, user: dict = Depends(get_current_user)) -> list[dict]:
    svc.get_case_or_403(user, case_id)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT m.*, u.name AS created_by_name FROM case_meetings m "
            "JOIN users u ON u.id = m.created_by WHERE m.case_id = ? "
            "ORDER BY m.scheduled_at", (case_id,)).fetchall()
    return [dict(r) for r in rows]


@cases_router.post("/{case_id}/meetings", tags=["cases"])
def create_meeting(case_id: int, body: MeetingIn,
                   user: dict = Depends(require_role("officer"))) -> dict:
    svc.get_case_or_403(user, case_id)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO case_meetings (case_id, title, scheduled_at, duration_min, "
            "location, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (case_id, body.title, body.scheduled_at, body.duration_min,
             body.location, body.notes, user["id"]),
        )
        mid = cur.lastrowid
    svc.audit(user["id"], "schedule_meeting", "case", case_id,
              f"{body.title} @ {body.scheduled_at}")
    svc.notify_case_members(
        case_id, "meeting_scheduled",
        f"Meeting scheduled for case #{case_id}: '{body.title}' on "
        f"{body.scheduled_at} at {body.location}.", exclude=user["id"])
    return {"id": mid}


@cases_router.delete("/{case_id}/meetings/{meeting_id}", tags=["cases"])
def cancel_meeting(case_id: int, meeting_id: int,
                   user: dict = Depends(require_role("officer"))) -> dict:
    svc.get_case_or_403(user, case_id)
    with get_conn() as conn:
        m = conn.execute("SELECT * FROM case_meetings WHERE id = ? AND case_id = ?",
                         (meeting_id, case_id)).fetchone()
        if m is None:
            raise HTTPException(404, "Meeting not found")
        # only the organiser or a lead+ may cancel
        if m["created_by"] != user["id"] and role_rank(user["role"]) < role_rank("lead"):
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "Only the organiser or a team lead can cancel")
        conn.execute("DELETE FROM case_meetings WHERE id = ?", (meeting_id,))
    svc.audit(user["id"], "cancel_meeting", "case", case_id, m["title"])
    svc.notify_case_members(case_id, "meeting_cancelled",
                            f"Meeting '{m['title']}' for case #{case_id} was cancelled.",
                            exclude=user["id"])
    return {"ok": True}


@cases_router.get("/{case_id}/timeline", tags=["cases"])
def case_timeline(case_id: int, user: dict = Depends(get_current_user)) -> list[dict]:
    svc.get_case_or_403(user, case_id)
    if role_rank(user["role"]) < role_rank("officer"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff only")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT a.*, u.name AS actor_name FROM audit_log a "
            "LEFT JOIN users u ON u.id = a.actor_id "
            "WHERE a.entity = 'case' AND a.entity_id = ? ORDER BY a.created_at DESC",
            (case_id,)).fetchall()
    return [dict(r) for r in rows]


# ============================================================= NOTIFICATIONS
@notif_router.get("", tags=["notifications"])
def my_notifications(user: dict = Depends(get_current_user)) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
            (user["id"],)).fetchall()
        unread = conn.execute("SELECT COUNT(*) c FROM notifications WHERE user_id = ? "
                              "AND read = 0", (user["id"],)).fetchone()["c"]
    return {"unread": unread, "items": [dict(r) for r in rows]}


@notif_router.post("/read-all", tags=["notifications"])
def mark_all_read(user: dict = Depends(get_current_user)) -> dict:
    with get_conn() as conn:
        conn.execute("UPDATE notifications SET read = 1 WHERE user_id = ?", (user["id"],))
    return {"ok": True}


# ============================================================= BROADCASTS
# City-wide alerts (disasters, advisories). The broadcast row powers the
# always-visible banner; a notification per active user delivers the ping.
_BROADCAST_KINDS = {"disaster", "advisory"}
_SEVERITIES = ("low", "medium", "high", "critical")


@notif_router.post("/broadcast", tags=["notifications"])
def send_broadcast(body: BroadcastIn,
                   user: dict = Depends(require_role("admin"))) -> dict:
    if body.kind not in _BROADCAST_KINDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kind must be disaster|advisory")
    if body.severity not in _SEVERITIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid severity")
    if body.expires_at:
        try:
            datetime.fromisoformat(body.expires_at)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                "expires_at must be ISO datetime")

    prefix = f"[{body.severity.upper()}]"
    where = f" ({body.area})" if body.area else ""
    message = f"{prefix} {body.title}{where}: {body.message}"

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO broadcasts (kind, title, message, area, severity, "
            "link, expires_at, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (body.kind, body.title, body.message, body.area, body.severity,
             body.link, body.expires_at or None, user["id"]),
        )
        bid = cur.lastrowid
        # fan out one notification per active user, in a single transaction
        uids = [r["id"] for r in conn.execute(
            "SELECT id FROM users WHERE active = 1")]
        conn.executemany(
            "INSERT INTO notifications (user_id, type, message, link) "
            "VALUES (?, ?, ?, ?)",
            [(uid, body.kind, message, body.link) for uid in uids],
        )
    svc.audit(user["id"], "broadcast", "broadcast", bid,
              f"{body.kind}/{body.severity}: {body.title} -> {len(uids)} users")
    return {"id": bid, "recipients": len(uids)}


@notif_router.get("/broadcasts/active", tags=["notifications"])
def active_broadcasts(user: dict = Depends(get_current_user)) -> list[dict]:
    """Active, unexpired broadcasts for the alert banner — all roles."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT b.*, u.name AS sender FROM broadcasts b "
            "JOIN users u ON u.id = b.created_by "
            "WHERE b.active = 1 AND (b.expires_at IS NULL "
            "OR b.expires_at > datetime('now')) "
            "ORDER BY CASE b.severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
            "WHEN 'medium' THEN 2 ELSE 3 END, b.created_at DESC",
        ).fetchall()
    return [dict(r) for r in rows]


@notif_router.get("/broadcasts", tags=["notifications"])
def list_broadcasts(user: dict = Depends(require_role("admin"))) -> list[dict]:
    """Full broadcast history for the admin panel (newest first)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT b.*, u.name AS sender FROM broadcasts b "
            "JOIN users u ON u.id = b.created_by "
            "ORDER BY b.created_at DESC LIMIT 100").fetchall()
    return [dict(r) for r in rows]


@notif_router.post("/broadcasts/{bid}/deactivate", tags=["notifications"])
def deactivate_broadcast(bid: int,
                         user: dict = Depends(require_role("admin"))) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM broadcasts WHERE id = ?", (bid,)).fetchone()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Broadcast not found")
        conn.execute("UPDATE broadcasts SET active = 0 WHERE id = ?", (bid,))
    svc.audit(user["id"], "broadcast_deactivate", "broadcast", bid)
    return {"id": bid, "active": False}
