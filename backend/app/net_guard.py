"""SSRF guard for caller-supplied stream URLs.

When a non-admin asks the server to fetch/ingest a stream URL, we must make
sure the URL points at a genuinely public host — not loopback, the cloud
metadata endpoint, an internal LAN service, etc. This module resolves the host
(DNS only, no fetch) and rejects any address in a non-public range.

THREAT-MODEL NOTE (DNS rebinding): this is a best-effort, resolve-time guard.
A hostile DNS server could return a public address now and a private one when
the stream is actually opened later (TOCTOU / DNS rebinding). Defeating that
requires pinning the resolved address through the actual socket connect, which
the underlying media stack does not expose. For this deployment (operator-run,
admins bypass the check entirely) the resolve-only guard is an acceptable
trade-off and stops the obvious SSRF cases.
"""
from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

from fastapi import HTTPException

logger = logging.getLogger("visionscan.net_guard")

_ALLOWED_SCHEMES = {"http", "https", "rtsp", "rtsps"}


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def assert_public_url(url: str) -> None:
    """Reject URLs that aren't safe for the server to reach out to.

    Raises HTTPException 400 when the scheme is unsupported, the host is
    missing/unresolvable, or any resolved address falls in a private,
    loopback, link-local, multicast, reserved or unspecified range.
    """
    parsed = urlparse(url or "")
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise HTTPException(400, f"Unsupported URL scheme: {parsed.scheme or '(none)'}")

    host = parsed.hostname
    if not host:
        raise HTTPException(400, "URL has no host")

    try:
        infos = socket.getaddrinfo(host, parsed.port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, socket.error, UnicodeError, ValueError):
        raise HTTPException(400, "unresolvable host")

    if not infos:
        raise HTTPException(400, "unresolvable host")

    # Check EVERY resolved address — a host may map to several.
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            raise HTTPException(400, "unresolvable host")
        if _is_blocked_ip(ip):
            raise HTTPException(400, "URL resolves to a non-public address")
