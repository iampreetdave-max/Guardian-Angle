"""Pydantic request models for the CrimeGPT API."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from .service import PARTY_ROLES


class PartyIn(BaseModel):
    role: str = Field(..., description="accused|victim|witness")
    name: str = Field(..., min_length=1, max_length=200)
    age: int | None = Field(None, ge=0, le=150)
    gender: str | None = Field(None, max_length=30)
    address: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=40)
    id_proof: str | None = Field(None, max_length=120)
    description: str | None = Field(None, max_length=2000)

    @field_validator("role")
    @classmethod
    def _role_ok(cls, v: str) -> str:
        if v not in PARTY_ROLES:
            raise ValueError(f"role must be one of {PARTY_ROLES}")
        return v


class PartyUpdateIn(BaseModel):
    role: str | None = None
    name: str | None = Field(None, max_length=200)
    age: int | None = Field(None, ge=0, le=150)
    gender: str | None = Field(None, max_length=30)
    address: str | None = Field(None, max_length=500)
    phone: str | None = Field(None, max_length=40)
    id_proof: str | None = Field(None, max_length=120)
    description: str | None = Field(None, max_length=2000)

    @field_validator("role")
    @classmethod
    def _role_ok(cls, v):
        if v is not None and v not in PARTY_ROLES:
            raise ValueError(f"role must be one of {PARTY_ROLES}")
        return v


class SeizureIn(BaseModel):
    item: str = Field(..., min_length=1, max_length=300)
    quantity: str | None = Field(None, max_length=80)
    description: str | None = Field(None, max_length=2000)
    seized_from: str | None = Field(None, max_length=300)
    seized_at: str | None = Field(None, max_length=80)
    witness_names: str | None = Field(None, max_length=400)


class StatementIn(BaseModel):
    party_id: int | None = None
    statement_text: str = Field(..., min_length=1, max_length=8000)


class DiaryIn(BaseModel):
    entry_type: str = Field("note", max_length=40)
    narrative: str = Field(..., min_length=1, max_length=8000)


class SuggestIn(BaseModel):
    narrative: str = Field("", max_length=12000)
    top_k: int = Field(6, ge=1, le=25)
