"""Security middleware stack for the VisionScan / CityShield API.

A small set of Starlette ``BaseHTTPMiddleware`` components, stdlib-only (plus
PyJWT, already a project dependency, for the lockdown admin check). Each is
fail-soft: an optional feature must never crash startup or block a request it
cannot evaluate.

Intended mount order (in ``main.py``)::

    app.add_middleware(LockdownMiddleware)        # innermost (runs last)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(SecurityHeadersMiddleware) # outermost (runs first)

FastAPI/Starlette executes the *last* ``add_middleware`` call first on the way
in, so the effective request order is:

    SecurityHeaders -> Metrics -> RateLimit -> Lockdown -> route

and the response unwinds in reverse. SecurityHeaders being outermost guarantees
its headers are stamped on every response, including the 429 / 423 short-circuit
responses produced by the inner layers.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import Counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import get_settings

log = logging.getLogger("visionscan.security_mw")


# ---------------------------------------------------------------------------
# 1. Security headers
# ---------------------------------------------------------------------------
_CSP = (
    "default-src 'self'; "
    "img-src 'self' data: blob: https://*.tile.openstreetmap.org; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; "
    "connect-src 'self' https://*.tile.openstreetmap.org"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Stamp hardening headers on every response.

    The CSP intentionally allows the same-origin React bundle plus OSM raster
    tiles for the city map (``img-src``/``connect-src`` to
    ``*.tile.openstreetmap.org``) and inline styles (Leaflet/Tailwind emit
    them). HSTS is only sent over https so local http dev is unaffected.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        h = response.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "no-referrer"
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        h["Content-Security-Policy"] = _CSP
        if request.url.scheme == "https":
            h["Strict-Transport-Security"] = "max-age=31536000"
        return response


# ---------------------------------------------------------------------------
# 2. Rate limiting (in-memory token bucket)
# ---------------------------------------------------------------------------
# Every live RateLimitMiddleware instance registers itself here so that
# reset_rate_limits() (used by the test suite) can clear every bucket dict.
_RL_INSTANCES: list["RateLimitMiddleware"] = []


def reset_rate_limits() -> None:
    """Clear the token buckets of every live RateLimitMiddleware instance.

    Tests call this between cases so one test's traffic cannot exhaust another's
    budget. No-op if no middleware has been instantiated yet.
    """
    for inst in list(_RL_INSTANCES):
        with inst._lock:
            inst._buckets.clear()


class _Bucket:
    __slots__ = ("tokens", "updated")

    def __init__(self, tokens: float, updated: float) -> None:
        self.tokens = tokens
        self.updated = updated


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-(client IP, class) continuous-refill token bucket.

    Three classes, each with its own per-minute limit from settings:

    * ``login``  — any path containing ``/auth/login``.
    * ``upload`` — POST to ``/api/videos``, or path starting
      ``/api/search/image`` / ``/api/search/face``.
    * ``default`` — everything else.

    Capacity = the per-minute limit; refill is continuous at ``limit / 60``
    tokens per second. An exhausted bucket short-circuits with 429 and a
    ``Retry-After`` header. Disabled wholesale when ``enable_rate_limit`` is
    False. The bucket dict is guarded by a lock and pruned when it grows past
    10_000 entries (defends against IP-spoofed key blow-up).
    """

    _MAX_BUCKETS = 10_000

    def __init__(self, app) -> None:
        super().__init__(app)
        self._buckets: dict[tuple[str, str], _Bucket] = {}
        self._lock = threading.Lock()
        _RL_INSTANCES.append(self)

    def _classify(self, request: Request) -> str:
        path = request.url.path
        if "/auth/login" in path:
            return "login"
        if (request.method == "POST" and path == "/api/videos") or \
                path.startswith("/api/search/image") or \
                path.startswith("/api/search/face"):
            return "upload"
        # Bulk data-export endpoints get the tighter upload budget rather than
        # the generous default, so a leaked admin token can't rapidly exfiltrate
        # the whole case DB / CSVs by hammering them at 120 req/min.
        if path.startswith("/api/admin/export/"):
            return "export"
        return "default"

    def _limit_for(self, cls: str, settings) -> int:
        if cls == "login":
            return settings.rate_limit_login_per_min
        # Exports share the upload limit (no separate setting needed): a low,
        # conservative cap suited to heavyweight, infrequent requests.
        if cls in ("upload", "export"):
            return settings.rate_limit_upload_per_min
        return settings.rate_limit_default_per_min

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.enable_rate_limit:
            return await call_next(request)

        cls = self._classify(request)
        limit = self._limit_for(cls, settings)
        # Guard against a misconfigured non-positive limit (would lock everyone
        # out); treat it as "no limit for this class".
        if limit <= 0:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        key = (ip, cls)
        refill_per_sec = limit / 60.0
        now = time.monotonic()

        with self._lock:
            if len(self._buckets) > self._MAX_BUCKETS:
                # Cheap, total prune — buckets refill on next hit, so dropping
                # them only forgives in-flight throttling, never over-limits.
                self._buckets.clear()
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=float(limit), updated=now)
                self._buckets[key] = bucket
            else:
                elapsed = now - bucket.updated
                if elapsed > 0:
                    bucket.tokens = min(float(limit),
                                        bucket.tokens + elapsed * refill_per_sec)
                    bucket.updated = now
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                allowed = True
            else:
                allowed = False
                deficit = 1.0 - bucket.tokens
                retry_after = max(1, int(deficit / refill_per_sec) + 1)

        if not allowed:
            return JSONResponse(
                {"detail": "Too many requests"},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# 3. Metrics
# ---------------------------------------------------------------------------
_METRICS_LOCK = threading.Lock()
METRICS: dict = {
    "started_at": time.time(),
    "requests": 0,
    "errors": 0,
    "by_status": Counter(),
}


def get_metrics() -> dict:
    """Plain-dict snapshot of the live metrics, plus ``uptime_sec``."""
    with _METRICS_LOCK:
        return {
            "started_at": METRICS["started_at"],
            "requests": METRICS["requests"],
            "errors": METRICS["errors"],
            "by_status": dict(METRICS["by_status"]),
            "uptime_sec": time.time() - METRICS["started_at"],
        }


class MetricsMiddleware(BaseHTTPMiddleware):
    """Tally total requests, error count (status >= 500), and a per-status
    Counter, all under a lock. Exposed via :func:`get_metrics`."""

    async def dispatch(self, request: Request, call_next):
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            # The error path still counts toward errors/by_status before the
            # exception propagates to Starlette's default 500 handler.
            raise
        finally:
            with _METRICS_LOCK:
                METRICS["requests"] += 1
                METRICS["by_status"][status_code] += 1
                if status_code >= 500:
                    METRICS["errors"] += 1


# ---------------------------------------------------------------------------
# 4. Lockdown
# ---------------------------------------------------------------------------
_LOCKDOWN_LOCK = threading.Lock()
_LOCKDOWN_TTL_SEC = 2.0
_lockdown_cache: dict = {"value": None, "fetched_at": 0.0}


def is_lockdown() -> bool:
    """Return the current lockdown flag from ``app_settings``, with a 2s TTL
    in-process cache so the hot request path doesn't hit SQLite every call.
    Fail-soft: any DB error reads as 'not locked down'."""
    now = time.monotonic()
    with _LOCKDOWN_LOCK:
        if _lockdown_cache["value"] is not None and \
                (now - _lockdown_cache["fetched_at"]) < _LOCKDOWN_TTL_SEC:
            return _lockdown_cache["value"]
    value = False
    try:
        from .database import get_conn
        with get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'lockdown'"
            ).fetchone()
        value = bool(row and str(row["value"]) == "1")
    except Exception:  # pragma: no cover - never let a DB hiccup wedge requests
        log.warning("lockdown state read failed; treating as off", exc_info=True)
        value = False
    with _LOCKDOWN_LOCK:
        _lockdown_cache["value"] = value
        _lockdown_cache["fetched_at"] = now
    return value


