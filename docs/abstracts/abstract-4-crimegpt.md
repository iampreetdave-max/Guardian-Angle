# CrimeGPT – AI-Powered Automation for Crime Documentation and Legal Intelligence

**Problem ID:** PS-69EEFDFB90B99 · **Category:** 2
**Hackathon:** Kanad S.H.I.E.L.D. 2026 — Cyber Crime Branch, Ahmedabad City
**Team:** _[team name placeholder]_ · **Members:** _[member placeholder]_

---

## Problem

Across a case lifecycle — from a victim's first report to the accused's arrest and
remand — officers hand-produce chargesheets, remand requests, seizure receipts,
medical letters, court-custody letters, and face-identification forms, re-entering
the same names, addresses, sections, and seized items into each, which is slow and
invites errors and omissions. Officers also struggle to quickly map an incident
narrative to the right BNS/BNSS/BSA sections and relevant case law, slowing
investigation and prosecution.

## Proposed Solution

CrimeGPT automates the documentation lifecycle from a **single unified case-data
pool**: an officer enters names, addresses, statements, sections, and seized items
once, and the document engine generates all eight Gujarat-police documents
(Purvani Chargesheet, Medical Treatment Letter, Remand Request, Seizure Receipt,
Court Custody Letter, Accused Panchanama, Accused Face Identification Form, and a
running Case Diary) with no re-entry. Its differentiator is **legal intelligence
grounded in real law, not hallucination**: the Arbiter module runs RAG over a
local IPC/IT-Act/CrPC + BNS/BNSS/BSA corpus and suggests applicable sections and
landmark judgments from an incident summary, citing only retrieved provisions —
guarded against prompt injection and validated so it never invents a section.
Gemini polishes drafts when a key is present; a deterministic citation-grounded
template produces the same documents fully offline. Output is multilingual
(English/Hindi/Gujarati).

## Methodology

- **Data / case pool:** A `case_documents`-backed unified pool (already in the
  schema) holds entities once; entries are editable and traceable, and every
  document renders from that shared pool to eliminate duplication.
- **Models:** Arbiter RAG — MiniLM/ChromaDB retrieval over a legal corpus →
  section + judgment suggestions; FIR/document composition via
  Gemini-with-offline-fallback. A timeline Case Diary logs investigative steps,
  witness interaction, and evidence seizure from complaint to arrest. Sanitization
  + UNTRUSTED-fence prompt-injection guards and a citation validator wrap every
  LLM call so output cites only corpus-grounded sections.
- **Validation:** Generated documents are checked for shared-data consistency
  (the same name/section appears identically across forms); section suggestions
  are evaluated against the retrieved corpus; offline and online paths produce the
  same structured documents. Keyword/case-number search and a version/audit trail
  cover retrieval and traceability.
- **Deployment:** FastAPI + SQLite case store; ReportLab branded PDFs; JWT/RBAC,
  audit log, lockdown; one-command Docker; runs offline on CPU.

## Tools & Technologies

Python · FastAPI · SQLite · ChromaDB + MiniLM (RAG) · Gemini-with-offline-fallback ·
ReportLab (document PDFs) · React + Vite · JWT/RBAC + OWASP security middleware +
prompt-injection guards · Docker. Companion modules: VisionScan evidence frames
and GovIntel legal feed attach into the same case.

## Key Differentiators

- **Accurate, duplication-free generation:** one case-data pool drives all eight
  documents — the core evaluation criterion — so a name or section entered once is
  consistent everywhere.
- **Grounded legal section mapping:** RAG over a real BNS/BNSS/BSA + IPC/IT-Act
  corpus suggests sections and case law and cites only retrieved provisions;
  output is citation-validated and never invents law.
- **Chronological Case Diary:** an automated timeline from first report to arrest,
  with version history and an audit trail.
- **Multilingual & offline:** English/Hindi/Gujarati input and output; full offline
  template path means it works without a Gemini key or network.
- **Security-hardened:** prompt-injection defences, JWT revocation, brute-force
  lockout, and a documented internal security-testing report.

## Expected Impact

By generating an entire case's documentation from one data entry and surfacing the
applicable BNS/BNSS/BSA sections and judgments at the point of writing, CrimeGPT
can cut documentation time and transcription errors sharply while keeping a
complete, auditable case diary. The prototype demonstrates single-pool generation
of multiple court-ready documents and grounded section suggestions offline, making
it deployable inside the Cyber Crime Branch workflow without cloud dependence.

> AI section suggestions and draft documents are decision-support outputs that an
> investigating officer must review and verify before filing.
