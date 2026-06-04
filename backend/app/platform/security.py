"""Auth primitives: password hashing (bcrypt), JWT, and FastAPI dependencies
for current-user resolution and role / case-access enforcement.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import get_settings
from ..database import get_conn

_bearer = HTTPBearer(auto_error=False)

# Role hierarchy for >= comparisons
_ROLE_RANK = {"citizen": 0, "officer": 1, "lead": 2, "admin": 3}


# ---------------- passwords ----------------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ---------------- tokens ----------------
def create_token(user_id: int, role: str, token_version: int = 0) -> str:
    s = get_settings()
    payload = {
        "sub": str(user_id),
        "role": role,
        # Embed the user's token_version so revocation (logout-all, password
        # reset, role change, deactivation) invalidates tokens minted earlier.
        "tv": token_version,
        "exp": datetime.now(timezone.utc) + timedelta(hours=s.jwt_expire_hours),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


# ---------------- dependencies ----------------
def _user_from_creds(creds: HTTPAuthorizationCredentials | None) -> dict:
    """Resolve a live, active user from bearer credentials, or raise 401."""
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = _decode(creds.credentials)
    uid = int(payload.get("sub", 0))
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, email, role, team_id, active, token_version "
            "FROM users WHERE id = ?",
            (uid,),
        ).fetchone()
    if row is None or not row["active"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    # Revocation check: tokens minted before a token_version bump are rejected.
    # Tokens issued before the column existed carry no "tv" -> default 0, which
    # equals the column default, so legacy tokens keep working.
    if payload.get("tv", 0) != row["token_version"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token revoked")
    return dict(row)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    return _user_from_creds(creds)


def auth_gate(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """Flag-gated auth for the VisionScan / Arbiter routes.

    Open by default (public demo). When VISIONSCAN_REQUIRE_AUTH=true, a valid
    login token is required just like get_current_user.
    """
    if not get_settings().require_auth:
        return None
    return _user_from_creds(creds)


def require_role(*roles: str):
    """Dependency factory: allow only the given roles (or higher rank)."""
    min_rank = min(_ROLE_RANK[r] for r in roles)

    def checker(user: dict = Depends(get_current_user)) -> dict:
        if _ROLE_RANK.get(user["role"], -1) < min_rank:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return checker


def is_staff(user: dict) -> bool:
    return _ROLE_RANK.get(user["role"], 0) >= _ROLE_RANK["officer"]


def role_rank(role: str) -> int:
    return _ROLE_RANK.get(role, 0)
