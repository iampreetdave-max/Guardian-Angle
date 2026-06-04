"""Pydantic request models for the platform API."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ---- auth ----
class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(..., min_length=6)
    phone: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


# ---- admin: users & teams ----
class CreateUserIn(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field("officer", description="officer|lead|admin")
    team_id: Optional[int] = None
    badge_no: Optional[str] = None
    phone: Optional[str] = None


class UpdateUserIn(BaseModel):
    """Partial update of a staff user. Only fields present in the request body
    are changed (team_id may be set to null to remove from a team).

    ``active=False`` deactivates the account (and revokes its sessions); the
    user can no longer authenticate until reactivated."""
    team_id: Optional[int] = None
    role: Optional[str] = None
    active: Optional[bool] = None


class TeamIn(BaseModel):
    name: str
    station: str = "Ahmedabad Cyber Crime Branch"
    lead_user_id: Optional[int] = None


# ---- complaints ----
class ComplaintIn(BaseModel):
    title: str
    description: str
    category: Optional[str] = None
    location: Optional[str] = None
    area: Optional[str] = None      # Ahmedabad locality (constants/ahmedabad.py)


# ---- broadcasts (city-wide disaster / advisory alerts) ----
class BroadcastIn(BaseModel):
    kind: str = Field("advisory", description="disaster|advisory")
    title: str = Field(..., min_length=3, max_length=120)
    message: str = Field(..., min_length=3, max_length=2000)
    area: Optional[str] = None      # optional Ahmedabad locality
    severity: str = Field("medium", description="low|medium|high|critical")
    link: Optional[str] = None
    expires_at: Optional[str] = Field(
        None, description="ISO datetime; empty = active until deactivated")


class TriageIn(BaseModel):
    severity: str = Field("medium", description="low|medium|high|critical")
    priority: int = Field(3, ge=1, le=5)
    response_message: str = ""
    assigned_team_id: Optional[int] = None
    create_case: bool = True


# ---- cases ----
class CaseIn(BaseModel):
    title: str
    description: str = ""
    complaint_id: Optional[int] = None
    assigned_team_id: Optional[int] = None
    severity: str = "medium"
    priority: int = Field(3, ge=1, le=5)
    citizen_id: Optional[int] = None


class AssignIn(BaseModel):
    user_ids: list[int]
    role_on_case: str = "investigator"


class EvidenceIn(BaseModel):
    kind: str = Field(..., description="frame|video|file|report|note")
    ref: Optional[str] = None
    caption: str = ""
    visibility: str = Field("team", description="team|station|department|citizen")


class DocumentIn(BaseModel):
    doc_type: str = Field(..., description="FIR|brief|chargesheet|other")
    title: str
    content: str = ""


class MessageIn(BaseModel):
    body: str


class MeetingIn(BaseModel):
    title: str
    scheduled_at: str = Field(..., description="ISO datetime, e.g. 2026-06-02T15:30")
    duration_min: int = Field(60, ge=5, le=600)
    location: str = "Ahmedabad Cyber Crime Branch"
    notes: str = ""


class CloseCaseIn(BaseModel):
    verdict: str


class VisibilityIn(BaseModel):
    citizen_visible: bool


class RatingIn(BaseModel):
    stars: int = Field(..., ge=1, le=5)
    comment: str = ""
