"""Generate the CityShield · VisionScan security testing PDF.

Two steps, one command:

  1. Run the security regression suite under ``backend/tests/`` in a subprocess,
     capturing the pass/fail summary line (and any failures).
  2. Render ``docs/SECURITY_TESTING_REPORT.pdf`` with ReportLab, reusing the
     exact navy/gold letterhead helpers (``_brand_header`` / ``_brand_footer``)
     from ``app.services.report`` so the security report shares the platform's
     CCTV-evidence-report branding.

Run from backend/ (PowerShell):
    .\\.venv\\Scripts\\python.exe scripts\\gen_security_report.py

The intent is an artefact the Cyber Crime Branch can hand to a reviewer: it
opens with a live, machine-checked test verdict, then walks the OWASP coverage,
the AI threat model, and the findings that were closed — not a templated
boilerplate report, but the actual state of this build.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# --- paths -------------------------------------------------------------------
# This file lives at backend/scripts/gen_security_report.py.
_HERE = Path(__file__).resolve()
BACKEND_DIR = _HERE.parents[1]                 # backend/
REPO_ROOT = _HERE.parents[2]                   # repo root
TESTS_DIR = BACKEND_DIR / "tests"
DOCS_DIR = REPO_ROOT / "docs"
PDF_PATH = DOCS_DIR / "SECURITY_TESTING_REPORT.pdf"

# Make ``app`` importable when run from anywhere.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Brand helpers + palette — reused verbatim from the evidence-report module so
# both documents carry identical CityShield letterhead branding.
from app.services.report import (  # noqa: E402
    GOLD,
    GOLD_DARK,
    INK,
    NAVY,
    _brand_footer,
    _brand_header,
    _BAND_H,
)

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    HRFlowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# --------------------------------------------------------------------------- #
# Step 1 — run the suite, capture the verdict.
# --------------------------------------------------------------------------- #
def run_pytest() -> dict:
    """Run the security suite in a subprocess and parse pytest's summary.

    Returns a dict: {ok, passed, failed, errored, summary, returncode, raw_tail}.
    Never raises — a non-zero pytest exit is reported, not fatal, so the PDF can
    still be produced documenting the failure.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(BACKEND_DIR)
    env.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

    print(f"Running security suite: pytest {TESTS_DIR} ...")
    # No -q: the terse mode can drop the final "N passed" line from captured
    # (non-TTY) output behind the warnings summary, leaving us nothing to parse.
    # The default reporter reliably prints the summary line last. -p no:warnings
    # silences the deprecation chatter so the summary is the genuine tail.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(TESTS_DIR),
         "-p", "no:cacheprovider", "-p", "no:warnings"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    # Parse stdout (pytest's own summary); stderr can carry shutdown-thread log
    # noise that must not shadow the verdict line.
    out = proc.stdout or ""

    def _num(pattern: str) -> int:
        m = re.search(pattern, out)
        return int(m.group(1)) if m else 0

    passed = _num(r"(\d+)\s+passed")
    failed = _num(r"(\d+)\s+failed")
    errored = _num(r"(\d+)\s+error")

    # The canonical one-line verdict pytest prints last, e.g.
    # "38 passed, 3 warnings in 29.71s".
    summary = ""
    for line in reversed(out.splitlines()):
        if re.search(r"\d+\s+(passed|failed|error)", line):
            summary = line.strip().strip("= ").strip()
            break
    if not summary:
        summary = f"pytest exited with code {proc.returncode} (no summary parsed)"

    ok = proc.returncode == 0 and failed == 0 and errored == 0
    print(f"  -> {summary}")

    return {
        "ok": ok,
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "summary": summary,
        "returncode": proc.returncode,
        "raw_tail": "\n".join(out.splitlines()[-40:]),
    }


# --------------------------------------------------------------------------- #
# Step 2 — render the PDF.
# --------------------------------------------------------------------------- #
def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("SecTitle", parent=ss["Title"],
                          textColor=NAVY, fontSize=20, spaceAfter=2))
    ss.add(ParagraphStyle("SecSub", parent=ss["Normal"],
                          textColor=INK, fontSize=10, leading=14))
    ss.add(ParagraphStyle("SecH2", parent=ss["Heading2"],
                          textColor=NAVY, fontSize=13, spaceBefore=14,
                          spaceAfter=4))
    ss.add(ParagraphStyle("SecBody", parent=ss["Normal"],
                          fontSize=9.5, leading=13.5, textColor=colors.HexColor("#1b2436")))
    ss.add(ParagraphStyle("SecBullet", parent=ss["Normal"],
                          fontSize=9.5, leading=13))
    ss.add(ParagraphStyle("SecCellHdr", parent=ss["Normal"], fontSize=8.5,
                          textColor=colors.white, fontName="Helvetica-Bold"))
    ss.add(ParagraphStyle("SecCell", parent=ss["Normal"], fontSize=8, leading=10.5))
    ss.add(ParagraphStyle("SecFinding", parent=ss["Normal"], fontSize=9,
                          leading=12.5))
    ss.add(ParagraphStyle("SecVerdict", parent=ss["Normal"], fontSize=11,
                          leading=15, textColor=NAVY))
    return ss


