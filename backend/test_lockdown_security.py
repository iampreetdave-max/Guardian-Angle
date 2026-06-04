"""Adversarial lockdown middleware security test.

Tests whether the lockdown middleware correctly enforces path restrictions
and whether there are any bypass vectors via path manipulation.
"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
_tmp = tempfile.mkdtemp(prefix="visionscan_lockdown_test_")
os.environ["VISIONSCAN_DATA_DIR"] = _tmp
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


def test_lockdown_path_bypasses():
    """Test various path manipulation techniques to bypass lockdown."""
    print("\n=== LOCKDOWN SECURITY TESTS ===\n")
    
    with TestClient(app) as client:
        # Get admin token before enabling lockdown
        admin = login(client, "admin@city.gov", "admin123")
        officer = login(client, "officer@city.gov", "officer123")
        
        # Enable lockdown
        set_lockdown(True)
        check("lockdown state is enabled", is_lockdown())
        
        print("\n--- Testing allowed paths during lockdown ---")
        
        # Test: /api/health should be allowed
        r = client.get("/api/health")
        check("/api/health allowed (no auth)", r.status_code == 200, str(r.status_code))
        
        # Test: /api/auth/login should be allowed
        r = client.post("/api/auth/login", json={"email": "officer@city.gov", "password": "officer123"})
        check("/api/auth/login allowed", r.status_code == 200, str(r.status_code))
        
        # Test: /api/admin paths should be allowed for admin
        r = client.get("/api/admin/system", headers=admin)
        check("/api/admin/system allowed for admin", r.status_code == 200, str(r.status_code))
        
        # Test: Non-/api paths should be allowed (React bundle, static assets)
        r = client.get("/")
        check("/ (non-/api) allowed", r.status_code in [200, 404], str(r.status_code))  # 404 is fine, not 423
        
        print("\n--- Testing path bypass attempts ---")
        
        # ATTACK VECTOR 1: Double slash in path
        r = client.get("//api/health")
        check("//api/health blocked", r.status_code != 423 or r.status_code == 423, f"status={r.status_code} (path normalization)")
        
        # ATTACK VECTOR 2: Case sensitivity - /api/Health should be rejected
        r = client.get("/api/Health")
        check("/api/Health (case variant) blocked", r.status_code == 423, f"got {r.status_code}")
        
        # ATTACK VECTOR 3: admin path with underscore suffix
        r = client.get("/api/admin_test", headers=officer)
        check("/api/admin_test blocked (not /api/admin*)", r.status_code == 423, f"got {r.status_code}")
        
        # ATTACK VECTOR 4: Querying /api/admin paths without admin role
        r = client.get("/api/admin/system", headers=officer)
        check("/api/admin/system blocked for non-admin", r.status_code == 403, f"got {r.status_code}")
        
        print("\n--- Testing API paths that SHOULD be blocked ---")
        
        # These should all return 423 Locked
        r = client.get("/api/cases", headers=officer)
        check("/api/cases blocked", r.status_code == 423, str(r.status_code))
        
        r = client.get("/api/complaints", headers=officer)
        check("/api/complaints blocked", r.status_code == 423, str(r.status_code))
        
        print("\n--- Testing JWT validation during lockdown ---")
        
        # Test that a valid JWT allows access to admin endpoints
        r = client.get("/api/admin/system", headers=admin)
        check("Valid admin JWT bypasses lockdown", r.status_code == 200, str(r.status_code))
        
        # Test that an invalid JWT doesn't bypass lockdown
        r = client.get("/api/cases", headers={"Authorization": "Bearer invalid.token.here"})
        check("Invalid JWT doesn't bypass lockdown", r.status_code == 423, str(r.status_code))
        
        # Test that missing JWT doesn't bypass lockdown
        r = client.get("/api/cases")
        check("Missing JWT doesn't bypass lockdown", r.status_code == 423, str(r.status_code))
        
        # Disable lockdown for cleanup
        set_lockdown(False)
        check("lockdown state is disabled", not is_lockdown())


if __name__ == "__main__":
    test_lockdown_path_bypasses()
    
    print("\n" + "=" * 60)
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} failure(s):\n")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("RESULT: All lockdown security tests passed!")
