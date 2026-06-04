"""Adversarial lockdown middleware security test.

Tests whether the lockdown middleware correctly enforces path restrictions
and whether there are any bypass vectors via path manipulation.

Run from backend/:  python scripts/lockdown_security_test.py
"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ["VISIONSCAN_DATA_DIR"] = tempfile.mkdtemp(prefix="visionscan_lockdown_")
os.environ["VISIONSCAN_ENABLE_ANOMALY"] = "false"

import sys
from fastapi.testclient import TestClient
from app.main import app
from app.security_mw import set_lockdown, is_lockdown

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def login(client: TestClient, email: str, password: str) -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['token']}"}


def main() -> None:
    print("Lockdown Middleware Security Test")
    print("=" * 60)
    
    with TestClient(app) as client:
        # Get admin and officer tokens before enabling lockdown
        admin = login(client, "admin@city.gov", "admin123")
        officer = login(client, "officer@city.gov", "officer123")
        
        # Enable lockdown
        set_lockdown(True)
        check("lockdown state is enabled", is_lockdown())
        
        print("\n--- Testing ALLOWED paths during lockdown ---")
        
        # Test: /api/health should be allowed (exact match)
        r = client.get("/api/health")
        check("GET /api/health allowed (no auth)", r.status_code == 200, str(r.status_code))
        
        # Test: /api/auth/login should be allowed (exact match)
        r = client.post("/api/auth/login", json={"email": "officer@city.gov", "password": "officer123"})
        check("POST /api/auth/login allowed", r.status_code == 200, str(r.status_code))
        
        # Test: /api/admin paths should be allowed for admin (startswith check)
        r = client.get("/api/admin/system", headers=admin)
        check("GET /api/admin/system allowed for admin", r.status_code == 200, str(r.status_code))
        
        # Test: Non-/api paths should be allowed (React bundle, static assets)
        r = client.get("/")
        not_locked = r.status_code != 423
        check("GET / (non-/api) not locked", not_locked, f"status={r.status_code}")
        
        print("\n--- Testing BLOCKED paths (non-whitelisted API calls) ---")
        
        # These should all return 423 Locked
        r = client.get("/api/cases", headers=officer)
        check("GET /api/cases blocked with 423", r.status_code == 423, str(r.status_code))
        
        r = client.get("/api/complaints", headers=officer)
        check("GET /api/complaints blocked with 423", r.status_code == 423, str(r.status_code))
        
        r = client.post("/api/complaints", headers=officer, json={"title": "test"})
        check("POST /api/complaints blocked with 423", r.status_code == 423, str(r.status_code))
        
        print("\n--- Testing PATH VARIANTS & POTENTIAL BYPASSES ---")
        
        # ATTACK VECTOR 1: Case sensitivity - /api/Health should be BLOCKED
        # Code uses == which is case-sensitive, so this SHOULD be blocked
        r = client.get("/api/Health")
        check("GET /api/Health (case variant) blocked", r.status_code == 423, f"got {r.status_code}")
        
        # ATTACK VECTOR 2: /api/admin with trailing slash
        r = client.get("/api/admin/", headers=admin)
        check("GET /api/admin/ allowed (admin path)", r.status_code == 200, f"got {r.status_code}")
        
        # ATTACK VECTOR 3: /api/admin_ prefix shouldn't match /api/admin*
        # This tests if startswith("/api/admin") is too permissive
        r = client.get("/api/admin_test", headers=admin)
        status = r.status_code
        check("GET /api/admin_test blocked (doesn't match /api/admin*)", status == 423, f"got {status}")
        
        # ATTACK VECTOR 4: /api/admi (partial match) should be blocked
        r = client.get("/api/admi", headers=admin)
        status = r.status_code
        check("GET /api/admi blocked", status == 423, f"got {status}")
        
        # ATTACK VECTOR 5: Ensure non-admin can't access /api/admin/* despite lockdown rule
        r = client.get("/api/admin/system", headers=officer)
        check("GET /api/admin/system blocks non-admin (403, not bypassed by lockdown)", r.status_code == 403, f"got {r.status_code}")
        
        print("\n--- Testing JWT VALIDATION during lockdown ---")
        
        # Test that an admin JWT allows everything
        r = client.get("/api/cases", headers=admin)
        check("Admin JWT allows /api/cases during lockdown", r.status_code == 200, str(r.status_code))
        
        # Test that an invalid JWT doesn't bypass lockdown
        r = client.get("/api/cases", headers={"Authorization": "Bearer invalid.token.here"})
        check("Invalid JWT doesn't bypass lockdown", r.status_code == 423, str(r.status_code))
        
        # Test that missing JWT doesn't bypass lockdown
        r = client.get("/api/cases")
        check("No JWT doesn't bypass lockdown", r.status_code == 423, str(r.status_code))
        
        # Test Bearer token format issues - lowercase "bearer"
        token = admin['Authorization'].split()[-1]
        r = client.get("/api/cases", headers={"authorization": f"bearer {token}"})
        check("Lowercase 'bearer' prefix works", r.status_code == 200, str(r.status_code))
        
        print("\n--- Testing LOGOUT endpoint during lockdown ---")
        
        # /api/auth/logout should be handled - check if it's accessible
        # (It's not explicitly whitelisted, so it should be blocked)
        r = client.post("/api/auth/logout", headers=officer)
        check("POST /api/auth/logout blocked", r.status_code == 423, str(r.status_code))
        
        # But logout-all is a newer endpoint - check if it exists
        r = client.post("/api/auth/logout-all", headers=officer)
        if r.status_code != 404:
            check("POST /api/auth/logout-all blocked during lockdown", r.status_code == 423, str(r.status_code))
        
        # Disable lockdown for cleanup
        set_lockdown(False)
        check("lockdown state is disabled after tests", not is_lockdown())


if __name__ == "__main__":
    main()
    
    print("\n" + "=" * 60)
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} FAILURES:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("RESULT: All lockdown security tests passed!")
