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

import io
import logging
import os
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(doc.leftMargin, y, f"Generated {now}")
    canvas.drawCentredString(
        page_w / 2.0, y,
        "CONFIDENTIAL — For authorized investigation use only",
    )
    canvas.drawRightString(page_w - doc.rightMargin, y, f"Page {doc.page}")
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


def build_report(
    case_title: str,
    investigator: str,
    query: str,
    query_type: str,
    frame_ids: list[int],
) -> bytes:
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
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta = (
        f"<b>Case:</b> {case_title}<br/>"
        f"<b>Investigator:</b> {investigator or 'N/A'}<br/>"
        f"<b>Query ({query_type}):</b> {query or 'N/A'}<br/>"
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
                    f"Frame #{r['frame_id']} · {r['filename']}<br/>"
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
