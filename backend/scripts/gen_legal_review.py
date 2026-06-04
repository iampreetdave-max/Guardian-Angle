"""Generate the lawyer-review PDF for CrimeGPT's legal section catalogue.

Renders every entry of app.crimegpt.legal_sections.OFFENCE_MAP into a branded,
reviewer-friendly PDF so a lawyer can verify the BNS 2023 / BNSS / special-act
mappings, IPC cross-references and judgment citations before the hackathon
submission. Re-run any time the catalogue changes:

    cd backend && .venv\\Scripts\\python.exe -m scripts.gen_legal_review
"""
from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.crimegpt.legal_sections import OFFENCE_MAP

NAVY = colors.HexColor("#0a1124")
GOLD = colors.HexColor("#f4b23c")
LIGHT = colors.HexColor("#f5f6fa")
RED = colors.HexColor("#b3261e")

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "legal_review")
OUT_PATH = os.path.join(OUT_DIR, "CrimeGPT_Legal_Sections_Review.pdf")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("TitleNavy", parent=ss["Title"], textColor=NAVY, fontSize=22, spaceAfter=4))
    ss.add(ParagraphStyle("Sub", parent=ss["Normal"], textColor=colors.HexColor("#555a6e"), fontSize=11, spaceAfter=2))
    ss.add(ParagraphStyle("H2Navy", parent=ss["Heading2"], textColor=NAVY, spaceBefore=10, spaceAfter=4))
    ss.add(ParagraphStyle("EntryTitle", parent=ss["Heading3"], textColor=NAVY, fontSize=12.5, spaceBefore=8, spaceAfter=2))
    ss.add(ParagraphStyle("Body", parent=ss["Normal"], fontSize=9.5, leading=13))
    ss.add(ParagraphStyle("Mono", parent=ss["Normal"], fontName="Courier", fontSize=8.5, leading=11, textColor=colors.HexColor("#333")))
    ss.add(ParagraphStyle("Warn", parent=ss["Normal"], fontSize=9.5, leading=13, textColor=RED))
    return ss


