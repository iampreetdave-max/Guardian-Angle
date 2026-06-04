"""CrimeGPT — AI crime documentation automation.

Covers: unified pool CRUD roundtrip, offline section suggestion (snatching ->
BNS 304; OTP fraud -> BNS 318/319 + IT Act 66C/66D), generation of all 7 doc
types (PDF bytes + version bump), the auto case-diary entry on generation, and
citizen role gating (403).

The officer and lead demo accounts share the seeded Cyber Investigation Unit
team, so a case created by the lead (with that team) is accessible to the
officer — exactly the real RBAC path.
"""
from __future__ import annotations

import pytest

from app.crimegpt.service import DOC_TYPES


@pytest.fixture(scope="module")
def case_id(client, auth_headers) -> int:
    """A case owned by the lead's team, accessible to the officer."""
    r = client.post("/api/cases", headers=auth_headers["lead"], json={
        "title": "Mobile snatching near Lal Darwaja",
        "description": ("Victim reports that two persons on a motorcycle snatched "
                        "her mobile phone and gold chain near the bus stop. One "
                        "accused threatened her when she resisted."),
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ----------------------------------------------------------------- pool CRUD
def test_pool_crud_roundtrip(client, auth_headers, case_id):
    off = auth_headers["officer"]

    # add an accused, a victim, a witness
    pa = client.post(f"/api/crimegpt/cases/{case_id}/parties", headers=off, json={
        "role": "accused", "name": "Ramesh K.", "age": 27, "gender": "M",
        "address": "Dariapur, Ahmedabad", "phone": "9876500000",
        "id_proof": "Aadhaar xxxx-1234", "description": "Tall, scar on left cheek",
    })
    assert pa.status_code == 200, pa.text
    accused_id = pa.json()["id"]

    pv = client.post(f"/api/crimegpt/cases/{case_id}/parties", headers=off, json={
        "role": "victim", "name": "Sita P.", "age": 34, "gender": "F"})
    assert pv.status_code == 200, pv.text

    pw = client.post(f"/api/crimegpt/cases/{case_id}/parties", headers=off, json={
        "role": "witness", "name": "Anil shopkeeper"})
    assert pw.status_code == 200, pw.text

    # seizure + statement
    sz = client.post(f"/api/crimegpt/cases/{case_id}/seizures", headers=off, json={
        "item": "Samsung mobile phone", "quantity": "1", "seized_from": "Ramesh K.",
        "witness_names": "Anil, Mahesh"})
    assert sz.status_code == 200, sz.text

    st = client.post(f"/api/crimegpt/cases/{case_id}/statements", headers=off, json={
        "party_id": accused_id, "statement_text": "I was present at the scene."})
    assert st.status_code == 200, st.text

    # read back the pool
    pool = client.get(f"/api/crimegpt/cases/{case_id}/pool", headers=off)
    assert pool.status_code == 200, pool.text
    body = pool.json()
    roles = sorted(p["role"] for p in body["parties"])
    assert roles == ["accused", "victim", "witness"]
    assert len(body["seizures"]) == 1
    assert len(body["statements"]) == 1
    assert body["case"]["id"] == case_id

    # update + delete a party
    up = client.patch(f"/api/crimegpt/cases/{case_id}/parties/{accused_id}",
                      headers=off, json={"phone": "9999999999"})
    assert up.status_code == 200, up.text
    dl = client.delete(f"/api/crimegpt/cases/{case_id}/parties/{accused_id}",
                       headers=off)
    assert dl.status_code == 200, dl.text


# ----------------------------------------------------------------- suggestions
def test_suggest_snatching(client, auth_headers):
    r = client.post("/api/crimegpt/suggest-sections", headers=auth_headers["officer"],
                    json={"narrative": "Two men on a bike snatched her mobile phone "
                          "and snatching the gold chain near the market."})
    assert r.status_code == 200, r.text
    sugg = r.json()["suggestions"]
    bns_all = " ".join(b for s in sugg for b in s["bns"])
    assert "BNS 304" in bns_all, bns_all


def test_suggest_otp_fraud(client, auth_headers):
    r = client.post("/api/crimegpt/suggest-sections", headers=auth_headers["officer"],
                    json={"narrative": "The complainant received a fake call asking "
                          "for an OTP. The fraudster used personation and phishing "
                          "to commit online fraud and money was transferred via UPI."})
    assert r.status_code == 200, r.text
    blob = str(r.json()["suggestions"])
    assert "BNS 318" in blob, blob
    assert "66C" in blob and "66D" in blob, blob


# ----------------------------------------------------------------- documents
@pytest.mark.parametrize("doc_type", list(DOC_TYPES.keys()))
def test_generate_each_doc_type(client, auth_headers, case_id, doc_type):
    off = auth_headers["officer"]
    r = client.post(f"/api/crimegpt/cases/{case_id}/documents/{doc_type}",
                    headers=off)
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF", f"{doc_type} did not return a PDF"
    assert r.headers.get("content-type", "").startswith("application/pdf")
    v1 = int(r.headers["X-Document-Version"])

    # regenerating bumps the version
    r2 = client.post(f"/api/crimegpt/cases/{case_id}/documents/{doc_type}",
                     headers=off)
    assert r2.status_code == 200, r2.text
    assert int(r2.headers["X-Document-Version"]) == v1 + 1


def test_diary_auto_entry_after_generation(client, auth_headers, case_id):
    off = auth_headers["officer"]
    # generate one document, then confirm a diary 'document' entry exists
    client.post(f"/api/crimegpt/cases/{case_id}/documents/seizure_receipt",
                headers=off)
    d = client.get(f"/api/crimegpt/cases/{case_id}/diary", headers=off)
    assert d.status_code == 200, d.text
    types = [e["entry_type"] for e in d.json()["items"]]
    assert "document" in types, types
    narratives = " ".join(e["narrative"] for e in d.json()["items"])
    assert "Seizure Receipt" in narratives


def test_documents_list_versions(client, auth_headers, case_id):
    off = auth_headers["officer"]
    docs = client.get(f"/api/crimegpt/cases/{case_id}/documents", headers=off)
    assert docs.status_code == 200, docs.text
    items = docs.json()["items"]
    assert items, "expected generated documents to be listed"
    # every row carries a content hash + human title
    assert all(it["content_hash"] for it in items)
    assert all(it["doc_title"] for it in items)


def test_hindi_generation_never_blocked(client, auth_headers, case_id):
    """Offline (no Gemini key) hi/gu generation must still return a valid PDF."""
    off = auth_headers["officer"]
    r = client.post(f"/api/crimegpt/cases/{case_id}/documents/remand_request"
                    "?language=hi", headers=off)
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF"


# ----------------------------------------------------------------- gating
def test_citizen_forbidden(client, auth_headers, case_id):
    cit = auth_headers["citizen"]
    assert client.get(f"/api/crimegpt/cases/{case_id}/pool",
                      headers=cit).status_code == 403
    assert client.post("/api/crimegpt/suggest-sections", headers=cit,
                       json={"narrative": "theft"}).status_code == 403
    assert client.post(f"/api/crimegpt/cases/{case_id}/documents/seizure_receipt",
                       headers=cit).status_code == 403
    assert client.post(f"/api/crimegpt/cases/{case_id}/parties", headers=cit,
                       json={"role": "accused", "name": "X"}).status_code == 403


def test_health(client):
    r = client.get("/api/crimegpt/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["module"] == "CrimeGPT"
    assert len(body["doc_types"]) == 7
