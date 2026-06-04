"""Test for citation bypass vulnerability in arbiter guards."""
import sys
import re

# Inline the functions to analyze
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
    print(f"[DEBUG] Allowed tokens extracted: {allowed}")
    
    for m in _CITED_SECTION_RE.finditer(text):
        token = m.group(1).lower()
        print(f"[DEBUG] Found citation: {m.group(1)} -> token: {token}")
        if token not in allowed:
            print(f"[DEBUG] Token {token} NOT in allowed set!")
            return False
    
    return True


# Test 1: Normal case - should pass
print("TEST 1: Normal case (should PASS)")
allowed = {"IPC Section 420", "IT Act 2000 Section 66C"}
text = "The accused may be charged under Section 420 and Section 66C."
result = validate_output(text, allowed)
print(f"Result: {result}\n")

# Test 2: Out-of-range section - should fail
print("TEST 2: Out-of-range section (should FAIL)")
allowed = {"IPC Section 420"}
text = "This falls under Section 999 of the code."
result = validate_output(text, allowed)
print(f"Result: {result}\n")

# Test 3: Case sensitivity bypass attempt
print("TEST 3: Case sensitivity bypass (UPPERCASE ACT NAME)")
allowed = {"IPC Section 66C"}  # lowercase
text = "This falls under Section 66C."  # uppercase C preserved in extraction
result = validate_output(text, allowed)
print(f"Result: {result}\n")

# Test 4: Malformed section in allowed set
print("TEST 4: Malformed section in allowed set (66-C with hyphen)")
allowed = {"IPC Section 66-C"}  # hyphen instead of bare section
text = "Section 66C mentioned here"
tokens = _allowed_section_tokens(allowed)
print(f"Tokens from '66-C': {tokens}")
result = validate_output(text, allowed)
print(f"Result: {result}\n")

# Test 5: Section 66C vs 66 extraction issue
print("TEST 5: Detailed token extraction - 66C")
test_strings = [
    "IPC Section 66C",
    "IPC Section 66-C", 
    "IPC Section 66 C",
    "Section 66C",
]
for s in test_strings:
    tokens = _allowed_section_tokens({s})
    print(f"  '{s}' -> tokens: {tokens}")