_OWASP_ROWS = [
    ("A01 Broken Access Control",
     "Role hierarchy + require_role; admin-only system/lockdown/export; per-case "
     "access; staff-only health payload; exact /api/admin lockdown allowlist."),
    ("A02 Cryptographic Failures",
     "bcrypt password hashing; HS256 JWT with asserted-secure secret; HSTS on "
     "HTTPS; expiring urlsafe reset tokens."),
    ("A03 Injection",
     "Parameterized SQL throughout; prompt-injection treated as injection — "
     "sanitise + untrusted-fence + output validation; upload magic sniffing."),
    ("A04 Insecure Design",
     "Fail-soft optional features; emergency lockdown kill-switch; brute-force "
     "lockout; export size guards; one-message-per-case citizen cap."),
    ("A05 Security Misconfiguration",
     "Hardening headers + tight CSP on every response (outermost layer); "
     "explicit CORS; no stack-trace leakage."),
    ("A06 Vulnerable Components",
     "Pinned deps; stdlib-first security paths. Recommendation: pip-audit / "
     "Dependabot in CI (partial)."),
    ("A07 Auth Failures",
     "Race-safe brute-force lockout; token_version revocation (logout-all, "
     "pw change/reset, role change, deactivation); enumeration-safe forgot-pw."),
    ("A08 Data Integrity Failures",
     "Magic-number + size-capped uploads; WAL-safe online DB backup; Arbiter "
     "never invents law (citation-validated, grounded fallback)."),
    ("A09 Logging & Monitoring",
     "Central audit trail incl. failed exports; request/error metrics; "
     "/admin/security-events review feed."),
    ("A10 SSRF",
     "assert_public_url blocks private/loopback/metadata/multicast/reserved; "
     "scheme whitelist; applied to caller stream URLs."),
]

_FINDINGS = [
    ("F-01 Lockdown path-prefix bypass — unintended route allowlist",
     "Lexical startswith('/api/admin') also matched siblings (/api/admins). "
     "Fixed: exact /api/admin or /api/admin/ subtree only."),
    ("F-02 JWT decode error in lockdown treated as non-admin (fail-closed)",
     "Confirmed the lockdown admin check fails closed — any decode/role error "
     "is treated as non-admin, never admin."),
    ("F-03 SSRF bypass — stream URL resolution to private addresses",
     "Stream URLs could resolve to internal/metadata hosts. Fixed: "
     "assert_public_url checks every resolved address + scheme."),
    ("F-04 Change-password did not revoke existing sessions",
     "Old/leaked tokens stayed valid after a password change. Fixed: bump "
     "token_version in the same update, like reset_password."),
    ("F-05 Register inconsistently passed token_version to create_token",
     "Token minted without an explicit tv. Fixed: pass token_version=0 so "
     "minting stays consistent with revocation state."),
    ("F-06 Timing-based user enumeration in forgot-password",
     "Extra work only when the account existed leaked existence via latency. "
     "Fixed: always 200, email deferred to a background task."),
    ("F-07 No mechanism to deactivate users through the API",
     "No supported account cut-off. Fixed: admin PATCH active=false bumps "
     "token_version; inactive users rejected at auth."),
    ("F-08 Login attempt counting vulnerable to race conditions",
     "Concurrent failures could overshoot the lockout. Fixed: BEGIN IMMEDIATE "
     "makes count-then-insert atomic per email."),
    ("F-09 validate_output() bypass via composite citations (e.g. 499/500)",
     "A disallowed section could ride alongside an allowed one in one clause. "
     "Fixed: capture the whole clause, check every token."),
    ("F-10 Information leak in /admin/system — model-availability disclosure",
     "Model/host telemetry leaked to non-admins. Fixed: admin-only system "
     "console; health full payload officer+ only."),
    ("F-11 Prompt-injection guard didn't validate output vs injected fences",
     "Output echoing UNTRUSTED_/END_ scaffolding slipped through. Fixed: "
     "validate_output rejects fence-leak patterns too."),
    ("F-12 Lockdown JWT decoding did not use try/except",
     "A decode exception could surface as a 500 in the hot path. Fixed: decode "
     "fully wrapped in try/except returning False."),
    ("F-13 Export endpoints did not enforce export-level rate limiting",
     "/admin/export/* shared the generous default budget. Fixed: dedicated "
     "'export' rate-limit class on the tight upload cap."),
    ("F-14 Missing audit entries for failed exports / rate-limit hits",
     "A failed export left no audit trace. Fixed: _audit_export_failed records "
     "every failure so the trail has no blind spot."),
]


