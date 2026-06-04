"""Unit tests for the SSRF guard (assert_public_url).

All cases use literal IPs or `localhost` so the suite never depends on live DNS
for a remote name (which would make CI flaky/offline-unfriendly)."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.net_guard import assert_public_url


@pytest.mark.parametrize("url", [
    "http://127.0.0.1",            # loopback
    "http://localhost:8000",       # loopback (resolves locally, not remote DNS)
    "http://169.254.169.254",      # link-local cloud metadata endpoint
    "http://10.0.0.1",             # RFC1918 private
    "rtsp://192.168.1.4",          # private LAN camera (allowed scheme, bad host)
])
def test_blocks_private_and_loopback(url):
    with pytest.raises(HTTPException) as ei:
        assert_public_url(url)
    assert ei.value.status_code == 400


def test_blocks_unsupported_scheme():
    with pytest.raises(HTTPException) as ei:
        assert_public_url("ftp://example.com/resource")
    assert ei.value.status_code == 400


def test_allows_public_ip():
    # 8.8.8.8 is a global, public address — should pass without raising.
    assert_public_url("http://8.8.8.8")
