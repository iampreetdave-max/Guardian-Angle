"""GovIntel REST API — mounted under /api/gov/*.

Single point of access to government resolutions, notifications, circulars,
Acts, rules, judgments and schemes. Search/read endpoints are open by default
(auth_gate, like Arbiter); bookmarks/subscriptions need a login; feed refresh is
restricted to lead/admin.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..arbiter import llm
from ..platform.security import auth_gate, get_current_user, require_role
from . import service, sources, store

router = APIRouter()


class SummarizeRequest(BaseModel):
    id: str = ""
    text: str = ""
    language: str = Field("en", description="en | hi | gu")


class SubscriptionRequest(BaseModel):
    query: str = ""
    doc_type: str = ""
    region: str = ""


class BookmarkRequest(BaseModel):
    doc_id: str


class SavedSearchRequest(BaseModel):
    name: str = ""
    query: str = ""
    doc_type: str = ""
    region: str = ""
    department: str = ""
    date_from: str = ""
    date_to: str = ""
    alert: bool = False


# ----------------------------------------------------------------- health/meta
@router.get("/health", tags=["gov"])
def gov_health() -> dict:
    return {
        "module": "GovIntel",
        "corpus_documents": service.document_count(),
        "semantic": store.semantic_enabled(),
        "categories": service.CATEGORIES,
        "regions": service.REGIONS,
        "feeds": sources.feed_catalog(),
        "llm_online": llm.is_online(),
        "mode": "Gemini summaries" if llm.is_online() else "offline (extractive)",
        "search_mode": "semantic (ChromaDB)" if store.semantic_enabled() else "keyword",
        "languages": list(llm.LANGUAGES.keys()),
    }


@router.get("/categories", tags=["gov"])
def gov_categories() -> dict:
    return {"categories": service.CATEGORIES, "regions": service.REGIONS}


@router.get("/departments", tags=["gov"])
def gov_departments(_user=Depends(auth_gate)) -> dict:
    return {"departments": service.departments()}


@router.get("/trending", tags=["gov"])
def gov_trending() -> dict:
    return {"trending": service.trending()}


@router.get("/insights", tags=["gov"])
def gov_insights() -> dict:
    """Trending/insights strip: counts by type & jurisdiction, most-bookmarked,
    latest fetch timestamp and per-feed source health."""
    return service.insights()


@router.get("/suggest", tags=["gov"])
def gov_suggest(q: str = Query("", description="prefix to auto-complete")) -> dict:
    return {"suggestions": service.suggest(q)}


# ----------------------------------------------------------------- search/read
@router.get("/search", tags=["gov"])
def gov_search(
    q: str = Query("", description="keyword / semantic query"),
    doc_type: str = Query("", description="GR|Notification|Circular|Act|Rule|Judgment|Scheme"),
    region: str = Query("", description="central|gujarat"),
    jurisdiction: str = Query("", description="alias for region: central|gujarat"),
    department: str = Query(""),
    date_from: str = Query("", description="ISO date lower bound"),
    date_to: str = Query("", description="ISO date upper bound"),
    k: int = Query(20, ge=1, le=60),
    _user=Depends(auth_gate),
) -> dict:
    return service.search(query=q, doc_type=doc_type, region=region,
                          jurisdiction=jurisdiction, department=department,
                          date_from=date_from, date_to=date_to, k=k)


@router.get("/document/{doc_id}", tags=["gov"])
def gov_document(doc_id: str, _user=Depends(auth_gate)) -> dict:
    doc = service.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/document/{doc_id}/related", tags=["gov"])
def gov_related(doc_id: str, _user=Depends(auth_gate)) -> dict:
    return service.related(doc_id)


@router.post("/summarize", tags=["gov"])
def gov_summarize(body: SummarizeRequest, _user=Depends(auth_gate)) -> dict:
    if not body.id and not body.text:
        raise HTTPException(400, "Provide an `id` or `text` to summarise")
    return service.summarize(doc_id=body.id, text=body.text, language=body.language)


# ----------------------------------------------------------------- bookmarks
@router.get("/bookmarks", tags=["gov"])
def list_bookmarks(user: dict = Depends(get_current_user)) -> dict:
    return {"items": service.list_bookmarks(user["id"])}


@router.post("/bookmarks", tags=["gov"])
def add_bookmark(body: BookmarkRequest, user: dict = Depends(get_current_user)) -> dict:
    service.add_bookmark(user["id"], body.doc_id)
    return {"ok": True}


@router.delete("/bookmarks/{doc_id}", tags=["gov"])
def remove_bookmark(doc_id: str, user: dict = Depends(get_current_user)) -> dict:
    service.remove_bookmark(user["id"], doc_id)
    return {"ok": True}


# ----------------------------------------------------------------- subscriptions
@router.get("/subscriptions", tags=["gov"])
def list_subscriptions(user: dict = Depends(get_current_user)) -> dict:
    return {"items": service.list_subscriptions(user["id"])}


@router.post("/subscriptions", tags=["gov"])
def add_subscription(body: SubscriptionRequest,
                     user: dict = Depends(get_current_user)) -> dict:
    if not (body.query.strip() or body.doc_type or body.region):
        raise HTTPException(400, "A subscription needs a query, category or region")
    return service.add_subscription(user["id"], query=body.query,
                                    doc_type=body.doc_type, region=body.region)


@router.delete("/subscriptions/{sub_id}", tags=["gov"])
def remove_subscription(sub_id: int, user: dict = Depends(get_current_user)) -> dict:
    service.remove_subscription(user["id"], sub_id)
    return {"ok": True}


# ----------------------------------------------------------------- saved searches
@router.get("/saved-searches", tags=["gov"])
def list_saved_searches(user: dict = Depends(get_current_user)) -> dict:
    return {"items": service.list_saved_searches(user["id"])}


@router.post("/saved-searches", tags=["gov"])
def add_saved_search(body: SavedSearchRequest,
                     user: dict = Depends(get_current_user)) -> dict:
    if not (body.query.strip() or body.doc_type or body.region or body.department):
        raise HTTPException(400, "A saved search needs a query, category, region or department")
    filters = {
        "doc_type": body.doc_type, "region": body.region,
        "department": body.department, "date_from": body.date_from,
        "date_to": body.date_to,
    }
    return service.add_saved_search(user["id"], name=body.name, query=body.query,
                                    filters=filters, alert=body.alert)


@router.post("/saved-searches/{search_id}/run", tags=["gov"])
def run_saved_search(search_id: int, k: int = Query(24, ge=1, le=60),
                     user: dict = Depends(get_current_user)) -> dict:
    res = service.run_saved_search(user["id"], search_id, k=k)
    if not res:
        raise HTTPException(404, "Saved search not found")
    return res


@router.delete("/saved-searches/{search_id}", tags=["gov"])
def remove_saved_search(search_id: int, user: dict = Depends(get_current_user)) -> dict:
    service.remove_saved_search(user["id"], search_id)
    return {"ok": True}


# ----------------------------------------------------------------- refresh (lead+)
@router.post("/refresh", tags=["gov"])
def gov_refresh(_user: dict = Depends(require_role("lead"))) -> dict:
    return service.refresh()
