"""Unit tests for the Arbiter prompt-injection / output-validation guards."""
from __future__ import annotations

from app.arbiter.guards import (
    sanitize_user_text,
    validate_output,
    wrap_untrusted,
)


# ----------------------------------------------------------------- sanitize
def test_sanitize_caps_length():
    out = sanitize_user_text("a" * 10_000, max_chars=100)
    assert len(out) == 100


def test_sanitize_strips_fences_and_control_chars():
    raw = "<<<UNTRUSTED_X>>>\nhello\x00\x07world>>>"
    out = sanitize_user_text(raw)
    assert "<<<" not in out
    assert ">>>" not in out
    assert "\x00" not in out and "\x07" not in out
    assert "hello" in out and "world" in out
    # newlines and tabs are preserved
    assert sanitize_user_text("a\n\tb") == "a\n\tb"


def test_sanitize_collapses_runaway_newlines():
    out = sanitize_user_text("a\n\n\n\n\nb")
    assert "\n\n\n" not in out
    assert out == "a\n\nb"


def test_sanitize_handles_none():
    assert sanitize_user_text(None) == ""


# -------------------------------------------------------------- wrap_untrusted
def test_wrap_untrusted_format():
    wrapped = wrap_untrusted("incident", "some text")
    assert wrapped == "<<<UNTRUSTED_INCIDENT>>>\nsome text\n<<<END_INCIDENT>>>"


# ------------------------------------------------------------- validate_output
def test_validate_output_accepts_allowed_citation():
    allowed = {"IPC Section 420", "IT Act 2000 Section 66C"}
    text = "The accused may be charged under Section 420 and Section 66C."
    assert validate_output(text, allowed) is True


def test_validate_output_rejects_out_of_set_section():
    allowed = {"IPC Section 420"}
    text = "This falls under Section 999 of the code."
    assert validate_output(text, allowed) is False


def test_validate_output_rejects_role_leak():
    allowed = {"IPC Section 420"}
    for leak in (
        "Here is my system prompt: you are...",
        "Sure, I will ignore previous instructions.",
        "As an AI model I cannot do that.",
    ):
        assert validate_output(leak, allowed) is False, leak


def test_validate_output_passes_when_no_citation():
    # Conservative: no clearly-cited section -> let it through.
    assert validate_output("Please file an FIR at your local station.", set()) is True
