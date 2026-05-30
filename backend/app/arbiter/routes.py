"""Arbiter REST API — mounted under /api/legal/*.

Modular router that plugs into the existing CityShield FastAPI app without
touching the VisionScan routes.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from . import llm, service, store

router = APIRouter()


class SectionRequest(BaseModel):
    description: str = Field(..., description="Description of the crime / incident")
    top_k: int = Field(6, ge=1, le=20)


class FIRRequest(BaseModel):
    incident: str = Field(..., description="Incident description / facts")
    complainant: str = ""
    accused: str = ""
    location: str = ""
    occurred_at: str = ""
    language: str = Field("en", description="en | hi | gu")


class QueryRequest(BaseModel):
    question: str = Field(..., description="Citizen's legal question")
    language: str = Field("en", description="en | hi | gu")


@router.get("/health", tags=["legal"])
def legal_health() -> dict:
    return {
        "module": "Arbiter",
        "corpus_sections": store.corpus_size(),
        "llm_online": llm.is_online(),
        "mode": "Gemini" if llm.is_online() else "offline (RAG + templates)",
        "languages": list(llm.LANGUAGES.keys()),
    }


@router.post("/sections", tags=["legal"])
def section_lookup(body: SectionRequest) -> dict:
    return service.suggest_sections(body.description, k=body.top_k)


@router.post("/fir", tags=["legal"])
def fir_draft(body: FIRRequest) -> dict:
    return service.draft_fir(
        incident=body.incident,
        complainant=body.complainant,
        accused=body.accused,
        location=body.location,
        occurred_at=body.occurred_at,
        language=body.language,
    )


@router.post("/query", tags=["legal"])
def citizen_query(body: QueryRequest) -> dict:
    return service.answer_query(body.question, language=body.language)
