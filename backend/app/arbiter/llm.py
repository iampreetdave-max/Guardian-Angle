"""LLM layer for Arbiter — Gemini when available, graceful offline fallback.

If a Gemini API key is configured, generation is delegated to Gemini for fluent,
multilingual output. If not (offline / field deployment), `generate()` returns
None and callers fall back to deterministic, citation-grounded templates — so
Arbiter is always functional, just more polished when online.
"""
from __future__ import annotations

import logging
import os
import threading

from ..config import get_settings

log = logging.getLogger("visionscan.arbiter.llm")

_lock = threading.Lock()
_model = None
_init_done = False

LANGUAGES = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}


def _resolve_key() -> str:
    s = get_settings()
    return s.gemini_api_key or os.getenv("GEMINI_API_KEY", "")


def is_online() -> bool:
    """True if Gemini generation is available (a key is configured)."""
    return bool(_resolve_key())


def _ensure_model():
    global _model, _init_done
    if _init_done:
        return _model
    with _lock:
        if _init_done:
            return _model
        _init_done = True
        key = _resolve_key()
        if not key:
            return None
        try:
            import google.generativeai as genai

            genai.configure(api_key=key)
            _model = genai.GenerativeModel(get_settings().gemini_model)
            log.info("Arbiter: Gemini model ready (%s)", get_settings().gemini_model)
        except Exception as e:  # pragma: no cover
            log.warning("Arbiter: Gemini init failed, using offline fallback: %s", e)
            _model = None
    return _model


def generate(prompt: str, language: str = "en") -> str | None:
    """Generate text with Gemini, or return None if unavailable (offline)."""
    model = _ensure_model()
    if model is None:
        return None
    lang = LANGUAGES.get(language, "English")
    sys = (
        "You are Arbiter, a legal assistant for Indian police and citizens. "
        "Be precise, cite only the provided sections, never invent law, and add "
        "a short disclaimer that this is AI-generated and must be verified by an "
        f"officer/lawyer. Respond in {lang}."
    )
    try:
        resp = model.generate_content(f"{sys}\n\n{prompt}")
        return (resp.text or "").strip() or None
    except Exception as e:  # pragma: no cover
        log.warning("Arbiter: Gemini generation failed: %s", e)
        return None
