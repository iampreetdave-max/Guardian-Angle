"""Devanagari and Gujarati text in generated PDFs.

ReportLab's built-in Helvetica has no Indic glyphs, so Hindi or Gujarati typed
into a case title came out of the exporter as blank boxes. The platform speaks
three languages everywhere else, so its evidence documents have to as well.

The Noto Indic fonts bundled here carry almost no Latin (Devanagari has 5 Latin
glyphs, Gujarati none), so a document cannot simply be switched wholesale to one
of them — an English label would break. Instead `rich()` splits a string into
per-script runs and wraps each in the font that can actually draw it, which
handles the common real case of one field mixing both ("FIR क्रमांक 123").

Everything degrades to Helvetica if the font files are missing, so an export
never fails because of a font.
"""
from __future__ import annotations

import logging
from pathlib import Path
from xml.sax.saxutils import escape

log = logging.getLogger("visionscan.fonts")

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

LATIN = "latin"
DEVA = "deva"
GUJR = "gujr"

_FILES = {
    DEVA: ("NotoSansDevanagari-Regular.ttf", "NotoSansDevanagari-Bold.ttf"),
    GUJR: ("NotoSansGujarati-Regular.ttf", "NotoSansGujarati-Bold.ttf"),
}
_FACES = {
    DEVA: ("NotoSansDevanagari", "NotoSansDevanagari-Bold"),
    GUJR: ("NotoSansGujarati", "NotoSansGujarati-Bold"),
}

_registered: dict[str, tuple[str, str]] | None = None


def register_indic_fonts() -> dict[str, tuple[str, str]]:
    """Register the bundled Indic fonts with ReportLab. Idempotent and
    fail-soft: a missing or unreadable file just means that script falls back to
    Helvetica (and renders as boxes) rather than breaking PDF generation."""
    global _registered
    if _registered is not None:
        return _registered

    available: dict[str, tuple[str, str]] = {}
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except Exception:  # pragma: no cover - reportlab always present in practice
        log.warning("reportlab unavailable; Indic PDF text will not render")
        _registered = {}
        return _registered

    for script, (reg_file, bold_file) in _FILES.items():
        reg_name, bold_name = _FACES[script]
        try:
            reg_path, bold_path = FONT_DIR / reg_file, FONT_DIR / bold_file
            if not reg_path.exists():
                log.warning("Indic font missing: %s", reg_path)
                continue
            pdfmetrics.registerFont(TTFont(reg_name, str(reg_path)))
            # Bold is optional — fall back to the regular face if absent.
            if bold_path.exists():
                pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))
            else:
                bold_name = reg_name
            available[script] = (reg_name, bold_name)
        except Exception:
            log.warning("could not register %s font", script, exc_info=True)

    _registered = available
    if available:
        log.info("Indic PDF fonts registered: %s", ", ".join(sorted(available)))
    return _registered


def script_of(ch: str) -> str:
    o = ord(ch)
    if 0x0900 <= o <= 0x097F:
        return DEVA
    if 0x0A80 <= o <= 0x0AFF:
        return GUJR
    return LATIN


def has_indic(text: str) -> bool:
    return any(script_of(c) != LATIN for c in str(text or ""))


def rich(text, bold: bool = False, base: str | None = None) -> str:
    """XML-escape `text` for a ReportLab Paragraph, wrapping Indic runs in a font
    that can draw them.

    Latin runs are left unwrapped so they inherit the paragraph style — which
    keeps existing documents byte-identical when there is no Indic text at all.
    """
    s = str(text or "")
    if not s:
        return ""
    available = register_indic_fonts()
    if not available or not has_indic(s):
        return escape(s)

    out: list[str] = []
    run: list[str] = []
    run_script = script_of(s[0])

    def flush() -> None:
        if not run:
            return
        chunk = escape("".join(run))
        face = available.get(run_script)
        if run_script != LATIN and face:
            out.append(f'<font name="{face[1] if bold else face[0]}">{chunk}</font>')
        else:
            out.append(chunk)
        run.clear()

    for ch in s:
        sc = script_of(ch)
        # Only whitespace inherits the current run. Punctuation must NOT: the
        # bundled Gujarati face has zero Latin glyphs, so a comma left inside a
        # Gujarati run resolves to .notdef and the character silently disappears
        # from the PDF (it extracts as ). Digits are Latin for the same
        # reason.
        if sc != run_script and not ch.isspace():
            flush()
            run_script = sc
        run.append(ch)
    flush()
    return "".join(out)


def font_for(text, bold: bool = False, default: str = "Helvetica") -> str:
    """Single font name able to draw `text` — for canvas.drawString and table
    styles, which take one font rather than inline markup."""
    available = register_indic_fonts()
    for ch in str(text or ""):
        sc = script_of(ch)
        if sc != LATIN and sc in available:
            return available[sc][1 if bold else 0]
    return f"{default}-Bold" if bold and not default.endswith("-Bold") else default
