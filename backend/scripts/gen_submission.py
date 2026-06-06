"""Build the two PDFs the Kanad S.H.I.E.L.D. form asks for, for a single
submission covering all five problem statements:

  1. SUBMISSION-document.pdf  — one combined proposal document (platform +
     all 5 problem statements + live demo + validation + security + ER/arch).
  2. SUBMISSION-roadmap.pdf   — an implementation & deployment roadmap.

Reuses the branded helpers and per-statement content from gen_proposal.py so
the numbers stay live and consistent. Run from backend/ with PYTHONPATH=.:

    .venv\\Scripts\\python.exe -m scripts.gen_submission
"""
from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Reuse everything from the proposal generator so content stays in lock-step.
from scripts.gen_proposal import (
    CLIPS_URL,
    DEMO_ACCOUNTS,
    DEMO_URL,
    GITHUB_URL,
    GOLD,
    GOLD_DARK,
    HF_URL,
    INK,
    NAVY,
    OUT_DIR,
    SS,
    TEAM,
    TODAY,
    _BAND_H,
    _about_submitter,
    _architecture_diagram,
    _bullets,
    _criteria_matrix,
    _disclaimer_page,
    _how_prediction_works,
    _live_backtest,
    _live_demo_access,
    _on_page,
    _p,
    _security_summary,
    _specs,
    _table,
    _validation_deployment,
)

PROBLEM_IDS = [
    ("PS-69E9C85F9C307", "Cat 1", "VisionScan — Smart CCTV Analysis"),
    ("PS-69EEFE1294451", "Cat 2", "Crime Hotspot Mapping & Predictive Patrol Routing"),
    ("PS-69EEFDD4DA6E9", "Cat 2", "Unified Legal & Government Intelligence"),
    ("PS-69EEFDFB90B99", "Cat 2", "CrimeGPT — Crime Documentation & Legal Intelligence"),
    ("PS-69EEFE4F8CD1C", "Cat 2", "Open-Ended Innovation Platform for Smart Policing"),
]


def _doc(buf: io.BytesIO, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=_BAND_H + 18, bottomMargin=1.8 * cm,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm, title=title,
    )


def _render(story: list, title: str) -> tuple[bytes, int]:
    buf = io.BytesIO()
    page = {"n": 0}

    def _count(canvas, d):
        page["n"] = d.page
        _on_page(canvas, d)

    _doc(buf, title).build(list(story), onFirstPage=_count, onLaterPages=_count)
    return buf.getvalue(), page["n"]


def _cover(title: str, tagline: str, extra_rows: list[list[str]]) -> list:
    story = [Spacer(1, 18 * mm),
             HRFlowable(width="40%", color=GOLD, thickness=2, spaceAfter=10),
             _p(title, "VSCoverTitle"),
             _p(tagline, "VSCoverSub"),
             Spacer(1, 9 * mm)]
    rows = [
        ["Hackathon", "Kanad S.H.I.E.L.D. 2026 — Cyber Crime Branch, Ahmedabad City Police"],
        ["Live demo", DEMO_URL],
    ] + extra_rows + [["Team", TEAM], ["Date", TODAY]]
    t = Table(
        [[Paragraph(f"<b>{k}</b>", SS["VSCoverMeta"]), Paragraph(v, SS["VSCoverMeta"])]
         for k, v in rows],
        colWidths=[3.6 * cm, 13.2 * cm],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1ea")),
    ]))
    story.append(t)
    story.append(Spacer(1, 10 * mm))
    return story