def _header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 14 * mm, A4[0], 14 * mm, stroke=0, fill=1)
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(15 * mm, A4[1] - 9 * mm, "CrimeGPT — Legal Section Catalogue · Review Copy (Confidential)")
    canvas.setFillColor(colors.HexColor("#888"))
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
    canvas.drawString(15 * mm, 10 * mm, f"Generated {date.today().isoformat()} · VisionScan / CityShield prototype")
    canvas.restoreState()


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    ss = _styles()
    story = []

    # ---- Cover / instructions -------------------------------------------------
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("CrimeGPT — Legal Section Catalogue", ss["TitleNavy"]))
    story.append(Paragraph("Independent legal review requested · Kanad S.H.I.E.L.D. Hackathon 2026 (Cyber Crime Branch, Ahmedabad)", ss["Sub"]))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=2))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("What this system does", ss["H2Navy"]))
    story.append(Paragraph(
        "CrimeGPT is a prototype module that helps police officers draft case documents "
        "(chargesheet, remand request, seizure receipt, panchanama, etc.). When an officer types a "
        "free-text incident narrative, the system suggests potentially applicable legal provisions from the "
        "curated catalogue reproduced in this document. Suggestions are <b>advisory only</b> — an officer "
        "always confirms the final sections — but wrong mappings would still be embarrassing and unsafe, "
        "which is why we are asking for your review.", ss["Body"]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("What we need you to check", ss["H2Navy"]))
    for q in (
        "1. <b>BNS section numbers</b> — is each Bharatiya Nyaya Sanhita 2023 section number correct for the offence named?",
        "2. <b>IPC cross-references</b> — are the bracketed old-IPC equivalents the right \"closest equivalent\" for officer familiarity?",
        "3. <b>BNSS procedural references</b> — are the Bharatiya Nagarik Suraksha Sanhita 2023 references (FIR, inquest, magistrate complaint, etc.) correct?",
        "4. <b>Special acts</b> — IT Act, NDPS, Arms Act, POCSO, Dowry Prohibition, MV Act references: correct sections, correct usage?",
        "5. <b>Judgment citations</b> — each cited landmark judgment: correct citation, and squarely on point for the proposition stated?",
        "6. <b>Omissions</b> — any common Ahmedabad-relevant offence pattern we should add (especially cybercrime)?",
        "7. Entries flagged <b>VERIFY BEFORE USE</b> are ones we were least certain about — please prioritise those.",
    ):
        story.append(Paragraph(q, ss["Body"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "<b>How to respond:</b> simplest is to reply per entry number with \"OK\" or the correction "
        "(e.g. \"Entry 7: BNS 117 covers grievous hurt, but cite BNS 118 if a weapon was used\"). "
        "Anything you flag will be corrected before the system is demonstrated.", ss["Body"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Note: this is a hackathon prototype evaluated on seeded demonstration data. It is not deployed, "
        "and no real case decisions depend on it today.", ss["Warn"]))
    story.append(PageBreak())

    # ---- Summary table ---------------------------------------------------------
    story.append(Paragraph("Summary of all entries", ss["H2Navy"]))
    rows = [["#", "Offence pattern", "BNS 2023", "Special acts", "Flag"]]
    for i, e in enumerate(OFFENCE_MAP, 1):
        bns = "; ".join(s.split(" — ")[0] for s in e.get("bns", [])) or "—"
        other = "; ".join(s.split(" — ")[0] for s in e.get("other", [])) or "—"
        rows.append([
            str(i),
            Paragraph(e["label"], ss["Body"]),
            Paragraph(bns, ss["Body"]),
            Paragraph(other, ss["Body"]),
            "VERIFY" if e.get("verify") else "",
        ])
    t = Table(rows, colWidths=[9 * mm, 52 * mm, 50 * mm, 50 * mm, 17 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), GOLD),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("TEXTCOLOR", (4, 1), (4, -1), RED),
        ("FONTNAME", (4, 1), (4, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9cdd8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ---- Full entries ----------------------------------------------------------
    story.append(Paragraph("Full catalogue — entry by entry", ss["H2Navy"]))
    story.append(Paragraph(
        "Trigger keywords show which narrative words activate a suggestion; they are included so you can "
        "judge whether an entry could be suggested in the wrong situations.", ss["Body"]))
    story.append(Spacer(1, 2 * mm))

    for i, e in enumerate(OFFENCE_MAP, 1):
        flag = "  —  ⚠ VERIFY BEFORE USE" if e.get("verify") else ""
        story.append(Paragraph(f"Entry {i}: {e['label']}{flag}", ss["EntryTitle"]))
        story.append(HRFlowable(width="100%", color=GOLD if not e.get("verify") else RED, thickness=1))

        def add_field(name, items):
            if items:
                story.append(Paragraph(f"<b>{name}:</b>", ss["Body"]))
                for it in items:
                    story.append(Paragraph(f"&nbsp;&nbsp;• {it}", ss["Body"]))

        add_field("BNS 2023 (substantive)", e.get("bns"))
        add_field("BNSS 2023 (procedural)", e.get("bnss"))
        add_field("Special acts / other provisions", e.get("other"))
        add_field("Landmark judgments cited", e.get("judgments"))
        if not e.get("judgments"):
            story.append(Paragraph("<b>Landmark judgments cited:</b> none (deliberately omitted rather than risk a bad citation)", ss["Body"]))
        kw = ", ".join(e.get("keywords", []))
        syn = ", ".join(e.get("synonyms", []))
        story.append(Paragraph(f"<b>Trigger keywords:</b> <font face='Courier' size='8'>{kw}</font>", ss["Body"]))
        if syn:
            story.append(Paragraph(f"<b>Secondary terms:</b> <font face='Courier' size='8'>{syn}</font>", ss["Body"]))
        story.append(Spacer(1, 3 * mm))

    # ---- Closing ---------------------------------------------------------------
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=2))
    story.append(Paragraph("Thank you — corrections received before 18 June 2026 can be incorporated ahead of the submission deadline (20 June).", ss["Body"]))

    doc = SimpleDocTemplate(
        OUT_PATH, pagesize=A4,
        topMargin=20 * mm, bottomMargin=18 * mm, leftMargin=15 * mm, rightMargin=15 * mm,
        title="CrimeGPT Legal Sections — Review Copy",
    )
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    print(f"written: {OUT_PATH}")
    print(f"entries: {len(OFFENCE_MAP)} | flagged verify: {sum(1 for e in OFFENCE_MAP if e.get('verify'))}")


if __name__ == "__main__":
    build()
