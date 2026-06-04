"""GovIntel polish — advanced filters, cross-linking, bookmarks, saved searches,
and the insights/trending strip.

Runs entirely on the offline keyword path (no chromadb in the test venv), which is
the deployment-critical fallback, so these tests also assert the module stays fully
functional without the semantic stack. The bundled corpus (25 curated documents) is
the always-on fixture, seeded idempotently on first request.
"""
from __future__ import annotations


# ----------------------------------------------------------------- advanced filters
def test_filtered_search_returns_only_matching_type_and_jurisdiction(client):
    """doc_type + jurisdiction (Central vs Gujarat) narrow the result set exactly."""
    r = client.get("/api/gov/search", params={"doc_type": "Act", "jurisdiction": "central", "k": 30})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] > 0, "expected at least one central Act in the bundled corpus"
    for d in body["results"]:
        assert d["doc_type"] == "Act"
        assert d["region"] == "central"

    # `region` is the legacy alias for `jurisdiction` — same contract.
    rg = client.get("/api/gov/search", params={"region": "gujarat", "k": 30})
    assert rg.status_code == 200, rg.text
    assert rg.json()["count"] > 0
    assert all(d["region"] == "gujarat" for d in rg.json()["results"])


def test_search_is_open_without_auth(client):
    """auth_gate keeps search/read open (no login required), like Arbiter."""
    r = client.get("/api/gov/search", params={"q": "right to information"})
    assert r.status_code == 200, r.text
    assert r.json()["count"] >= 1


def test_departments_filter_lists_departments(client, auth_headers):
    r = client.get("/api/gov/departments", headers=auth_headers["officer"])
    assert r.status_code == 200, r.text
    assert isinstance(r.json()["departments"], list)
    assert len(r.json()["departments"]) > 0


# ----------------------------------------------------------------- cross-linking
def test_related_docs_returns_kin_for_corpus_doc(client):
    """A document with curated kin (RTI Act) returns a non-empty related set, with
    curated links surfaced first and a link_type label on every entry."""
    r = client.get("/api/gov/document/act-rti-2005/related")
    assert r.status_code == 200, r.text
    body = r.json()
    rel = body["related"]
    assert len(rel) > 0, "RTI Act should cross-link to its curated kin"
    assert any(x.get("link_type") == "curated" for x in rel)
    assert all("link_type" in x and "doc_type" in x for x in rel)
    assert body["doc_id"] == "act-rti-2005"
    # the curated chain (judgment / scheme) must be present
    rel_ids = {x["id"] for x in rel}
    assert "judgment-cbse-aditya-bandopadhyay" in rel_ids


def test_related_for_unknown_doc_is_empty(client):
    r = client.get("/api/gov/document/does-not-exist/related")
    assert r.status_code == 200, r.text
    assert r.json()["related"] == []


# ----------------------------------------------------------------- bookmarks
def test_bookmark_roundtrip(client, auth_headers):
    """star -> list (present) -> unstar -> list (absent), per-user."""
    h = auth_headers["officer"]
    doc_id = "act-rti-2005"

    # clean slate
    client.delete(f"/api/gov/bookmarks/{doc_id}", headers=h)

    assert client.post("/api/gov/bookmarks", json={"doc_id": doc_id}, headers=h).status_code == 200
    listed = client.get("/api/gov/bookmarks", headers=h).json()["items"]
    assert any(x["id"] == doc_id for x in listed)

    assert client.delete(f"/api/gov/bookmarks/{doc_id}", headers=h).status_code == 200
    listed = client.get("/api/gov/bookmarks", headers=h).json()["items"]
    assert all(x["id"] != doc_id for x in listed)


def test_bookmarks_require_login(client):
    assert client.get("/api/gov/bookmarks").status_code == 401


# ----------------------------------------------------------------- saved searches
def test_saved_search_persists_and_reruns(client, auth_headers):
    """A saved search keeps query + filters + alert flag, lists back, and re-runs to
    a filtered result set."""
    h = auth_headers["lead"]
    payload = {"name": "Central Acts", "query": "", "doc_type": "Act",
               "region": "central", "alert": True}
    created = client.post("/api/gov/saved-searches", json=payload, headers=h)
    assert created.status_code == 200, created.text
    sid = created.json()["id"]
    assert created.json()["alert"] is True
    assert created.json()["filters"]["doc_type"] == "Act"

    items = client.get("/api/gov/saved-searches", headers=h).json()["items"]
    mine = next(x for x in items if x["id"] == sid)
    assert mine["name"] == "Central Acts"
    assert mine["alert"] is True
    assert mine["filters"]["region"] == "central"

    run = client.post(f"/api/gov/saved-searches/{sid}/run", headers=h)
    assert run.status_code == 200, run.text
    assert run.json()["count"] > 0
    assert all(d["doc_type"] == "Act" and d["region"] == "central"
               for d in run.json()["results"])

    assert client.delete(f"/api/gov/saved-searches/{sid}", headers=h).status_code == 200
    remaining = client.get("/api/gov/saved-searches", headers=h).json()["items"]
    assert all(x["id"] != sid for x in remaining)


def test_saved_search_rejects_empty(client, auth_headers):
    r = client.post("/api/gov/saved-searches", json={}, headers=auth_headers["officer"])
    assert r.status_code == 400, r.text


def test_run_unknown_saved_search_404(client, auth_headers):
    r = client.post("/api/gov/saved-searches/999999/run", headers=auth_headers["officer"])
    assert r.status_code == 404, r.text


def test_saved_searches_require_login(client):
    assert client.get("/api/gov/saved-searches").status_code == 401


# ----------------------------------------------------------------- insights strip
def test_insights_strip(client):
    """Trending/insights payload: counts by type & jurisdiction, totals, source
    health, and the most-bookmarked list — all available offline."""
    r = client.get("/api/gov/insights")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_documents"] > 0
    assert isinstance(body["by_type"], dict) and body["by_type"]
    assert isinstance(body["by_jurisdiction"], dict)
    assert "central" in body["by_jurisdiction"]
    assert isinstance(body["most_bookmarked"], list)
    assert isinstance(body["feeds"], list) and len(body["feeds"]) > 0
    # every feed row carries the health fields the UI renders
    for f in body["feeds"]:
        assert "feed_key" in f and "name" in f and "ok" in f


def test_most_bookmarked_reflects_a_star(client, auth_headers):
    """A starred document shows up (with a count) in the insights most-bookmarked list."""
    h = auth_headers["admin"]
    doc_id = "act-rti-2005"
    assert client.post("/api/gov/bookmarks", json={"doc_id": doc_id}, headers=h).status_code == 200
    try:
        body = client.get("/api/gov/insights").json()
        ids = {x["doc_id"] for x in body["most_bookmarked"]}
        assert doc_id in ids
        row = next(x for x in body["most_bookmarked"] if x["doc_id"] == doc_id)
        assert row["count"] >= 1
    finally:
        client.delete(f"/api/gov/bookmarks/{doc_id}", headers=h)
