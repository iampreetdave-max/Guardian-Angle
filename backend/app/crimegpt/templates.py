"""Document generation engine — branded ReportLab PDFs for the 7 statutory
Indian-police documents, filled from the unified case data pool.

Each builder takes the assembled context (case header + parties + seizures +
statements + suggested sections) and returns PDF bytes. The navy/gold
letterhead is reused from services/report.py so every CrimeGPT document carries
the same Cyber Crime Branch, Ahmedabad branding as the forensic report.

Multilingual: for language in {hi, gu} the free-text narrative paragraphs are
translated via the Arbiter LLM bridge (arbiter.llm.generate, which has an
offline fallback). Structural labels stay in English so the document is always
intelligible and the PDF is NEVER blocked when translation is unavailable.
"""
from __future__ import annotations

import io
import logging
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from ..services.fonts import register_indic_fonts, rich
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from ..arbiter import llm
from ..services.report import GOLD, INK, NAVY, _BAND_H, _on_page
from . import service as svc

log = logging.getLogger("visionscan.crimegpt.templates")


# ----------------------------------------------------------------- styles
def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("CGTitle", parent=styles["Title"],
                              textColor=NAVY, fontSize=15, spaceAfter=4))
    styles.add(ParagraphStyle("CGSub", parent=styles["Normal"], fontSize=9,
                              textColor=INK, alignment=1, spaceAfter=8))
    styles.add(ParagraphStyle("CGH", parent=styles["Heading2"], textColor=NAVY,
                              fontSize=11, spaceBefore=10, spaceAfter=4))
    styles.add(ParagraphStyle("CGBody", parent=styles["Normal"], fontSize=9.5,
                              leading=14, spaceAfter=4))
    styles.add(ParagraphStyle("CGMeta", parent=styles["Normal"], fontSize=9,
                              textColor=INK, leading=13))
    styles.add(ParagraphStyle("CGCell", parent=styles["Normal"], fontSize=8.5,
                              leading=11))
    styles.add(ParagraphStyle("CGSmall", parent=styles["Normal"], fontSize=8,
                              textColor=INK))
    return styles


def _esc(v) -> str:
    """Escape user-supplied text for ReportLab's mini-markup (it parses <…>) and
    wrap any Devanagari/Gujarati runs in a font that can draw them.

    Every string in this module already goes through here, so routing the font
    handling through it covers the whole document — including the hi/gu
    narratives this module generates by design, which previously came out of the
    exporter as blank boxes. rich() leaves pure-Latin text byte-identical.
    """
    if v is None:
        return ""
    return rich(v)


# ----------------------------------------------------------------- translation
def _localize(paragraph: str, language: str) -> str:
    """Return the narrative in the requested language.

    For en, returns as-is. For hi/gu, asks the Arbiter LLM bridge to translate;
    if the bridge is offline (returns None), the English text is returned with a
    short bilingual marker so the document is never blocked.
    """
    if language == "en" or not paragraph.strip():
        return paragraph
    lang_name = llm.LANGUAGES.get(language, "English")
    prompt = (
        f"Translate the following Indian police case narrative into {lang_name}. "
        "Keep proper nouns, names, section numbers and dates unchanged. Return "
        "only the translation, no preamble.\n\n"
        f"<<<UNTRUSTED_NARRATIVE>>>\n{paragraph}\n<<<END_NARRATIVE>>>"
    )
    try:
        out = llm.generate(prompt, language=language)
    except Exception:  # never let translation crash a PDF build
        out = None
    if out:
        return out
    return paragraph  # English fallback — labels stay English regardless


def _doc(title: str) -> tuple[SimpleDocTemplate, io.BytesIO]:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=_BAND_H + 18, bottomMargin=1.8 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, title=title,
    )
    return doc, buf


def _now() -> str:
    return datetime.now().strftime("%d-%m-%Y %H:%M")


