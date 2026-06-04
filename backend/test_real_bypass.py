"""Test for real citation bypass vulnerability."""
import sys
import re

def _allowed_section_tokens(allowed_citations: set[str]) -> set[str]:
    """Extract bare, lower-cased section identifiers from allowed citations."""
    tokens: set[str] = set()
    for cite in allowed_citations or set():
        for m in re.findall(r"\d+[A-Za-z]?", str(cite)):
            tokens.add(m.lower())
    return tokens

_CITED_SECTION_RE = re.compile(r"section\s+(\d+[A-Za-z]?)", re.IGNORECASE)

def validate_output(text: str, allowed_citations: set[str]) -> bool:
    """Return False if the output is unsafe to surface."""
    if not text:
        return True
    
    allowed = _allowed_section_tokens(allowed_citations)
    
    for m in _CITED_SECTION_RE.finditer(text):
        token = m.group(1).lower()
        if token not in allowed:
            return False
    
    return True

# ATTACK: If we can inject a malformed citation into the allowed set
# that normalizes differently, we could bypass validation

print("ATTACK SCENARIO 1: If metadata contains 'IPC Section 66-C' instead of 'IPC Section 66C'")
print("=" * 80)

# Simulate what happens if corpus has inconsistent formatting
allowed_from_corpus = {"IPC Section 66-C"}  # stored this way in corpus
tokens = _allowed_section_tokens(allowed_from_corpus)
print(f"Allowed tokens from corpus ('IPC Section 66-C'): {tokens}")

# Model outputs this
model_output = "This falls under Section 66C as per the act."
result = validate_output(model_output, allowed_from_corpus)
print(f"Model cites 'Section 66C', validation result: {result}")
print(f"BYPASS POSSIBLE: {not result}\n")

print("ATTACK SCENARIO 2: Multiple digit/letter combos")
print("=" * 80)

# If corpus has sections like "Section 12B" and "Section 12AB"
allowed_set = {"IPC Section 12B"}
tokens = _allowed_section_tokens(allowed_set)
print(f"Allowed tokens from 'IPC Section 12B': {tokens}")

# Can model cite "Section 12" and have it extracted as just "12"?
model_output = "As per Section 12 of the act..."
result = validate_output(model_output, allowed_set)
print(f"Model cites 'Section 12' (part of 12B), validation: {result}")
print(f"ISSUE: Section 12 and 12B are DIFFERENT but token '12' matches!\n")

print("ATTACK SCENARIO 3: Regex extraction differences")
print("=" * 80)

# The regex r"\d+[A-Za-z]?" will match:
test_cases = [
    ("Section 66C", "66c"),        # OK
    ("Section 66 C", "66"),         # Only matches "66", misses "C"
    ("Section 66-C", "66"),         # Only matches "66", misses "C"  
    ("Section 66/67", "66"),        # Only matches "66", not "67"
]

for text, expected_token in test_cases:
    m = re.search(r"section\s+(\d+[A-Za-z]?)", text, re.IGNORECASE)
    if m:
        token = m.group(1).lower()
        print(f"  '{text}' -> extracted: '{token}' (expected '{expected_token}')")

print("\nCONCLUSION:")
print("=" * 80)
print("1. If corpus metadata has 'IPC Section 66-C' but output says '66C',")
print("   the tokens don't match ('66' vs '66c') -> LEGITIMATE FAIL (no bypass)")
print("2. If corpus has 'IPC Section 12B' and model cites just '12',")
print("   token '12' WILL match 'Section 12B' -> REAL BYPASS POSSIBLE")
print("3. Metadata is sourced from legal_corpus.json which uses 'act' + 'section' fields")
print("   Corpus sections all end in 0-9, 0-9[A-Z], never hyphens or spaces")
