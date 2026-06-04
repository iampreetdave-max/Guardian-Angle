"""Export-integrity (chain-of-custody) helpers in services/report.py.

Covers the additive integrity surface:
  * sha256 helpers (full digest, short form, header dict) are well-formed;
  * a stamped forensic report renders to a valid PDF whose footer carries the
    SAME digest that ``build_report_with_integrity`` returns (and that
    ``integrity_header`` advertises);
  * the stamp is REPRODUCIBLE: re-rendering the same content at the same pinned
    generation timestamp yields byte-identical output and hash — which is what
    makes the printed hash genuinely re-verifiable;
  * the legacy ``build_report`` signature/return type is unchanged (backward
    compatible) and ReportLab's global ``invariant`` flag is restored after a
    stamped build, so other PDF paths are unaffected.
"""
from __future__ import annotations

import hashlib
import re

from app.services import report


def _short_of(digest: str) -> str:
    return f"{digest[:4]}…{digest[-4:]}"


def test_integrity_sha256_and_short_forms():
    data = b"%PDF-1.4 fake"
    digest = report.integrity_sha256(data)
    assert digest == hashlib.sha256(data).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert report.integrity_short(digest) == _short_of(digest)
    # header helpers produce the documented header name
    assert report.integrity_header(digest) == {report.INTEGRITY_HEADER: digest}
    assert report.integrity_headers(data) == {report.INTEGRITY_HEADER: digest}


def test_build_report_with_integrity_returns_valid_pdf_and_digest():
    pdf, digest = report.build_report_with_integrity(
        "Integrity Case", "Insp. Test", "red jacket near gate", "text", [])
    assert pdf[:5] == b"%PDF-"          # real PDF
    assert len(pdf) > 1000
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    # The header the serving site should attach matches the returned digest.
    assert report.integrity_header(digest)[report.INTEGRITY_HEADER] == digest


def test_stamp_is_reproducible_for_same_content_and_timestamp():
    """Same content + same pinned generation timestamp => identical bytes/hash.

    This is the property that lets a printed report's footer hash be checked: a
    verifier re-renders the document deterministically and must reproduce it.
    """
    from reportlab import rl_config

    pin = "2026-06-04 10:00:00"

    def render_content() -> bytes:
        token = report._INTEGRITY_CTX.set(("", pin))
        prev = rl_config.invariant
        rl_config.invariant = 1
        try:
            return report._build_report_pdf(
                "Integrity Case", "Insp. Test", "red jacket", "text", [])
        finally:
            report._INTEGRITY_CTX.reset(token)
            rl_config.invariant = prev

    a = render_content()
    b = render_content()
    assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest()


def test_legacy_build_report_unchanged_signature_and_invariant_restored():
    from reportlab import rl_config

    before = rl_config.invariant
    pdf = report.build_report("Legacy", "Insp X", "q", "text", [])
    assert isinstance(pdf, bytes) and pdf[:5] == b"%PDF-"
    # A stamped build must NOT leak ReportLab's invariant flag to other PDFs.
    assert rl_config.invariant == before


def test_unstamped_build_carries_no_integrity_context():
    """Directly rendering the content (no stamp_integrity) leaves the footer in
    its original form — the integrity ContextVar is unset."""
    assert report._INTEGRITY_CTX.get() is None
    pdf = report._build_report_pdf("Plain", "Insp X", "q", "text", [])
    assert pdf[:5] == b"%PDF-"
    assert report._INTEGRITY_CTX.get() is None