def _verdict_table(result: dict, styles) -> Table:
    badge = "ALL TESTS PASSED" if result["ok"] else "ATTENTION — SEE SUMMARY"
    badge_color = colors.HexColor("#1f7a4d") if result["ok"] else GOLD_DARK
    rows = [
        [Paragraph("Suite verdict", styles["SecCellHdr"]),
         Paragraph(badge, ParagraphStyle("v", parent=styles["SecVerdict"],
                                         textColor=colors.white,
                                         fontName="Helvetica-Bold"))],
        [Paragraph("pytest summary", styles["SecCellHdr"]),
         Paragraph(result["summary"], styles["SecCell"])],
        [Paragraph("Passed / Failed / Errored", styles["SecCellHdr"]),
         Paragraph(f"{result['passed']} / {result['failed']} / {result['errored']}",
                   styles["SecCell"])],
        [Paragraph("Generated", styles["SecCellHdr"]),
         Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), styles["SecCell"])],
    ]
    t = Table(rows, colWidths=[5.0 * cm, 11.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), NAVY),
        ("BACKGROUND", (1, 0), (1, 0), badge_color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8cfde")),
    ]))
    return t


def _matrix_table(styles) -> Table:
    header = [Paragraph("OWASP Top 10 (2021)", styles["SecCellHdr"]),
              Paragraph("Implemented controls in this build", styles["SecCellHdr"])]
    data = [header]
    for risk, ctrl in _OWASP_ROWS:
        data.append([Paragraph(f"<b>{risk}</b>", styles["SecCell"]),
                     Paragraph(ctrl, styles["SecCell"])])
    t = Table(data, colWidths=[4.6 * cm, 11.9 * cm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7dce6")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, GOLD),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f3f5fa")))
    t.setStyle(TableStyle(style))
    return t


def _findings_table(styles) -> Table:
    header = [Paragraph("Finding (confirmed &amp; fixed)", styles["SecCellHdr"]),
              Paragraph("Resolution", styles["SecCellHdr"])]
    data = [header]
    for title, fix in _FINDINGS:
        data.append([Paragraph(f"<b>{title}</b>", styles["SecCell"]),
                     Paragraph(fix, styles["SecCell"])])
    t = Table(data, colWidths=[7.6 * cm, 8.9 * cm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7dce6")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, GOLD),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f3f5fa")))
    t.setStyle(TableStyle(style))
    return t


def _bullets(items: list[str], styles) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(t, styles["SecBullet"]), leftIndent=10) for t in items],
        bulletType="bullet", bulletColor=GOLD_DARK, start="•", leftIndent=12,
    )


def _on_page(canvas, doc) -> None:
    _brand_header(canvas, doc)
    _brand_footer(canvas, doc)


