"""CrimeGPT REST API — mounted under /api/crimegpt/*.

AI-powered crime documentation automation. Officers enter case facts ONCE into
the unified data pool; CrimeGPT generates every statutory document, suggests
BNS/BNSS/BSA sections, and maintains a chronological case diary.

All case-scoped endpoints are officer-gated AND access-checked against the
specific case via the platform's get_case_or_403 (so an officer can only touch
cases on their team / assigned to them, exactly like the rest of CityShield).
The stateless section-suggestion endpoint is officer-gated but not case-scoped.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..arbiter import llm
from ..platform.security import require_role
from ..platform.service import get_case_or_403
from . import legal_sections, service as svc, templates
from .models import (
    DiaryIn, PartyIn, PartyUpdateIn, SeizureIn, StatementIn, SuggestIn,
)

router = APIRouter()


# ----------------------------------------------------------------- health/meta
@router.get("/health", tags=["crimegpt"])
def crimegpt_health() -> dict:
    return {
        "module": "CrimeGPT",
        "doc_types": svc.DOC_TYPES,
        "party_roles": list(svc.PARTY_ROLES),
        "offence_patterns": len(legal_sections.OFFENCE_MAP),
        "llm_online": llm.is_online(),
        "translation_mode": "Gemini" if llm.is_online()
        else "offline (English labels retained)",
        "languages": list(llm.LANGUAGES.keys()),
    }


@router.get("/legal/catalogue", tags=["crimegpt"])
def legal_catalogue(_user: dict = Depends(require_role("officer"))) -> dict:
    """The full curated BNS/BNSS offence catalogue (reference panel)."""
    return {"patterns": legal_sections.all_offence_patterns()}


# ----------------------------------------------------------------- suggest sections
@router.post("/suggest-sections", tags=["crimegpt"])
def suggest_sections(body: SuggestIn,
                     _user: dict = Depends(require_role("officer"))) -> dict:
    """Rank applicable BNS/BNSS sections for a free-text case narrative.

    Pure-offline keyword/synonym scoring; stateless (no case needed) so it can
    be called from the case-creation flow READ-ONLY before a case exists.
    """
    ranked = legal_sections.suggest_sections(body.narrative, top_k=body.top_k)
    return {
        "narrative_chars": len(body.narrative or ""),
        "count": len(ranked),
        "suggestions": ranked,
    }


# ----------------------------------------------------------------- pool
@router.get("/cases/{case_id}/pool", tags=["crimegpt"])
def get_pool(case_id: int, user: dict = Depends(require_role("officer"))) -> dict:
    get_case_or_403(user, case_id)
    pool = svc.get_pool(case_id)
    pool["case"] = svc.get_case_header(case_id)
    return pool


# ---- parties
@router.post("/cases/{case_id}/parties", tags=["crimegpt"])
def add_party(case_id: int, body: PartyIn,
              user: dict = Depends(require_role("officer"))) -> dict:
    get_case_or_403(user, case_id)
    pid = svc.add_party(case_id, user["id"], body.model_dump())
    return {"id": pid}


@router.patch("/cases/{case_id}/parties/{party_id}", tags=["crimegpt"])
def update_party(case_id: int, party_id: int, body: PartyUpdateIn,
                 user: dict = Depends(require_role("officer"))) -> dict:
    get_case_or_403(user, case_id)
    if not svc.update_party(case_id, party_id, user["id"],
                            body.model_dump(exclude_unset=True)):
        raise HTTPException(404, "Party not found or nothing to update")
    return {"ok": True}


@router.delete("/cases/{case_id}/parties/{party_id}", tags=["crimegpt"])
def delete_party(case_id: int, party_id: int,
                 user: dict = Depends(require_role("officer"))) -> dict:
    get_case_or_403(user, case_id)
    if not svc.delete_party(case_id, party_id, user["id"]):
        raise HTTPException(404, "Party not found")
    return {"ok": True}


# ---- seizures
@router.post("/cases/{case_id}/seizures", tags=["crimegpt"])
def add_seizure(case_id: int, body: SeizureIn,
                user: dict = Depends(require_role("officer"))) -> dict:
    get_case_or_403(user, case_id)
    sid = svc.add_seizure(case_id, user["id"], body.model_dump())
    return {"id": sid}


@router.delete("/cases/{case_id}/seizures/{seizure_id}", tags=["crimegpt"])
def delete_seizure(case_id: int, seizure_id: int,
                   user: dict = Depends(require_role("officer"))) -> dict:
    get_case_or_403(user, case_id)
    if not svc.delete_seizure(case_id, seizure_id, user["id"]):
        raise HTTPException(404, "Seizure not found")
    return {"ok": True}


# ---- statements
@router.post("/cases/{case_id}/statements", tags=["crimegpt"])
def add_statement(case_id: int, body: StatementIn,
                  user: dict = Depends(require_role("officer"))) -> dict:
    get_case_or_403(user, case_id)
    sid = svc.add_statement(case_id, user["id"], body.model_dump())
    return {"id": sid}


@router.delete("/cases/{case_id}/statements/{statement_id}", tags=["crimegpt"])
def delete_statement(case_id: int, statement_id: int,
                     user: dict = Depends(require_role("officer"))) -> dict:
    get_case_or_403(user, case_id)
    if not svc.delete_statement(case_id, statement_id, user["id"]):
        raise HTTPException(404, "Statement not found")
    return {"ok": True}


# ----------------------------------------------------------------- diary
@router.get("/cases/{case_id}/diary", tags=["crimegpt"])
def list_diary(case_id: int, user: dict = Depends(require_role("officer"))) -> dict:
    get_case_or_403(user, case_id)
    return {"items": svc.list_diary(case_id)}


@router.post("/cases/{case_id}/diary", tags=["crimegpt"])
def add_diary(case_id: int, body: DiaryIn,
              user: dict = Depends(require_role("officer"))) -> dict:
    get_case_or_403(user, case_id)
    did = svc.add_diary(case_id, user["id"], body.entry_type or "note", body.narrative)
    from ..platform import service as platform_svc
    platform_svc.audit(user["id"], "crimegpt_diary_entry", "case", case_id,
                       body.entry_type or "note")
    return {"id": did}


# ----------------------------------------------------------------- documents
@router.get("/cases/{case_id}/documents", tags=["crimegpt"])
def list_documents(case_id: int,
                   user: dict = Depends(require_role("officer"))) -> dict:
    get_case_or_403(user, case_id)
    return {"items": svc.list_documents(case_id)}


@router.post("/cases/{case_id}/documents/{doc_type}", tags=["crimegpt"])
def generate_document(
    case_id: int, doc_type: str,
    language: str = Query("en", description="en|hi|gu"),
    user: dict = Depends(require_role("officer")),
) -> Response:
    """Generate (or regenerate) a statutory document as a branded PDF.

    Records a versioned crimegpt_documents row (regenerating bumps the version),
    writes an auto case-diary entry, and streams the PDF back. Translation for
    hi/gu is best-effort via the Arbiter LLM bridge — the PDF is never blocked
    when translation is unavailable.
    """
    get_case_or_403(user, case_id)
    if doc_type not in svc.DOC_TYPES:
        raise HTTPException(404, f"Unknown document type '{doc_type}'")
    if language not in ("en", "hi", "gu"):
        language = "en"

    case = svc.get_case_header(case_id)
    pool = svc.get_pool(case_id)
    # Suggest sections from the case narrative so the document carries them.
    narrative = (case.get("description") or case.get("title") or "")
    sections = legal_sections.suggest_sections(narrative, top_k=6)

    version = svc.next_version(case_id, doc_type)
    try:
        pdf = templates.generate_pdf(doc_type, case, pool, sections, version, language)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(500, f"Document generation failed: {exc}")

    svc.record_document(case_id, doc_type, language, version, pdf, user["id"])
    title = svc.DOC_TYPES[doc_type]
    svc.add_diary(case_id, user["id"], "document",
                  f"{title} v{version} generated by {user['name']} "
                  f"({language.upper()}).")

    filename = f"{doc_type}_case{case_id}_v{version}_{language}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Document-Version": str(version),
            "X-Document-Type": doc_type,
        },
    )