# ----------------------------------------------------------------- shared blocks
def _header_block(styles, case: dict, doc_title: str, version: int,
                  language: str) -> list:
    team = case.get("team") or {}
    station = team.get("station") or "Cyber Crime Branch, Ahmedabad"
    fir = case.get("complaint_id")
    fir_str = f"FIR/Complaint No. {fir}" if fir else "FIR No. ____________"
    story = [
        Paragraph(_esc(doc_title), styles["CGTitle"]),
        Paragraph(f"{_esc(station)} &nbsp;·&nbsp; Gujarat Police", styles["CGSub"]),
    ]
    meta = (
        f"<b>Case No.:</b> {case.get('id', '____')} &nbsp;&nbsp; "
        f"<b>{_esc(fir_str)}</b><br/>"
        f"<b>Police Station:</b> {_esc(station)}<br/>"
        f"<b>Document:</b> {_esc(doc_title)} &nbsp;·&nbsp; <b>Version:</b> v{version} "
        f"&nbsp;·&nbsp; <b>Language:</b> {language.upper()}<br/>"
        f"<b>Generated:</b> {_now()}"
    )
    story.append(Paragraph(meta, styles["CGMeta"]))
    story.append(Spacer(1, 6))
    return story


def _sections_block(styles, sections: list[dict]) -> list:
    if not sections:
        return []
    story = [Paragraph("Sections Invoked (AI-suggested — verify before filing)",
                       styles["CGH"])]
    bns_all, proc_all, other_all = [], [], []
    for s in sections:
        bns_all += s.get("bns", [])
        proc_all += s.get("bnss", [])
        other_all += s.get("other", [])
    if bns_all:
        story.append(Paragraph("<b>BNS 2023:</b> " + _esc("; ".join(dict.fromkeys(bns_all))),
                               styles["CGBody"]))
    if other_all:
        story.append(Paragraph("<b>Special Acts:</b> " + _esc("; ".join(dict.fromkeys(other_all))),
                               styles["CGBody"]))
    if proc_all:
        story.append(Paragraph("<b>Procedure (BNSS):</b> " + _esc("; ".join(dict.fromkeys(proc_all))),
                               styles["CGBody"]))
    return story


def _parties_table(styles, parties: list[dict], roles: tuple[str, ...],
                   heading: str) -> list:
    rows = [p for p in parties if p["role"] in roles]
    if not rows:
        return []
    story = [Paragraph(heading, styles["CGH"])]
    data = [["#", "Name", "Age/Gender", "Address", "Phone", "ID Proof"]]
    for i, p in enumerate(rows, 1):
        ag = "/".join(x for x in [str(p["age"]) if p.get("age") else "",
                                  p.get("gender") or ""] if x) or "—"
        data.append([
            str(i),
            Paragraph(_esc(p.get("name")), styles["CGCell"]),
            Paragraph(_esc(ag), styles["CGCell"]),
            Paragraph(_esc(p.get("address") or "—"), styles["CGCell"]),
            Paragraph(_esc(p.get("phone") or "—"), styles["CGCell"]),
            Paragraph(_esc(p.get("id_proof") or "—"), styles["CGCell"]),
        ])
    t = Table(data, colWidths=[0.8 * cm, 3.6 * cm, 2.2 * cm, 5 * cm, 2.4 * cm, 3.2 * cm])
    t.setStyle(_grid_style())
    story.append(t)
    return story


def _grid_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd2e0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6fa")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ])


def _signature_block(styles, role_label: str = "Investigating Officer") -> list:
    data = [[
        Paragraph("Signature: ____________________<br/><br/>"
                  f"<b>{_esc(role_label)}</b><br/>Name &amp; Badge No.: ____________",
                  styles["CGSmall"]),
        Paragraph("Place: ____________________<br/>"
                  f"Date: {datetime.now().strftime('%d-%m-%Y')}<br/><br/>"
                  "Station Seal:", styles["CGSmall"]),
    ]]
    t = Table(data, colWidths=[9 * cm, 8 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 14)]))
    return [Spacer(1, 18), t]


def _disclaimer(styles) -> list:
    return [
        Spacer(1, 10),
        Paragraph(
            "Generated by CityShield · CrimeGPT from the unified case data pool. "
            "AI-suggested sections and drafted narrative MUST be verified by the "
            "investigating officer before use as an official record.",
            styles["CGSmall"]),
    ]


def _build(doc: SimpleDocTemplate, buf: io.BytesIO, story: list) -> bytes:
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()


# ----------------------------------------------------------------- narrative
def _case_narrative(case: dict, language: str) -> str:
    base = (case.get("description") or case.get("title")
            or "Brief facts of the case to be recorded by the investigating officer.")
    return _localize(base, language)


