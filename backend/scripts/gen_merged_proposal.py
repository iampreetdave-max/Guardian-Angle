"""Generate ONE merged hackathon proposal PDF for the top-three Category-II
problem statements, reusing every section builder from ``gen_proposal`` so the
branding, security summary, live-backtest evidence and disclaimer stay identical
and self-consistent.

The merged document covers — in order — the three statements recommended as the
strongest fit for the CityShield / VisionScan platform:

    1. KANADSHIELD26_P2_07  (PS-69EEFE1294451)  Crime Hotspot + Predictive Patrol  [flagship]
    2. KANADSHIELD26_P2_06  (PS-69EEFDFB90B99)  CrimeGPT — Crime Documentation & Legal Intelligence
    3. KANADSHIELD26_P2_10  (PS-69EEFE4F8CD1C)  Open-Ended Innovation Platform for Smart Policing

Shared sections (architecture, the plain-language model explainer, the LIVE
backtest evidence table, live-demo access, validation/economics, the OWASP
security summary, the disclaimer and the about-the-participant page) appear once.

Run from backend/:
    PYTHONPATH=. python scripts/gen_merged_proposal.py
"""
from __future__ import annotations

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.dirname(HERE)
sys.path.insert(0, BACKEND)
sys.path.insert(0, HERE)

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import gen_proposal as G  # the canonical builders + brand palette + styles

# Order of the three statements in the merged document (flagship first).
ORDER = ["2-crime-hotspot", "4-crimegpt", "5-open-ended"]
OUT_PATH = os.path.join(G.OUT_DIR, "SUBMISSION-top3.pdf")


def _ids(spec: dict) -> str:
    """`KANADSHIELD26_P2_xx · PS-xxx` (catalogue ID first — that is what the
    organiser's spreadsheet expects)."""
    kanad = G.KANAD_ID.get(spec["problem_id"])
    return f"{kanad} · {spec['problem_id']}" if kanad else spec["problem_id"]


# ============================================================ cover
def _merged_cover(specs: list[dict]) -> list:
    story = [Spacer(1, 18 * mm)]
    logo = G._find_logo()
    if logo is not None:
        try:
            from reportlab.platypus import Image as RLImage
            from reportlab.lib.utils import ImageReader

            iw, ih = ImageReader(str(logo)).getSize()
            target_h = 30 * mm
            scale = target_h / float(ih) if ih else 1.0
            img = RLImage(str(logo), width=float(iw) * scale, height=target_h)
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Spacer(1, 8 * mm))
        except Exception:
            pass

    story.append(HRFlowable(width="40%", color=G.GOLD, thickness=2, spaceAfter=10))
    story.append(G._p("Unified AI Policing Platform", "VSCoverTitle"))
    story.append(G._p(
        "Three Cyber Crime Branch problem statements — one deployed, measured, "
        "security-hardened system.", "VSCoverSub"))
    story.append(Spacer(1, 10 * mm))

    statements_cell = Paragraph(
        "<br/>".join(f"{_ids(s)} — {G._esc(s['title'])}" for s in specs),
        G.SS["VSCoverMeta"])
    meta_rows = [
        [Paragraph("<b>Problem statements</b>", G.SS["VSCoverMeta"]), statements_cell],
        [Paragraph("<b>Category</b>", G.SS["VSCoverMeta"]),
         Paragraph("Category II — all three", G.SS["VSCoverMeta"])],
        [Paragraph("<b>Hackathon</b>", G.SS["VSCoverMeta"]),
         Paragraph("Kanad S.H.I.E.L.D. 2026 — Cyber Crime Branch, Ahmedabad City Police",
                   G.SS["VSCoverMeta"])],
        [Paragraph("<b>Live demo</b>", G.SS["VSCoverMeta"]),
         Paragraph(G.DEMO_URL, G.SS["VSCoverMeta"])],
        [Paragraph("<b>Participant</b>", G.SS["VSCoverMeta"]),
         Paragraph(G._esc(G.TEAM), G.SS["VSCoverMeta"])],
        [Paragraph("<b>Date</b>", G.SS["VSCoverMeta"]),
         Paragraph(G.TODAY, G.SS["VSCoverMeta"])],
    ]
    t = Table(meta_rows, colWidths=[4 * cm, 12.5 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1ea")),
    ]))
    story.append(t)
    story.append(Spacer(1, 12 * mm))
    story.append(G._p(
        "This single document covers the three problem statements submitted under "
        "this individual entry. They are not three separate projects — they are one "
        "working, deployed platform (CityShield / VisionScan) whose modules each "
        "answer one statement while sharing a single data model, security layer and "
        "live deployment. Each statement is presented with the module that answers it "
        "and that statement's official evaluation criteria mapped to a concrete "
        "feature.", "VSCoverMeta"))
    story.append(PageBreak())
    return story


