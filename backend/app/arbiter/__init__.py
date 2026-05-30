"""Arbiter — legal intelligence module for CityShield.

A simplified, police-focused legal assistant: RAG retrieval over a seed IPC /
IT Act 2000 / CrPC corpus (fully offline via ChromaDB) plus optional Gemini
generation (when an API key is configured) for polished FIR drafts and answers.
Falls back to deterministic, citation-grounded templates when offline / keyless,
so it always works in the field.
"""