# ===================================================== combined document
def build_combined(bt: dict | None) -> tuple[bytes, int]:
    specs = _specs(bt)
    story = _cover(
        "Unified AI Policing Platform",
        "One platform — five Cyber Crime Branch problem statements, solved together.",
        [["Problem IDs", " · ".join(f"{pid} ({cat})" for pid, cat, _ in PROBLEM_IDS)]],
    )
    story.append(_p(
        "This single document covers all five problem statements our team is "
        "submitting. They are not five separate projects — they are one working, "
        "deployed platform (<b>CityShield / VisionScan</b>) whose modules each answer "
        "one statement while sharing a single data model, security layer and live "
        "deployment. Each statement is presented below with the module that answers "
        "it and that statement's official evaluation criteria mapped to a concrete "
        "feature.", "VSCoverMeta"))
    story.append(PageBreak())

    # Executive summary
    story.append(_p("Executive summary", "VSH1"))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.2, spaceAfter=6))
    story.append(_p(
        "CityShield is an AI policing platform built for the Cyber Crime Branch, "
        "Ahmedabad. It fuses CCTV intelligence (semantic search + always-on anomaly "
        "detection), a GIS crime-hotspot map with backtested predictive risk and "
        "patrol-route optimisation, structured NCRP/1930 cyber-fraud intake, a legal-AI "
        "layer that drafts grounded BNS/BNSS/BSA documents, and a unified legal/"
        "government information feed — all on one CPU-only, offline-capable, "
        "security-hardened FastAPI + React stack."))
    story.append(_p(
        "Its defining property is a <b>genuine closed loop on one shared database</b>: a "
        "CCTV anomaly auto-creates a geo-tagged case, lifts the predictive risk for that "
        "locality, and dispatches the nearest patrol unit — the same data then flows into "
        "document automation and the GIS dashboard. Predictive accuracy is not asserted "
        "but measured (rolling-origin backtest: Hit-Rate@10 0.77, PAI 2.31×, beating "
        "frequency/prior/random baselines), and the platform runs live over HTTPS today."))

    # Platform at a glance
    story.append(_p("Platform at a glance", "VSH1"))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.2, spaceAfter=6))
    rows = [["Module", "What it does", "Answers"]] + [
        ["VisionScan", "CLIP semantic CCTV search (keyword / image / face / object), timestamped frames, exports.", "PS-…307 (Cat 1)"],
        ["Anomaly Watch", "Always-on hybrid CLIP+YOLO fire/smoke/accident/weapon/violence detection + live alerts.", "Cat-1 + Open-Ended"],
        ["GIS + Predictive", "react-leaflet map of 30 Ahmedabad localities; recency-weighted risk; NN+2-opt patrol routing.", "PS-…451 (flagship)"],
        ["Cyber intake + map", "NCRP/1930 fraud taxonomy, golden-hour banner; victim-location cyber-fraud map layer.", "PS-…451 cyber"],
        ["CrimeGPT / Arbiter", "7 police documents from one case pool; BNS/BNSS section intelligence; RAG legal AI.", "PS-…B99"],
        ["GovIntel", "Unified GR/notification/judgment search, cross-links, bookmarks, alerts.", "PS-…6E9"],
    ]
    story.append(_table(rows, [3.0 * cm, 10.8 * cm, 3.0 * cm]))
    story.append(PageBreak())

    # Architecture diagram
    story += _architecture_diagram()
    story.append(PageBreak())

    # Plain-language model explainer
    story += _how_prediction_works()
    story.append(PageBreak())

    # Five-statement mapping
    story.append(_p("Five problem statements, one platform", "VSH1"))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.2, spaceAfter=6))
    rows = [["#", "Problem statement", "ID", "Answered by"]]
    answered = ["VisionScan + Anomaly Watch", "GIS + predictive risk + patrol routing",
                "GovIntel legal feed", "CrimeGPT + Arbiter", "The integrated platform (closed loop)"]
    for i, ((pid, cat, name), by) in enumerate(zip(PROBLEM_IDS, answered), 1):
        rows.append([str(i), name, f"{pid}\n({cat})", by])
    story.append(_table(rows, [0.8 * cm, 7.6 * cm, 4.0 * cm, 4.4 * cm]))

    # Per-statement detail. KeepTogether keeps each text block and each matrix
    # intact so no single row orphans onto a near-empty page.
    for i, spec in enumerate(specs, 1):
        subtitle = (f"{spec['problem_id']} &middot; Category {spec['category']} &middot; "
                    f"answered by the {spec['tagline'].split('—')[0].strip()} module")
        block = [
            _p(f"Statement {i}: {spec['title']}", "VSH1"),
            _p(subtitle, "VSSmall"),
            HRFlowable(width="100%", color=GOLD, thickness=1.2, spaceAfter=6),
            _p("<b>The problem.</b> " + " ".join(spec["problem"])),
            _p("<b>How our platform solves it.</b>"),
            *[_p(para) for para in spec["solution"]],
        ]
        story.append(Spacer(1, 12))
        story.append(KeepTogether(block))
        story.append(Spacer(1, 4))
        story.append(KeepTogether(_criteria_matrix(spec["matrix_intro"], spec["matrix"])))

    # Shared sections
    story.append(PageBreak())
    story += _live_demo_access()
    story.append(PageBreak())
    story += _validation_deployment()
    story.append(PageBreak())
    story += _security_summary()
    story += _disclaimer_page()
    story += _about_submitter()

    return _render(story, "CityShield / VisionScan — Combined Proposal (5 statements)")