# ============================================================ DOCUMENT BUILDERS
def _purvani_chargesheet(ctx: dict) -> bytes:
    styles, language = _styles(), ctx["language"]
    case, pool, sections = ctx["case"], ctx["pool"], ctx["sections"]
    doc, buf = _doc("Purvani Chargesheet")
    story = _header_block(styles, case, "Purvani Chargesheet (Preliminary Charge-Sheet)",
                          ctx["version"], language)
    story += _sections_block(styles, sections)
    story.append(Paragraph("Brief Facts of the Case", styles["CGH"]))
    story.append(Paragraph(_esc(_case_narrative(case, language)), styles["CGBody"]))
    story += _parties_table(styles, pool["parties"], ("accused",), "Accused Person(s)")
    story += _parties_table(styles, pool["parties"], ("victim",), "Complainant / Victim(s)")
    story += _parties_table(styles, pool["parties"], ("witness",), "Witness(es)")
    if pool["seizures"]:
        story.append(Paragraph("Muddamal / Seized Articles", styles["CGH"]))
        data = [["#", "Article", "Qty", "Seized From"]]
        for i, s in enumerate(pool["seizures"], 1):
            data.append([str(i), Paragraph(_esc(s.get("item")), styles["CGCell"]),
                         Paragraph(_esc(s.get("quantity") or "—"), styles["CGCell"]),
                         Paragraph(_esc(s.get("seized_from") or "—"), styles["CGCell"])])
        t = Table(data, colWidths=[0.8 * cm, 7 * cm, 2 * cm, 7 * cm])
        t.setStyle(_grid_style()); story.append(t)
    story.append(Paragraph("Conclusion", styles["CGH"]))
    story.append(Paragraph(
        "On the basis of the above investigation, a prima facie case is made out "
        "against the accused under the sections noted above. The charge-sheet is "
        "submitted for the kind perusal of the Hon'ble Court.", styles["CGBody"]))
    story += _signature_block(styles)
    story += _disclaimer(styles)
    return _build(doc, buf, story)


def _medical_letter(ctx: dict) -> bytes:
    styles, language = _styles(), ctx["language"]
    case, pool = ctx["case"], ctx["pool"]
    doc, buf = _doc("Medical Treatment Letter")
    story = _header_block(styles, case, "Medical Treatment / Examination Letter",
                          ctx["version"], language)
    story.append(Paragraph("To,", styles["CGBody"]))
    story.append(Paragraph("The Medical Officer,<br/>Civil Hospital / Designated Health Centre, Ahmedabad.",
                           styles["CGBody"]))
    subjects = [p for p in pool["parties"] if p["role"] in ("accused", "victim")]
    subj = subjects[0] if subjects else None
    name = subj.get("name") if subj else "the person produced herewith"
    story.append(Paragraph("Subject: Request for medical examination / treatment.", styles["CGH"]))
    story.append(Paragraph(_esc(_localize(
        f"Kindly examine and provide necessary medical treatment to {name}, who is "
        f"connected with the above case, and furnish a medico-legal certificate "
        f"(MLC) recording the nature of injuries, age estimation where required, "
        f"and fitness to give a statement. The person is being produced before you "
        f"under police escort.", language)), styles["CGBody"]))
    if subj:
        story += _parties_table(styles, [subj], (subj["role"],), "Person to be Examined")
    story.append(Paragraph(
        "You are requested to preserve any samples of medico-legal importance and "
        "hand them over to the escorting officer against acknowledgement, for "
        "onward transmission to the Forensic Science Laboratory.", styles["CGBody"]))
    story += _signature_block(styles)
    story += _disclaimer(styles)
    return _build(doc, buf, story)


def _remand_request(ctx: dict) -> bytes:
    styles, language = _styles(), ctx["language"]
    case, pool, sections = ctx["case"], ctx["pool"], ctx["sections"]
    doc, buf = _doc("Remand Request Letter")
    story = _header_block(styles, case, "Application for Police Custody Remand (BNSS s.187)",
                          ctx["version"], language)
    story.append(Paragraph("To, The Hon'ble Court of the Learned Judicial Magistrate, Ahmedabad.",
                           styles["CGBody"]))
    story += _sections_block(styles, sections)
    story += _parties_table(styles, pool["parties"], ("accused",), "Accused Produced")
    story.append(Paragraph("Grounds for Police Custody", styles["CGH"]))
    story.append(Paragraph(_esc(_localize(
        "The accused named above has been arrested in connection with the present "
        "case. Custodial interrogation is necessary to recover the muddamal, "
        "identify co-accused, trace the proceeds of crime, and verify the "
        "disclosures already made. The facts of the case are as follows:", language)),
        styles["CGBody"]))
    story.append(Paragraph(_esc(_case_narrative(case, language)), styles["CGBody"]))
    story.append(Paragraph(
        "It is therefore prayed that the accused be remanded to police custody for "
        "a period as the Hon'ble Court deems fit, in the interest of a fair and "
        "complete investigation.", styles["CGBody"]))
    story += _signature_block(styles)
    story += _disclaimer(styles)
    return _build(doc, buf, story)