def set_lockdown(enabled: bool) -> None:
    """Persist the lockdown flag ('1'/'0') and invalidate the TTL cache so the
    next :func:`is_lockdown` reflects the change immediately."""
    from .database import get_conn
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES ('lockdown', ?)",
            ("1" if enabled else "0",),
        )
    with _LOCKDOWN_LOCK:
        _lockdown_cache["value"] = None
        _lockdown_cache["fetched_at"] = 0.0


_LOCKDOWN_MESSAGE = (
    "CityShield is in emergency lockdown. "
    "Only administrators may operate the platform."
)


class LockdownMiddleware(BaseHTTPMiddleware):
    """Emergency kill-switch.

    When :func:`is_lockdown` is True, only the following are allowed through:

    * any path NOT starting with ``/api`` (the React bundle, thumbnails, etc.),
    * ``/api/health``,
    * ``/api/auth/login`` (so an admin can sign in),
    * any ``/api/admin`` or ``/api/admin/...`` path (exact prefix, not a lexical
      ``startswith`` that would also match ``/api/admins`` etc.),
    * any request bearing a valid admin JWT (``role == "admin"``).

    Everything else is rejected with 423 Locked. The Bearer token is decoded
    lazily here (PyJWT, HS256, ``settings.jwt_secret``); any decode/role error
    is treated as 'not an admin'.
    """

    def _is_admin(self, request: Request) -> bool:
        auth = request.headers.get("authorization") or ""
        if not auth.lower().startswith("bearer "):
            return False
        token = auth[7:].strip()
        if not token:
            return False
        try:
            import jwt
            payload = jwt.decode(
                token, get_settings().jwt_secret, algorithms=["HS256"]
            )
            return payload.get("role") == "admin"
        except Exception:
            # Fail-closed: any decode/role error is treated as 'not admin'.
            # Log at debug for security auditing without leaking token data or
            # spamming the request log (a missing/garbage token is routine).
            log.debug("lockdown jwt decode failed", exc_info=True)
            return False

    async def dispatch(self, request: Request, call_next):
        if not is_lockdown():
            return await call_next(request)

        path = request.url.path
        # Exact-match the admin prefix (or require a path separator) so we don't
        # lexically allow unintended sibling routes like "/api/admins" or
        # "/api/admin_debug" — only the real "/api/admin" tree is exempt.
        if (
            not path.startswith("/api")
            or path == "/api/health"
            or path == "/api/auth/login"
            or path == "/api/admin"
            or path.startswith("/api/admin/")
        ):
            return await call_next(request)

        if self._is_admin(request):
            return await call_next(request)

        return JSONResponse({"detail": _LOCKDOWN_MESSAGE}, status_code=423)