# ===================================================== roadmap document
_PHASES = [
    ("P0", "Foundation", "Done", GOLD,
     "VisionScan CCTV semantic search; CityShield RBAC platform (cases, complaints, "
     "notifications, analytics); Arbiter legal-AI core."),
    ("P1", "Sensing & GIS", "Done", GOLD,
     "Anomaly Watch (CLIP+YOLO); Ahmedabad GIS map (30 localities); recency-weighted "
     "predictive hotspot risk; NN+2-opt patrol-route optimisation."),
    ("P2", "Cyber & Automation", "Done", GOLD,
     "NCRP/1930 cyber-fraud intake + victim-location cyber map; closed-loop "
     "anomaly→case→dispatch; CrimeGPT document automation; GovIntel legal feed."),
    ("P3", "Hardening & Proof", "Done", GOLD,
     "Phase-3 OWASP security workstream + 77-test suite; backtesting (Hit-Rate@k, PAI) "
     "with baseline comparison; live HTTPS deployment; branded submission docs."),
    ("P4", "Pilot Readiness", "Next · 0–3 mo", colors.HexColor("#f6d68a"),
     "Independent legal-review sign-off; independent security / penetration test; "
     "real-data integration pilot (FIR / CCTNS / NCRP-1930 connectors); structured "
     "officer field-feedback loop; field-responsive mobile view; map-tile hardening."),
    ("P5", "Scale", "Future · 3–12 mo", colors.white,
     "Multi-city rollout; GPU acceleration for higher CCTV throughput; extra anomaly "
     "classes (disaster: flood / building-collapse); 112 / emergency-response "
     "integration; command-centre analytics."),
]


def _timeline() -> Drawing:
    W, H = 500, 120
    d = Drawing(W, H)
    n = len(_PHASES)
    gap = 6
    seg = (W - 20 - gap * (n - 1)) / n
    x = 10
    for code, name, status, fill, _ in _PHASES:
        future = fill is colors.white
        d.add(Rect(x, 50, seg, 30, rx=4, ry=4, fillColor=fill, strokeColor=NAVY, strokeWidth=1))
        d.add(String(x + seg / 2, 61, code, fontName="Helvetica-Bold", fontSize=9,
                     fillColor=(NAVY if not future else INK), textAnchor="middle"))
        d.add(String(x + seg / 2, 86, name, fontName="Helvetica-Bold", fontSize=6.6,
                     fillColor=NAVY, textAnchor="middle"))
        d.add(String(x + seg / 2, 40, status, fontName="Helvetica", fontSize=6.2,
                     fillColor=GOLD_DARK if not future else colors.HexColor("#777"),
                     textAnchor="middle"))
        x += seg + gap
    # baseline arrow
    d.add(Rect(10, 47, W - 20, 1.4, fillColor=GOLD_DARK, strokeColor=GOLD_DARK))
    return d