def _seizure_receipt(ctx: dict) -> bytes:
    styles, language = _styles(), ctx["language"]
    case, pool = ctx["case"], ctx["pool"]
    doc, buf = _doc("Seizure Receipt")
    story = _header_block(styles, case, "Seizure Receipt (Panchnama of Seizure)",
                          ctx["version"], language)
    story.append(Paragraph(_esc(_localize(
        "The following article(s) were seized in the course of investigation in the "
        "presence of the panch witnesses noted herein, and a true copy of this "
        "receipt has been handed over to the person from whom they were seized.",
        language)), styles["CGBody"]))
    if pool["seizures"]:
        data = [["#", "Article & Description", "Qty", "Seized From", "Date/Time", "Panch Witnesses"]]
        for i, s in enumerate(pool["seizures"], 1):
            desc = s.get("item") or ""
            if s.get("description"):
                desc += f" — {s['description']}"
            data.append([
                str(i), Paragraph(_esc(desc), styles["CGCell"]),
                Paragraph(_esc(s.get("quantity") or "—"), styles["CGCell"]),
                Paragraph(_esc(s.get("seized_from") or "—"), styles["CGCell"]),
                Paragraph(_esc(s.get("seized_at") or "—"), styles["CGCell"]),
                Paragraph(_esc(s.get("witness_names") or "—"), styles["CGCell"]),
            ])
        t = Table(data, colWidths=[0.7 * cm, 5.3 * cm, 1.6 * cm, 2.8 * cm, 2.4 * cm, 3.2 * cm])
        t.setStyle(_grid_style()); story.append(t)
    else:
        story.append(Paragraph("No seized articles have been recorded for this case yet.",
                               styles["CGBody"]))
    story += _signature_block(styles, "Seizing Officer")
    story.append(Paragraph("Panch Witness 1: ____________________ &nbsp;&nbsp; "
                           "Panch Witness 2: ____________________", styles["CGSmall"]))
    story += _disclaimer(styles)
    return _build(doc, buf, story)


def _court_custody_letter(ctx: dict) -> bytes:
    styles, language = _styles(), ctx["language"]
    case, pool = ctx["case"], ctx["pool"]
    doc, buf = _doc("Court Custody Letter")
    story = _header_block(styles, case, "Application for Judicial (Court) Custody (BNSS s.187)",
                          ctx["version"], language)
    story.append(Paragraph("To, The Hon'ble Court of the Learned Judicial Magistrate, Ahmedabad.",
                           styles["CGBody"]))
    story += _parties_table(styles, pool["parties"], ("accused",), "Accused Produced")
    story.append(Paragraph("Prayer for Judicial Custody", styles["CGH"]))
    story.append(Paragraph(_esc(_localize(
        "The police custody remand of the accused having concluded / not being "
        "required, the accused is produced before this Hon'ble Court with a request "
        "to be remanded to judicial custody pending further investigation and trial. "
        "There is apprehension that, if released, the accused may tamper with "
        "evidence or abscond.", language)), styles["CGBody"]))
    story.append(Paragraph(_esc(_case_narrative(case, language)), styles["CGBody"]))
    story.append(Paragraph(
        "It is prayed that the accused be remanded to judicial custody for such "
        "period as the Hon'ble Court deems fit.", styles["CGBody"]))
    story += _signature_block(styles)
    story += _disclaimer(styles)
    return _build(doc, buf, story)


