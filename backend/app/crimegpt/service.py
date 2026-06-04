"""CrimeGPT service layer — the unified case data pool, diary, and document
versioning. All reads/writes go through the shared SQLite connection; document
generation delegates to templates.py (ReportLab).

Access control reuses the platform's case-access rules (svc.get_case_or_403)
and audit trail (svc.audit) so CrimeGPT data inherits the same RBAC + logging
as the rest of CityShield.
"""
from __future__ import annotations

import hashlib
import logging

from ..database import get_conn
from ..platform import service as platform_svc

log = logging.getLogger("visionscan.crimegpt")

# Canonical document keys -> human titles. The 7 statutory documents the
# officer can generate. Kept here so routes, templates and the frontend share
# one source of truth.
DOC_TYPES: dict[str, str] = {
    "purvani_chargesheet": "Purvani Chargesheet",
    "medical_letter": "Medical Treatment Letter",
    "remand_request": "Remand Request Letter (Police Custody)",
    "seizure_receipt": "Seizure Receipt",
    "court_custody_letter": "Court Custody Letter",
    "accused_panchanama": "Accused Panchanama",
    "face_identification": "Accused Face Identification Form",
}

PARTY_ROLES = ("accused", "victim", "witness")


# ----------------------------------------------------------------- pool: read
def get_pool(case_id: int) -> dict:
    """The full unified data pool for a case: parties, seizures, statements."""
    with get_conn() as conn:
        parties = [dict(r) for r in conn.execute(
            "SELECT * FROM case_parties WHERE case_id = ? ORDER BY "
            "CASE role WHEN 'accused' THEN 0 WHEN 'victim' THEN 1 ELSE 2 END, id",
            (case_id,))]
        seizures = [dict(r) for r in conn.execute(
            "SELECT * FROM case_seizures WHERE case_id = ? ORDER BY id", (case_id,))]
        statements = [dict(r) for r in conn.execute(
            "SELECT s.*, p.name AS party_name, u.name AS recorded_by_name "
            "FROM case_statements s "
            "LEFT JOIN case_parties p ON p.id = s.party_id "
            "LEFT JOIN users u ON u.id = s.recorded_by "
            "WHERE s.case_id = ? ORDER BY s.recorded_at", (case_id,))]
    return {"parties": parties, "seizures": seizures, "statements": statements}


def get_case_header(case_id: int) -> dict:
    """Case + complaint metadata used to fill document letterheads."""
    with get_conn() as conn:
        case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        case = dict(case) if case else {}
        team = None
        if case.get("assigned_team_id"):
            t = conn.execute("SELECT name, station FROM teams WHERE id = ?",
                             (case["assigned_team_id"],)).fetchone()
            team = dict(t) if t else None
    case["team"] = team
    return case


# ----------------------------------------------------------------- pool: parties
def add_party(case_id: int, actor_id: int, data: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO case_parties (case_id, role, name, age, gender, address, "
            "phone, id_proof, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (case_id, data["role"], data["name"], data.get("age"),
             data.get("gender"), data.get("address"), data.get("phone"),
             data.get("id_proof"), data.get("description")),
        )
        pid = cur.lastrowid
    platform_svc.audit(actor_id, "crimegpt_add_party", "case", case_id,
                       f"{data['role']}: {data['name']}")
    add_diary(case_id, actor_id, "investigation",
              f"{data['role'].capitalize()} '{data['name']}' added to the case file.")
    return pid


def update_party(case_id: int, party_id: int, actor_id: int, data: dict) -> bool:
    fields = {k: v for k, v in data.items() if k in (
        "role", "name", "age", "gender", "address", "phone", "id_proof",
        "description") and v is not None}
    if not fields:
        return False
    sets = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [party_id, case_id]
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE case_parties SET {sets} WHERE id = ? AND case_id = ?", params)
        changed = cur.rowcount > 0
    if changed:
        platform_svc.audit(actor_id, "crimegpt_update_party", "case", case_id,
                           f"party #{party_id}")
    return changed