def build_roadmap() -> tuple[bytes, int]:
    story = _cover(
        "Implementation & Deployment Roadmap",
        "From a working, deployed prototype to a pilot-ready policing platform.",
        [["Problem IDs", " · ".join(pid for pid, _, _ in PROBLEM_IDS)]],
    )
    story.append(_p("Where we are today", "VSH1"))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.2, spaceAfter=6))
    story.append(_p(
        "Unlike a concept pitch, the platform is <b>already built, deployed and "
        "measured</b>. Phases P0–P3 below are complete: all five modules run on one "
        "codebase, the predictive model is backtested and beats naive baselines, the "
        "security controls are pinned by a 77-test regression suite, and the system is "
        "live over HTTPS on a cloud VM provisioned from free platform credits — at no "
        "infrastructure cost. The roadmap ahead (P4–P5) is about moving from a "
        "synthetic-data prototype to a real-data pilot with the Cyber Crime Branch."))
    story.append(Spacer(1, 6))
    story.append(_timeline())
    story.append(Spacer(1, 8))

    story.append(PageBreak())
    story.append(_p("Phase detail", "VSH1"))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.2, spaceAfter=6))
    rows = [["Phase", "Status", "Key deliverables"]]
    for code, name, status, _fill, deliver in _PHASES:
        rows.append([f"<b>{code} · {name}</b>", status, deliver])
    story.append(_table(rows, [3.4 * cm, 2.8 * cm, 11.4 * cm]))
    story.append(PageBreak())

    story.append(_p("The road ahead — what a pilot would add", "VSH1"))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.2, spaceAfter=6))
    story += _bullets([
        "<b>Real-data integration.</b> Replace the synthetic Ahmedabad dataset with live "
        "FIR / complaint / CCTNS and NCRP-1930 feeds via additive connectors — the schema "
        "and APIs are already designed for this (no rewrite).",
        "<b>Independent assurance.</b> Complete the in-progress legal review (practising "
        "advocates) and commission an independent security / penetration test before any "
        "live deployment with real citizen data.",
        "<b>Officer-in-the-loop.</b> A structured feedback programme with serving officers "
        "(including a senior-officer / IPS review being arranged) to tune hotspot zones, "
        "patrol beats and document templates to real workflows.",
        "<b>Field & scale.</b> Field-responsive mobile view; GPU acceleration for "
        "city-scale CCTV; extra anomaly classes for disaster response; integration with "
        "112 / emergency dispatch.",
    ])

    story.append(_p("Risks &amp; mitigations", "VSH1"))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.2, spaceAfter=6))
    rows = [["Risk", "Mitigation"]]
    rows += [
        ["Predictive policing bias / feedback loops",
         "Explainable model (every score decomposes into its terms); human-in-the-loop; "
         "advisory-only outputs; documented data-provenance and disclaimer."],
        ["Wrong legal section suggested",
         "Suggestions are advisory; officer confirms; catalogue under independent legal "
         "review with explicit verify-before-use flags."],
        ["Sensitive data exposure",
         "RBAC, audit logging, lockdown, SSRF + prompt-injection guards, rate-limited "
         "exports; OWASP Top-10 coverage; offline-capable (no data leaves the deployment)."],
        ["Demo / venue connectivity",
         "Offline-first design runs with Wi-Fi unplugged; pre-cached tiles; recorded "
         "fallback; live HTTPS deployment as primary."],
    ]
    story.append(_table(rows, [5.4 * cm, 12.2 * cm]))

    story.append(_p("Sustainability &amp; cost", "VSH1"))
    story.append(HRFlowable(width="100%", color=GOLD, thickness=1.2, spaceAfter=6))
    story.append(_p(
        "The platform is CPU-only, offline-capable, and uses no paid AI APIs, so it runs "
        "with no recurring licensing or per-query cost. The live demo is hosted on free "
        "Microsoft Azure for Students credits at zero infrastructure cost; in production "
        "it can run on a modest government VM or commodity on-premise hardware. This makes "
        "sustained, real-world adoption by the department financially realistic."))
    story += _disclaimer_page()
    story += _about_submitter()

    return _render(story, "CityShield / VisionScan — Implementation Roadmap")


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    print("[submission] running live backtest for the combined document...")
    bt = _live_backtest()
    if bt:
        print(f"[submission] backtest OK: {bt['headline']}")

    out = []
    for name, fn in (("SUBMISSION-document.pdf", lambda: build_combined(bt)),
                     ("SUBMISSION-roadmap.pdf", build_roadmap)):
        pdf, pages = fn()
        path = os.path.join(OUT_DIR, name)
        with open(path, "wb") as fh:
            fh.write(pdf)
        out.append((name, pages, pdf[:4] == b"%PDF", len(pdf), path))

    print("\n" + "=" * 78)
    print("SUBMISSION PDFs WRITTEN")
    print("=" * 78)
    ok_all = True
    for name, pages, ok, size, path in out:
        ok_all &= ok
        print(f"  [{'OK  ' if ok else 'BAD '}] {name:<26s} {pages:>2d} pp  {size/1024:6.1f} KB  {path}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