def _accused_panchanama(ctx: dict) -> bytes:
    styles, language = _styles(), ctx["language"]
    case, pool = ctx["case"], ctx["pool"]
    doc, buf = _doc("Accused Panchanama")
    story = _header_block(styles, case, "Accused Panchanama (Arrest Panchnama)",
                          ctx["version"], language)
    story.append(Paragraph(_esc(_localize(
        "On the date and at the place noted below, in the presence of the panch "
        "witnesses, the accused named hereunder was arrested. At the time of "
        "arrest the following personal description, articles found on the person, "
        "and condition were noted by us, the panchas, and found to be true.",
        language)), styles["CGBody"]))
    accused = [p for p in pool["parties"] if p["role"] == "accused"]
    story += _parties_table(styles, accused, ("accused",), "Accused Arrested")
    for a in accused:
        if a.get("description"):
            story.append(Paragraph(
                f"<b>Physical description — {_esc(a.get('name'))}:</b> "
                f"{_esc(a.get('description'))}", styles["CGBody"]))
    story.append(Paragraph("Articles Found on the Accused", styles["CGH"]))
    if pool["seizures"]:
        for i, s in enumerate(pool["seizures"], 1):
            story.append(Paragraph(
                f"{i}. {_esc(s.get('item'))} "
                f"({_esc(s.get('quantity') or '1')}) — "
                f"{_esc(s.get('description') or 'recovered')}", styles["CGBody"]))
    else:
        story.append(Paragraph("Nil / to be recorded at the time of arrest.", styles["CGBody"]))
    story += _signature_block(styles, "Arresting Officer")
    story.append(Paragraph("Panch Witness 1: ____________________ &nbsp;&nbsp; "
                           "Panch Witness 2: ____________________", styles["CGSmall"]))
    story += _disclaimer(styles)
    return _build(doc, buf, story)


def _face_identification(ctx: dict) -> bytes:
    styles, language = _styles(), ctx["language"]
    case, pool = ctx["case"], ctx["pool"]
    doc, buf = _doc("Accused Face Identification Form")
    story = _header_block(styles, case, "Accused Face Identification Form",
                          ctx["version"], language)
    story.append(Paragraph(
        "To be used in conjunction with the Test Identification Parade (TIP) and "
        "any facial-recognition match generated by VisionScan. Affix photograph "
        "in the box and complete the descriptors below.", styles["CGBody"]))
    accused = [p for p in pool["parties"] if p["role"] == "accused"]
    for a in (accused or [None]):
        name = a.get("name") if a else "____________________"
        age = a.get("age") if a and a.get("age") else "____"
        gender = a.get("gender") if a and a.get("gender") else "____"
        desc = a.get("description") if a and a.get("description") else ""
        photo_cell = Paragraph("<para align='center'>[ Affix recent<br/>photograph ]"
                               "<br/><br/><br/></para>", styles["CGSmall"])
        info = (
            f"<b>Name:</b> {_esc(name)}<br/>"
            f"<b>Age:</b> {_esc(age)} &nbsp;&nbsp; <b>Gender:</b> {_esc(gender)}<br/>"
            f"<b>Identifying marks / description:</b> {_esc(desc) or '____________________'}<br/>"
            f"<b>Complexion:</b> ________ &nbsp; <b>Build:</b> ________ &nbsp; "
            f"<b>Height:</b> ________<br/>"
            f"<b>Face shape:</b> ________ &nbsp; <b>Distinctive features:</b> ________"
        )
        data = [[photo_cell, Paragraph(info, styles["CGCell"])]]
        t = Table(data, colWidths=[5 * cm, 12 * cm])
        t.setStyle(TableStyle([
            ("BOX", (0, 0), (0, 0), 0.8, INK),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f4f6fa")),
        ]))
        story.append(Spacer(1, 6)); story.append(t)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<b>VisionScan facial-match reference:</b> ____________________ "
        "(similarity score / camera / timestamp to be attached).", styles["CGBody"]))
    story.append(Paragraph(
        "Identified by witness: ____________________ &nbsp; "
        "Relationship to accused: ____________________", styles["CGBody"]))
    story += _signature_block(styles, "Identification Officer")
    story += _disclaimer(styles)
    return _build(doc, buf, story)


# ----------------------------------------------------------------- dispatch
_BUILDERS = {
    "purvani_chargesheet": _purvani_chargesheet,
    "medical_letter": _medical_letter,
    "remand_request": _remand_request,
    "seizure_receipt": _seizure_receipt,
    "court_custody_letter": _court_custody_letter,
    "accused_panchanama": _accused_panchanama,
    "face_identification": _face_identification,
}


def generate_pdf(doc_type: str, case: dict, pool: dict, sections: list[dict],
                 version: int, language: str = "en") -> bytes:
    """Build the requested document as PDF bytes. Raises KeyError on an unknown
    doc_type (the route validates against svc.DOC_TYPES first)."""
    builder = _BUILDERS[doc_type]
    ctx = {
        "case": case, "pool": pool, "sections": sections,
        "version": version, "language": language if language in ("en", "hi", "gu") else "en",
    }
    return builder(ctx)


# Re-exported for the route + tests.
DOC_TYPES = svc.DOC_TYPES
