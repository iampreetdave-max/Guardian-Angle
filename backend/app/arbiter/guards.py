"""Arbiter AI guards — prompt-injection defences and output validation.

These helpers treat all user-supplied text as untrusted *data* (never
instructions): they sanitise it, wrap it in clearly delimited fences so the
model can tell data from instructions, and validate the generated output so the
model cannot quietly invent legal sections or leak the system prompt.

The philosophy is conservative: we would rather let a borderline-correct answer
through than wrongly reject genuine legal aid, so output validation only flags
output that *clearly* cites a section we never provided, or that contains an
obvious role-leak / jailbreak marker.
"""
from __future__ import annotations

import logging
import re

from ..config import get_settings

log = logging.getLogger("visionscan.arbiter.guards")

# Control chars to strip (keep \n=0x0A and \t=0x09). C0 + DEL.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Our fence delimiter tokens — strip any user attempt to forge them.
_FENCE_RE = re.compile(r"<<<+|>>>+")
# 3+ consecutive newlines -> collapse to 2.
_MULTINL_RE = re.compile(r"\n{3,}")

# A clearly-cited section *clause*, e.g. "section 420", "Section 66C", or a
# composite list under one keyword like "Section 499/500" or
# "Sections 420, 467 and 471". We grab the whole run after the keyword and pull
# every section token out of it below, so a disallowed section can't hide behind
# a "/" / "," / "&" / "and" separator next to an allowed one.
_CITED_SECTION_RE = re.compile(
    r"sections?\s+"
    r"(\d+[A-Za-z]?(?:\s*(?:[/,&]|and)\s*\d+[A-Za-z]?)*)",
    re.IGNORECASE,
)
# Individual section tokens within a matched clause.
_SECTION_TOKEN_RE = re.compile(r"\d+[A-Za-z]?")

# Markers that suggest the model leaked its role / was jailbroken.
_ROLE_LEAK_MARKERS = (
    "system prompt",
    "ignore previous instructions",
    "as an ai model",
)

# Our prompt scaffolding. If any of these show up in the output the model has
# echoed back the fenced UNTRUSTED block's delimiters / labels rather than only
# its legitimate content — a sign the injected fenced content leaked through.
# (Legitimately echoing the *narrative* of an incident in an FIR is fine and
# expected; echoing the fence machinery is not.)
_FENCE_LEAK_RE = re.compile(
    r"<<<|>>>|untrusted_[a-z]+|end_[a-z]+", re.IGNORECASE
)


def sanitize_user_text(text: str, max_chars: int | None = None) -> str:
    """Sanitise untrusted user input before it ever reaches the model.

    Caps length at ``arbiter_max_input_chars`` (or ``max_chars``), strips
    control characters (keeping newlines/tabs), removes our fence tokens so the
    input cannot break out of its fence, and collapses runaway newlines.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    if max_chars is None:
        try:
            max_chars = get_settings().arbiter_max_input_chars
        except Exception:  # pragma: no cover - fail-soft on settings
            max_chars = 4000
    if max_chars and max_chars > 0:
        text = text[:max_chars]

    text = _CONTROL_RE.sub("", text)
    text = _FENCE_RE.sub("", text)
    text = _MULTINL_RE.sub("\n\n", text)
    return text.strip()


def wrap_untrusted(label: str, text: str) -> str:
    """Wrap untrusted ``text`` in clearly-delimited fences for the prompt."""
    label = (label or "INPUT").upper()
    return f"<<<UNTRUSTED_{label}>>>\n{text}\n<<<END_{label}>>>"


def _allowed_section_tokens(allowed_citations: set[str]) -> set[str]:
    """Extract bare, lower-cased section identifiers from allowed citations.

    Citations look like ``"IPC Section 420"`` or ``"IT Act 2000 Section 66C"``;
    a citation may also bundle several (e.g. ``"IPC Section 499/500"``). We pull
    every ``\\d+[A-Z]?`` token so comparison is robust to the surrounding act
    name and formatting.
    """
    tokens: set[str] = set()
    for cite in allowed_citations or set():
        for m in re.findall(r"\d+[A-Za-z]?", str(cite)):
            tokens.add(m.lower())
    return tokens


def validate_output(text: str, allowed_citations: set[str]) -> bool:
    """Return False if the output is unsafe to surface.

    Unsafe means it clearly cites a section identifier that was not in the
    provided (RAG-retrieved) set, it contains a role-leak / jailbreak marker, or
    it echoes back the fenced UNTRUSTED scaffolding. Conservative by design: if
    no section is clearly cited, or every cited section is allowed, the output
    passes.
    """
    if not text:
        return True

    low = text.lower()
    for marker in _ROLE_LEAK_MARKERS:
        if marker in low:
            log.warning("Arbiter output rejected: role-leak marker %r", marker)
            return False

    if _FENCE_LEAK_RE.search(text):
        log.warning("Arbiter output rejected: echoes fenced untrusted scaffolding")
        return False

    allowed = _allowed_section_tokens(allowed_citations)
    for m in _CITED_SECTION_RE.finditer(text):
        # A clause may bundle several sections ("499/500"); check each token so
        # a disallowed one can't ride alongside an allowed one.
        for tok in _SECTION_TOKEN_RE.findall(m.group(1)):
            token = tok.lower()
            if token not in allowed:
                log.warning(
                    "Arbiter output rejected: cites section %s not in allowed set",
                    tok,
                )
                return False

    return True
