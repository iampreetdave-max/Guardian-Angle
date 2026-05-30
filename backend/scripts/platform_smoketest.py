"""End-to-end smoke test of the CityShield platform API (run against a server)."""
import sys
import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"


def login(email, pw):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw})
    r.raise_for_status()
    return r.json()["token"]


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def main():
    ok = 0
    admin = login("admin@city.gov", "admin123")
    lead = login("lead@city.gov", "lead123")
    officer = login("officer@city.gov", "officer123")
    citizen = login("citizen@example.com", "citizen123")
    print("login: all 4 roles OK"); ok += 1

    # citizen files a complaint
    c = requests.post(f"{BASE}/api/complaints", headers=H(citizen), json={
        "title": "UPI fraud - money debited after OTP shared",
        "description": "I got a call from a fake bank official and Rs 85000 was debited.",
        "category": "cyber-fraud", "location": "Navrangpura, Ahmedabad"}).json()
    cid = c["id"]; print(f"complaint filed: id={cid}"); ok += 1

    # admin sees it
    comps = requests.get(f"{BASE}/api/complaints", headers=H(admin)).json()
    assert any(x["id"] == cid for x in comps), "admin can't see complaint"
    print(f"admin sees {len(comps)} complaint(s)"); ok += 1

    # lead triages -> creates case, gets team, notifies citizen
    tr = requests.post(f"{BASE}/api/complaints/{cid}/triage", headers=H(lead), json={
        "severity": "high", "priority": 1, "create_case": True, "assigned_team_id": 1,
        "response_message": "Your complaint is registered; our cyber unit is investigating."}).json()
    case_id = tr["case_id"]; print(f"triaged -> case id={case_id}"); ok += 1

    # lead assigns the officer
    requests.post(f"{BASE}/api/cases/{case_id}/assign", headers=H(lead),
                  json={"user_ids": [3], "role_on_case": "investigator"}).raise_for_status()
    print("officer assigned to case"); ok += 1

    # officer (assigned) adds evidence + a document
    requests.post(f"{BASE}/api/cases/{case_id}/evidence", headers=H(officer), json={
        "kind": "note", "caption": "Bank statement shows transfer to mule account",
        "visibility": "team"}).raise_for_status()
    requests.post(f"{BASE}/api/cases/{case_id}/evidence", headers=H(officer), json={
        "kind": "report", "ref": "frame:42", "caption": "CCTV: suspect at ATM",
        "visibility": "citizen"}).raise_for_status()
    requests.post(f"{BASE}/api/cases/{case_id}/documents", headers=H(officer), json={
        "doc_type": "FIR", "title": "FIR draft", "content": "IPC 420, IT Act 66C/66D..."}).raise_for_status()
    print("officer added 2 evidence + 1 FIR document"); ok += 1

    # citizen CANNOT access case yet (not visible)
    r = requests.get(f"{BASE}/api/cases/{case_id}", headers=H(citizen))
    assert r.status_code == 403, f"citizen should be blocked, got {r.status_code}"
    print("citizen blocked before visibility toggle (403 OK)"); ok += 1

    # officer turns on citizen visibility
    requests.post(f"{BASE}/api/cases/{case_id}/citizen-visibility", headers=H(officer),
                  json={"citizen_visible": True}).raise_for_status()
    # now citizen can view, and sees only citizen-visibility evidence
    case_view = requests.get(f"{BASE}/api/cases/{case_id}", headers=H(citizen))
    assert case_view.status_code == 200, "citizen still blocked after toggle"
    ev = requests.get(f"{BASE}/api/cases/{case_id}/evidence", headers=H(citizen)).json()
    staff_ev = requests.get(f"{BASE}/api/cases/{case_id}/evidence", headers=H(officer)).json()
    print(f"after toggle: citizen sees {len(ev)} evidence, staff sees {len(staff_ev)}"); ok += 1
    assert len(ev) == 1 and len(staff_ev) == 2, "visibility filtering wrong"
    print("evidence visibility scoping correct (citizen=1, staff=2)"); ok += 1

    # citizen documents are hidden
    cdocs = requests.get(f"{BASE}/api/cases/{case_id}/documents", headers=H(citizen)).json()
    assert cdocs == [], "citizen should not see internal documents"
    print("internal documents hidden from citizen"); ok += 1

    # citizen sends ONE message; second is blocked
    requests.post(f"{BASE}/api/cases/{case_id}/messages", headers=H(citizen),
                  json={"body": "Please update me."}).raise_for_status()
    r2 = requests.post(f"{BASE}/api/cases/{case_id}/messages", headers=H(citizen),
                       json={"body": "second message"})
    assert r2.status_code == 403, "citizen 2nd message should be blocked"
    print("citizen single-message cap enforced"); ok += 1

    # officer (non-lead) cannot close; lead closes
    rclose = requests.post(f"{BASE}/api/cases/{case_id}/close", headers=H(officer),
                           json={"verdict": "x"})
    assert rclose.status_code == 403, "officer should not close"
    requests.post(f"{BASE}/api/cases/{case_id}/close", headers=H(lead),
                  json={"verdict": "Accused identified and arrested; charge-sheet filed."}).raise_for_status()
    print("close: officer blocked, lead closed (verdict recorded)"); ok += 1

    # citizen rates
    requests.post(f"{BASE}/api/cases/{case_id}/rate", headers=H(citizen),
                  json={"stars": 5, "comment": "Quick and helpful."}).raise_for_status()
    print("citizen rated the closed case"); ok += 1

    # notifications + outbox
    n = requests.get(f"{BASE}/api/notifications", headers=H(citizen)).json()
    print(f"citizen notifications: unread={n['unread']}, total={len(n['items'])}"); ok += 1

    print(f"\nRESULT: PASS — {ok} checks passed.")


if __name__ == "__main__":
    main()