# ============================================================ executive summary
def _exec_summary(specs: list[dict]) -> list:
    out = [G._p("Executive summary", "VSH1"),
           HRFlowable(width="100%", color=G.GOLD, thickness=1.2, spaceAfter=6)]
    out.append(G._p(
        "CityShield is an AI policing platform built for the Cyber Crime Branch, "
        "Ahmedabad. On one CPU-only, offline-capable, security-hardened FastAPI + "
        "React stack it fuses a GIS crime-hotspot map with backtested predictive risk "
        "and patrol-route optimisation, a legal-AI layer that drafts grounded "
        "BNS/BNSS/BSA documents from a single case-data pool, CCTV intelligence "
        "(semantic search + always-on anomaly detection), structured NCRP/1930 "
        "cyber-fraud intake, and a unified legal/government feed."))
    out.append(G._p(
        "Its defining property is a <b>genuine closed loop on one shared database</b>: "
        "a CCTV anomaly auto-creates a geo-tagged case, lifts the predictive risk for "
        "that locality, and dispatches the nearest patrol unit — the same data then "
        "flows into document automation and the GIS dashboard. Predictive accuracy is "
        "not asserted but <b>measured</b> (rolling-origin backtest, beating "
        "frequency/prior/random baselines — see the Evidence page), and the platform "
        "<b>runs live over HTTPS today</b> on Microsoft Azure."))

    out.append(G._p("Three statements, one platform", "VSH2"))
    rows = [["#", "Problem statement", "Official ID", "Answered by"]]
    answered = {
        "2-crime-hotspot": "GIS + predictive risk + patrol routing",
        "4-crimegpt": "CrimeGPT + Arbiter legal AI",
        "5-open-ended": "The integrated platform (closed loop)",
    }
    for i, s in enumerate(specs, 1):
        rows.append([str(i), G._esc(s["title"]), _ids(s), answered[s["slug"]]])
    out.append(G._table(rows, [0.9 * cm, 6.1 * cm, 5.2 * cm, 4.3 * cm]))
    out.append(Spacer(1, 6))

    out.append(G._p("Platform at a glance", "VSH2"))
    glance = [
        ["Module", "What it does", "Answers"],
        ["GIS + Predictive + Patrol",
         "react-leaflet map of 30 Ahmedabad localities; recency-weighted risk; "
         "NN + 2-opt patrol routing",
         "P2_07 (flagship)"],
        ["CrimeGPT / Arbiter",
         "7 statutory police documents from one case pool; BNS/BNSS section "
         "intelligence; RAG legal AI",
         "P2_06"],
        ["CityShield closed loop",
         "Anomaly &rarr; auto-case &rarr; risk bump &rarr; nearest-unit dispatch on "
         "one shared model; RBAC; citizen portal",
         "P2_10"],
        ["Integrated companions",
         "VisionScan CCTV semantic search, Anomaly Watch detection, GovIntel legal "
         "feed — on the same stack",
         "all three"],
    ]
    out.append(G._table(glance, [4.2 * cm, 9.6 * cm, 2.7 * cm]))
    return out


# ============================================================ per-statement block
def _statement_block(i: int, spec: dict) -> list:
    out = [PageBreak(),
           G._p(f"Statement {i}: {G._esc(spec['title'])}", "VSH1"),
           HRFlowable(width="100%", color=G.GOLD, thickness=1.2, spaceAfter=4),
           G._p(f"{_ids(spec)} · Category {spec['category']} · answered by the "
                f"{spec['tagline']} module", "VSSmall")]

    out.append(G._p("<b>The problem.</b>"))
    for para in spec["problem"]:
        out.append(G._p(para))
    out.append(G._p("<b>How the platform solves it.</b>"))
    for para in spec["solution"]:
        out.append(G._p(para))

    out += G._methodology(spec["methodology"])
    out += G._criteria_matrix(spec["matrix_intro"], spec["matrix"])
    return out


# ============================================================ build
def build() -> int:
    os.makedirs(G.OUT_DIR, exist_ok=True)
    print("[merged] running live predictive backtest for the flagship evidence page...")
    bt = G._live_backtest()
    if bt is not None:
        print(f"[merged] backtest OK: {bt['headline']}")

    by_slug = {s["slug"]: s for s in G._specs(bt)}
    specs = [by_slug[s] for s in ORDER]

    story: list = []
    story += _merged_cover(specs)
    story += _exec_summary(specs)
    story.append(PageBreak())
    story += G._architecture_diagram()
    story.append(PageBreak())
    story += G._how_prediction_works(bt)
    for i, spec in enumerate(specs, 1):
        story += _statement_block(i, spec)
    story.append(PageBreak())
    story += G._evidence_flagship(bt)
    story.append(PageBreak())
    story += G._live_demo_access()
    story.append(PageBreak())
    story += G._validation_deployment()
    story.append(Spacer(1, 8))
    story += G._security_summary()
    story += G._disclaimer_page()
    story += G._about_submitter()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=G._BAND_H + 18, bottomMargin=1.8 * cm,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        title="Unified AI Policing Platform — Top 3 (Kanad S.H.I.E.L.D. 2026)",
    )
    page_counter = {"n": 0}

    def _count(canvas, d):
        page_counter["n"] = d.page
        G._on_page(canvas, d)

    doc.build(list(story), onFirstPage=_count, onLaterPages=_count)
    pdf_bytes = buf.getvalue()
    with open(OUT_PATH, "wb") as fh:
        fh.write(pdf_bytes)

    ok = pdf_bytes[:4] == b"%PDF"
    print("\n" + "=" * 78)
    print("MERGED PROPOSAL WRITTEN")
    print("=" * 78)
    print(f"  [{'OK ' if ok else 'BAD'}] {page_counter['n']:>2d} pp  "
          f"{len(pdf_bytes)/1024:6.1f} KB  {OUT_PATH}")
    print(f"  flagship evidence: "
          f"{'LIVE backtest embedded' if bt else 'backtest NOT reproduced (noted in PDF)'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(build())