def delete_party(case_id: int, party_id: int, actor_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM case_parties WHERE id = ? AND case_id = ?",
            (party_id, case_id))
        changed = cur.rowcount > 0
    if changed:
        platform_svc.audit(actor_id, "crimegpt_delete_party", "case", case_id,
                           f"party #{party_id}")
    return changed


# ----------------------------------------------------------------- pool: seizures
def add_seizure(case_id: int, actor_id: int, data: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO case_seizures (case_id, item, quantity, description, "
            "seized_from, seized_at, witness_names) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (case_id, data["item"], data.get("quantity"), data.get("description"),
             data.get("seized_from"), data.get("seized_at"),
             data.get("witness_names")),
        )
        sid = cur.lastrowid
    platform_svc.audit(actor_id, "crimegpt_add_seizure", "case", case_id, data["item"])
    add_diary(case_id, actor_id, "seizure",
              f"Article seized: {data['item']}"
              + (f" ({data['quantity']})" if data.get("quantity") else ""))
    return sid


def delete_seizure(case_id: int, seizure_id: int, actor_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM case_seizures WHERE id = ? AND case_id = ?",
            (seizure_id, case_id))
        changed = cur.rowcount > 0
    if changed:
        platform_svc.audit(actor_id, "crimegpt_delete_seizure", "case", case_id,
                           f"seizure #{seizure_id}")
    return changed


# ----------------------------------------------------------------- pool: statements
def add_statement(case_id: int, actor_id: int, data: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO case_statements (case_id, party_id, statement_text, "
            "recorded_by) VALUES (?, ?, ?, ?)",
            (case_id, data.get("party_id"), data["statement_text"], actor_id),
        )
        sid = cur.lastrowid
    platform_svc.audit(actor_id, "crimegpt_add_statement", "case", case_id,
                       f"statement #{sid}")
    add_diary(case_id, actor_id, "investigation", "Statement recorded.")
    return sid


def delete_statement(case_id: int, statement_id: int, actor_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM case_statements WHERE id = ? AND case_id = ?",
            (statement_id, case_id))
        changed = cur.rowcount > 0
    if changed:
        platform_svc.audit(actor_id, "crimegpt_delete_statement", "case", case_id,
                           f"statement #{statement_id}")
    return changed


# ----------------------------------------------------------------- diary
def add_diary(case_id: int, actor_id: int | None, entry_type: str,
              narrative: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO case_diary (case_id, entry_type, narrative, created_by) "
            "VALUES (?, ?, ?, ?)",
            (case_id, entry_type, narrative, actor_id),
        )
        return cur.lastrowid


def list_diary(case_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT d.*, u.name AS created_by_name FROM case_diary d "
            "LEFT JOIN users u ON u.id = d.created_by "
            "WHERE d.case_id = ? ORDER BY d.created_at, d.id", (case_id,)).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------- documents
def next_version(case_id: int, doc_type: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(version) AS v FROM crimegpt_documents "
            "WHERE case_id = ? AND doc_type = ?", (case_id, doc_type)).fetchone()
    return (row["v"] or 0) + 1


def record_document(case_id: int, doc_type: str, language: str, version: int,
                    pdf_bytes: bytes, actor_id: int) -> int:
    content_hash = hashlib.sha256(pdf_bytes).hexdigest()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO crimegpt_documents (case_id, doc_type, language, version, "
            "content_hash, generated_by) VALUES (?, ?, ?, ?, ?, ?)",
            (case_id, doc_type, language, version, content_hash, actor_id),
        )
        did = cur.lastrowid
    title = DOC_TYPES.get(doc_type, doc_type)
    platform_svc.audit(actor_id, "crimegpt_generate_document", "case", case_id,
                       f"{title} v{version} ({language})")
    return did


def list_documents(case_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT d.*, u.name AS generated_by_name FROM crimegpt_documents d "
            "LEFT JOIN users u ON u.id = d.generated_by "
            "WHERE d.case_id = ? ORDER BY d.generated_at DESC, d.id DESC",
            (case_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["doc_title"] = DOC_TYPES.get(d["doc_type"], d["doc_type"])
        out.append(d)
    return out