def build_pdf(result: dict) -> Path:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    doc = SimpleDocTemplate(
        str(PDF_PATH), pagesize=A4,
        topMargin=_BAND_H + 20, bottomMargin=1.9 * cm,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        title="CityShield · VisionScan — Security Testing Report",
        author="CityShield Cyber Crime Branch, Ahmedabad",
    )

    s = []
    s.append(Paragraph("Security Testing Report", styles["SecTitle"]))
    s.append(Paragraph(
        "CityShield · VisionScan — Unified AI Policing platform "
        "(CCTV intelligence + Arbiter legal-AI) · Cyber Crime Branch, Ahmedabad",
        styles["SecSub"]))
    s.append(Spacer(1, 4))
    s.append(HRFlowable(width="100%", thickness=1, color=GOLD,
                        spaceBefore=2, spaceAfter=10))

    # Live verdict block.
    s.append(Paragraph("Automated regression verdict", styles["SecH2"]))
    s.append(Paragraph(
        "The block below is produced live: <font name='Helvetica-Bold'>"
        "gen_security_report.py</font> runs the suite under "
        "<font name='Courier'>backend/tests/</font> in a subprocess against a "
        "throwaway database and records pytest's own summary before this page is "
        "rendered. It is the machine-checked state of the build at generation "
        "time, not a transcribed claim.", styles["SecBody"]))
    s.append(Spacer(1, 6))
    s.append(_verdict_table(result, styles))
    s.append(Spacer(1, 6))
    s.append(Paragraph(
        "<b>Self-assessment disclaimer.</b> This is an internal review by the "
        "team that built CityShield — not an independent third-party penetration "
        "test or formal audit. It documents the controls implemented and the "
        "threats designed against. Commission an external assessment before any "
        "live deployment handling real citizen data or active investigations; "
        "absence of a finding here is not proof of absence of a vulnerability.",
        styles["SecBody"]))

    # OWASP matrix.
    s.append(Paragraph("OWASP Top 10 (2021) coverage", styles["SecH2"]))
    s.append(Paragraph(
        "Each risk is mapped to the concrete controls implemented in this "
        "codebase. The companion <font name='Courier'>SECURITY_TESTING_REPORT.md"
        "</font> additionally names the exact regression test guarding each row.",
        styles["SecBody"]))
    s.append(Spacer(1, 6))
    s.append(_matrix_table(styles))

    # AI threat model.
    s.append(Paragraph(
        "Threat model — “no AI should attack us, and ours must not be turned”",
        styles["SecH2"]))
    s.append(Paragraph(
        "The AI surface is the most novel risk: it ingests fully "
        "attacker-controlled text (FIR narratives, citizen questions) and "
        "server-fetched URLs. CityShield defends in three lines:",
        styles["SecBody"]))
    s.append(Spacer(1, 4))
    s.append(_bullets([
        "<b>Prompt injection.</b> User text is sanitised (fence-token + "
        "control-char strip, length cap), embedded as data inside "
        "&lt;&lt;&lt;UNTRUSTED_*&gt;&gt;&gt; fences, and the hardened system "
        "instruction forbids prompt disclosure, role changes, and citing "
        "anything outside the provided sections.",
        "<b>Output validation, not just input.</b> validate_output rejects a "
        "generation that cites a section outside the RAG-retrieved set (each "
        "token in composite clauses like “499/500” is checked), leaks a "
        "role/jailbreak marker, or echoes the fence scaffolding — then the "
        "service degrades to the grounded offline template. The platform "
        "degrades to safe, never to fabricated law.",
        "<b>SSRF on untrusted URLs.</b> assert_public_url blocks private / "
        "loopback / cloud-metadata (169.254.169.254) / multicast / reserved "
        "hosts across every resolved address, with a scheme whitelist.",
        "<b>Untrusted media.</b> Uploads are sniffed by container magic number "
        "and extension before any decoder runs, and streamed under a hard size "
        "cap.",
        "<b>Recon starvation.</b> Model availability and host telemetry are "
        "withheld from anonymous / low-privilege callers (health + "
        "/admin/system tightened).",
    ], styles))

    # Findings.
    s.append(Paragraph("Confirmed-and-fixed findings", styles["SecH2"]))
    s.append(Paragraph(
        "Fourteen findings were raised during the Phase 3 review, confirmed, and "
        "closed. Each is now pinned by a regression test (named in the Markdown "
        "companion).", styles["SecBody"]))
    s.append(Spacer(1, 6))
    s.append(_findings_table(styles))

    # Closing.
    s.append(Paragraph("Defence-in-depth & residual risk", styles["SecH2"]))
    s.append(_bullets([
        "<b>Middleware order:</b> SecurityHeaders → Metrics → RateLimit "
        "→ Lockdown → route, so hardening headers land even on 429/423 "
        "short-circuits and a dedicated 'export' rate-limit class throttles bulk "
        "exfiltration.",
        "<b>Residual:</b> DNS-rebinding TOCTOU on the resolve-time SSRF guard "
        "(accepted, operator-run); dependency-CVE scanning recommended in CI; "
        "JWT revocation is per-user, not per-token.",
    ], styles))
    s.append(Spacer(1, 8))
    s.append(HRFlowable(width="100%", thickness=0.8, color=GOLD,
                        spaceBefore=2, spaceAfter=6))
    s.append(Paragraph(
        "Reproduce: <font name='Courier'>$env:PYTHONPATH='.'; "
        ".\\.venv\\Scripts\\python.exe -m pytest tests -q</font> &nbsp;|&nbsp; "
        "Regenerate this PDF: <font name='Courier'>.\\.venv\\Scripts\\python.exe "
        "scripts\\gen_security_report.py</font>",
        styles["SecBody"]))

    doc.build(s, onFirstPage=_on_page, onLaterPages=_on_page)
    return PDF_PATH


def main() -> int:
    print("CityShield · VisionScan — security report generator")
    print("=" * 56)
    result = run_pytest()
    pdf = build_pdf(result)
    size = pdf.stat().st_size if pdf.exists() else 0
    print("-" * 56)
    print(f"PDF written: {pdf}  ({size:,} bytes)")
    if not result["ok"]:
        print("WARNING: the suite did not pass cleanly; PDF reflects the "
              "actual verdict.")
        print(result["raw_tail"])
    # Exit non-zero only if the PDF failed to materialise; a test failure is
    # documented in the PDF, not a generator error.
    return 0 if size > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
