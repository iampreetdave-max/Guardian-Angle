"""Forensic PDF report generation (ReportLab).

Produces a timestamped evidence report: a branded navy/gold header band, case
header, query details, and a grid of matched frames with camera id, timestamp,
similarity score, and detected objects — suitable for attaching to an
investigation file.

The branding helpers (``_find_logo``, ``_brand_header``, ``_brand_footer``)
are intentionally module-public so the security-report generator can reuse the
same letterhead, e.g. ``from app.services.report import _brand_header``.
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .fonts import register_indic_fonts, rich
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..config import get_settings
from ..database import get_conn
from ..core.ingestion import format_timestamp

log = logging.getLogger("visionscan.report")

# ---- Brand palette ----
NAVY = colors.HexColor("#0a1124")
INK = colors.HexColor("#324468")
GOLD = colors.HexColor("#f4b23c")
GOLD_DARK = colors.HexColor("#c9821a")

# Accent retained for existing styles; now the brand gold-dark instead of the
# old "#1e3a5f".
ACCENT = GOLD_DARK

# Height of the navy letterhead band.
_BAND_H = 70

# ---- Export-integrity (chain-of-custody) ----
# Header name carried on every served report PDF; mirrors the in-footer stamp.
INTEGRITY_HEADER = "X-Integrity-SHA256"

# Per-build integrity state the footer draws, set by ``stamp_integrity``. Holds
# a (footer_line, generated_at) pair: ``footer_line`` is the printed stamp and
# ``generated_at`` PINS the footer's "Generated …" timestamp for the build so
# BOTH passes (and any later re-verification render) produce byte-identical
# content — which is what makes the stamped hash genuinely reproducible.
#
# A ContextVar (not a global) so concurrent report builds in different request
# threads never bleed each other's hash into a footer. When unset the footer
# renders exactly as before (live ``datetime.now()``), so these helpers are
# purely additive and the legacy ``build_report``/CrimeGPT paths are untouched.
_INTEGRITY_CTX: ContextVar[tuple[str, str] | None] = ContextVar(
    "report_integrity", default=None)


def integrity_sha256(pdf_bytes: bytes) -> str:
    """Full lowercase hex SHA-256 of the rendered PDF payload — the canonical
    chain-of-custody digest for an exported report."""
    return hashlib.sha256(pdf_bytes).hexdigest()


def integrity_short(digest: str) -> str:
    """Human-readable short form of a hex digest: ``ab12…ef89`` (first 4 + last 4
    hex chars with an ellipsis), for the printed footer line."""
    d = digest or ""
    return f"{d[:4]}…{d[-4:]}" if len(d) >= 8 else d


def integrity_header(digest: str) -> dict[str, str]:
    """Response header dict for a known integrity digest. Use with the digest
    returned by ``build_report_with_integrity`` / ``stamp_integrity`` so the
    served ``X-Integrity-SHA256`` matches the value stamped in the PDF footer::

        pdf, digest = build_report_with_integrity(...)
        return Response(content=pdf, media_type="application/pdf",
                        headers={**integrity_header(digest), ...})
    """
    return {INTEGRITY_HEADER: digest}


def integrity_headers(pdf_bytes: bytes) -> dict[str, str]:
    """Response header dict computed from served PDF bytes (the delivered-bytes
    digest). For stamped reports prefer ``integrity_header(digest)`` so header and
    footer carry the same content hash."""
    return {INTEGRITY_HEADER: integrity_sha256(pdf_bytes)}


def stamp_integrity(build_fn) -> tuple[bytes, str]:
    """Render a PDF with a reproducible chain-of-custody footer, two-pass.

    ``build_fn`` is a zero-arg callable that builds and returns the PDF bytes
    (it must call ``_on_page`` / ``_brand_footer`` for the stamp to appear).

    Determinism is the whole point: rendering runs with ReportLab's ``invariant``
    flag on (fixed PDF timestamps/IDs) AND the footer's "Generated" time pinned,
    so the document bytes become a pure function of its content. That makes the
    stamped SHA-256 genuinely re-verifiable -- re-render the same content and you
    get the same hash.

      pass 1: render the *content* (blank stamp) -> hash those bytes.
      pass 2: render again with the footer carrying
              ``Integrity SHA-256: ab12...ef89 . generated <ts>``.

    Returns ``(final_pdf_bytes, sha256_hex)`` where ``sha256_hex`` is the pass-1
    content hash -- the value stamped in the footer AND the one to advertise in
    the ``X-Integrity-SHA256`` header (via ``integrity_header``), so the printed
    copy and the response header agree.

    Fail-soft: if the second pass raises, the (unstamped) first-pass bytes and
    their hash are returned so a report is never lost to a stamping error.
    """
    from reportlab import rl_config

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prev_invariant = rl_config.invariant
    rl_config.invariant = 1
    # Pass 1 -- content only, but with the "Generated" timestamp pinned so the
    # content bytes match what pass 2 (and any re-verification) will produce.
    token = _INTEGRITY_CTX.set(("", ts))
    try:
        content = build_fn()
        digest = integrity_sha256(content)
        stamp = f"Integrity SHA-256: {integrity_short(digest)} · generated {ts}"
        # Pass 2 -- same content, footer now carries the stamp line.
        _INTEGRITY_CTX.reset(token)
        token = _INTEGRITY_CTX.set((stamp, ts))
        try:
            stamped = build_fn()
            return stamped, digest
        except Exception:  # pragma: no cover - defensive: never lose a report
            log.warning("integrity re-render failed; serving unstamped PDF",
                        exc_info=True)
            return content, digest
    finally:
        _INTEGRITY_CTX.reset(token)
        rl_config.invariant = prev_invariant


def _find_logo() -> Path | None:
    """Return the first logo file that exists, else None (fail-soft).

    Search order: ``$VISIONSCAN_STATIC_DIR/logo.png``,
    ``backend/app/static/logo.png``, ``<repo>/frontend/public/logo.png``.
    Resolved relative to this file so it works regardless of CWD.
    """
    here = Path(__file__).resolve()
    app_dir = here.parents[1]          # backend/app
    repo_root = here.parents[3]        # repo root

    candidates: list[Path] = []
    static_env = os.environ.get("VISIONSCAN_STATIC_DIR")
    if static_env:
        candidates.append(Path(static_env) / "logo.png")
    candidates.append(app_dir / "static" / "logo.png")
    candidates.append(repo_root / "frontend" / "public" / "logo.png")

    for c in candidates:
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


def _brand_header(canvas, doc) -> None:
    """Draw the full-width navy letterhead band with logo + wordmark."""
    page_w, page_h = doc.pagesize
    band_top = page_h
    band_bottom = page_h - _BAND_H

    canvas.saveState()
    # Full-width navy band.
    canvas.setFillColor(NAVY)
    canvas.rect(0, band_bottom, page_w, _BAND_H, stroke=0, fill=1)

    left = doc.leftMargin
    text_x = left

    # Logo at left (preserve aspect, ~50pt tall) via ImageReader.
    logo = _find_logo()
    if logo is not None:
        try:
            img = ImageReader(str(logo))
            iw, ih = img.getSize()
            target_h = 50.0
            scale = target_h / float(ih) if ih else 1.0
            target_w = float(iw) * scale
            logo_y = band_bottom + (_BAND_H - target_h) / 2.0
            canvas.drawImage(
                img, left, logo_y, width=target_w, height=target_h,
                mask="auto", preserveAspectRatio=True,
            )
            text_x = left + target_w + 12
        except Exception:  # fail-soft: render wordmark only
            log.debug("logo render failed; rendering wordmark only", exc_info=True)

    # Wordmark + subtitle.
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(text_x, band_bottom + _BAND_H - 30,
                      "CityShield · VisionScan")
    canvas.setFillColor(colors.HexColor("#c8cfde"))  # light gray
    canvas.setFont("Helvetica", 8.5)
    canvas.drawString(
        text_x, band_bottom + _BAND_H - 46,
        "Unified AI Policing — Cyber Crime Branch, Ahmedabad",
    )

    # Thin gold rule under the band.
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(1.2)
    canvas.line(0, band_bottom, page_w, band_bottom)
    canvas.restoreState()


def _brand_footer(canvas, doc) -> None:
    """Draw a thin gold rule + confidential footer line with page number."""
    page_w, _ = doc.pagesize
    y = doc.bottomMargin - 14

    canvas.saveState()
    # Thin gold rule above the footer line.
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(0.8)
    canvas.line(doc.leftMargin, y + 10, page_w - doc.rightMargin, y + 10)

    # On an integrity-stamped build the "Generated" time is PINNED (so both
    # passes hash identically); otherwise it's live. Backward compatible: an
    # unstamped build behaves exactly as before.
    integ = _INTEGRITY_CTX.get()
    now = integ[1] if integ else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(doc.leftMargin, y, f"Generated {now}")
    canvas.drawCentredString(
        page_w / 2.0, y,
        "CONFIDENTIAL — For authorized investigation use only",
    )
    canvas.drawRightString(page_w - doc.rightMargin, y, f"Page {doc.page}")

    # Chain-of-custody stamp (only on the second integrity pass; see
    # stamp_integrity). Drawn just under the footer line in muted gold so a
    # printed copy carries its verifiable hash + generation time.
    if integ and integ[0]:
        canvas.setFillColor(GOLD_DARK)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawCentredString(page_w / 2.0, y - 9, integ[0])
    canvas.restoreState()


def _on_page(canvas, doc) -> None:
    """Combined page decorator for onFirstPage / onLaterPages."""
    _brand_header(canvas, doc)
    _brand_footer(canvas, doc)


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("VSTitle", parent=styles["Title"],
                              textColor=NAVY, fontSize=18))
    styles.add(ParagraphStyle("VSMeta", parent=styles["Normal"],
                              fontSize=9, textColor=INK))
    styles.add(ParagraphStyle("VSCell", parent=styles["Normal"], fontSize=8))
    return styles


def _build_report_pdf(
    case_title: str,
    investigator: str,
    query: str,
    query_type: str,
    frame_ids: list[int],
) -> bytes:
    """Render the forensic CCTV report to PDF bytes once. Self-contained (fresh
    buffer + story every call) so it can be invoked twice by ``stamp_integrity``
    without flowable-reuse issues. The behaviour is identical to the original
    ``build_report`` body."""
    settings = get_settings()
    styles = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        # Top margin clears the navy band (+ breathing room); bottom margin
        # leaves room for the gold footer rule + line.
        topMargin=_BAND_H + 18,
        bottomMargin=1.8 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        title=case_title,
    )

    story = []
    story.append(Paragraph("CCTV Investigation Report", styles["VSTitle"]))
    story.append(Spacer(1, 6))
    # Pin the body "Generated" time to the integrity build's timestamp when one
    # is active, so both stamp passes (and re-verification) hash identically;
    # otherwise live, as before.
    _integ = _INTEGRITY_CTX.get()
    now = _integ[1] if _integ else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # case_title / investigator / query are typed by the officer and may be in
    # Hindi or Gujarati; rich() wraps those runs in a font that can draw them.
    register_indic_fonts()
    meta = (
        f"<b>Case:</b> {rich(case_title)}<br/>"
        f"<b>Investigator:</b> {rich(investigator) or 'N/A'}<br/>"
        f"<b>Query ({query_type}):</b> {rich(query) or 'N/A'}<br/>"
        f"<b>Generated:</b> {now}<br/>"
        f"<b>Frames in report:</b> {len(frame_ids)}"
    )
    story.append(Paragraph(meta, styles["VSMeta"]))
    story.append(Spacer(1, 12))

    # Resolve frames (preserve caller-supplied order)
    if frame_ids:
        placeholders = ",".join("?" for _ in frame_ids)
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT f.id AS frame_id, f.timestamp_sec, f.thumbnail_path, "
                "v.camera_id, v.filename "
                "FROM frames f JOIN videos v ON v.id = f.video_id "
                f"WHERE f.id IN ({placeholders})",
                frame_ids,
            ).fetchall()
            by_id = {r["frame_id"]: r for r in rows}

            ordered = [by_id[fid] for fid in frame_ids if fid in by_id]
            cells = []
            row_buffer = []
            for r in ordered:
                img_path = settings.thumbnails_dir / r["thumbnail_path"]
                dets = conn.execute(
                    "SELECT label, COUNT(*) c FROM detections WHERE frame_id = ? "
                    "GROUP BY label ORDER BY c DESC LIMIT 4",
                    (r["frame_id"],),
                ).fetchall()
                det_str = ", ".join(f"{d['label']}({d['c']})" for d in dets) or "—"

                try:
                    img = RLImage(str(img_path), width=7.5 * cm, height=4.2 * cm)
                except Exception:
                    img = Paragraph("[image unavailable]", styles["VSCell"])

                caption = (
                    f"<b>{r['camera_id']}</b> @ {format_timestamp(r['timestamp_sec'])}<br/>"
                    f"Frame #{r['frame_id']} · {rich(r['filename'])}<br/>"
                    f"Objects: {det_str}"
                )
                cell = [img, Paragraph(caption, styles["VSCell"])]
                row_buffer.append(cell)
                if len(row_buffer) == 2:
                    cells.append(row_buffer)
                    row_buffer = []
            if row_buffer:
                row_buffer.append("")
                cells.append(row_buffer)

        if cells:
            table = Table(cells, colWidths=[8.5 * cm, 8.5 * cm])
            table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
            ]))
            story.append(table)

    footer = Paragraph(
        "Generated by VisionScan · Frames are AI-ranked candidates and should be "
        "verified by an investigator before use as evidence.",
        styles["VSMeta"],
    )
    story.append(Spacer(1, 12))
    story.append(footer)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()


def build_report(
    case_title: str,
    investigator: str,
    query: str,
    query_type: str,
    frame_ids: list[int],
) -> bytes:
    """Backward-compatible entry point: returns the stamped report PDF bytes.

    Now carries the chain-of-custody footer (``Integrity SHA-256: … · generated
    …``); the signature and return type are unchanged so existing callers keep
    working. Use ``build_report_with_integrity`` when you also need the digest for
    the ``X-Integrity-SHA256`` response header."""
    pdf, _digest = build_report_with_integrity(
        case_title, investigator, query, query_type, frame_ids)
    return pdf


def build_report_with_integrity(
    case_title: str,
    investigator: str,
    query: str,
    query_type: str,
    frame_ids: list[int],
) -> tuple[bytes, str]:
    """Render the forensic report with its integrity footer and return
    ``(pdf_bytes, sha256_hex)``. The hex digest is the one stamped in the footer;
    pass it (or the bytes) to ``integrity_headers`` at the serving site."""
    return stamp_integrity(lambda: _build_report_pdf(
        case_title, investigator, query, query_type, frame_ids))
