"""Lightweight document categorisation + metadata extraction.

Live feed items (RSS) arrive as a title + summary with no structured doc_type or
department. These keyword/rule heuristics classify them into the same taxonomy as
the bundled corpus and pull out coarse metadata, so live and bundled documents
are searchable and filterable uniformly. No ML dependency — fast and offline.
"""
from __future__ import annotations

import re

# Ordered: the first category whose cues match wins. More specific terms first.
_TYPE_CUES: list[tuple[str, tuple[str, ...]]] = [
    ("Judgment", ("judgment", "judgement", "vs ", "v. ", "petitioner", "respondent",
                  "bench", "writ petition", "honble", "hon'ble court")),
    ("GR", ("government resolution", "ઠરાવ", "resolution no", "g.r.", " gr ")),
    ("Circular", ("circular", "office memorandum", "o.m.", "guidelines on")),
    ("Notification", ("notification", "notified", "gazette", "s.o.", "g.s.r.",
                      "in exercise of the powers")),
    ("Rule", ("rules,", " rules ", "regulations", "amendment rules")),
    ("Act", ("act,", " act ", "bill,", "sanhita", "adhiniyam")),
    ("Scheme", ("yojana", "scheme", "mission", "abhiyan", "nidhi", "programme")),
]

_REGION_CUES = ("gujarat", "ahmedabad", "gandhinagar", "surat", "vadodara",
                "rajkot", "ગુજરાત")

# crude department guess from common ministry/department keywords
_DEPT_CUES: list[tuple[str, tuple[str, ...]]] = [
    ("Ministry of Home Affairs", ("home affairs", "police", "cyber", "security")),
    ("Ministry of Finance", ("finance", "tax", "gst", "rbi", "bank", "pension", "subsidy")),
    ("Ministry of Health & Family Welfare", ("health", "hospital", "medical", "ayushman")),
    ("Ministry of Education", ("education", "school", "student", "university", "scholarship")),
    ("Ministry of Agriculture & Farmers Welfare", ("farmer", "agriculture", "crop", "kisan")),
    ("Ministry of Electronics & IT", ("information technology", "digital", "data", "meity", "cert-in")),
    ("Ministry of Law & Justice", ("court", "judicial", "law", "justice", "advocate")),
]


def classify(title: str, text: str = "") -> str:
    blob = f" {title} {text} ".lower()
    for doc_type, cues in _TYPE_CUES:
        if any(c in blob for c in cues):
            return doc_type
    return "Notification"


def guess_region(title: str, text: str = "", default: str = "central") -> str:
    blob = f"{title} {text}".lower()
    return "gujarat" if any(c in blob for c in _REGION_CUES) else default


def guess_department(title: str, text: str = "", default: str = "") -> str:
    blob = f"{title} {text}".lower()
    for dept, cues in _DEPT_CUES:
        if any(c in blob for c in cues):
            return dept
    return default


_STOP = {
    "the", "and", "for", "with", "from", "this", "that", "shall", "will", "under",
    "into", "have", "has", "are", "was", "were", "been", "being", "any", "all",
    "such", "may", "must", "not", "their", "which", "other", "than", "more",
    "india", "indian", "government", "department", "ministry", "act", "rules",
}


def extract_keywords(title: str, text: str = "", limit: int = 8) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", f"{title} {text}".lower())
    seen: dict[str, int] = {}
    for w in words:
        if w in _STOP:
            continue
        seen[w] = seen.get(w, 0) + 1
    ranked = sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in ranked[:limit]]
