"""GovIntel service layer — unified search, summarisation, cross-linking,
bookmarks, subscriptions, and feed refresh with notification fan-out.

The bundled corpus is the always-on backbone (works fully offline); live RSS
docs enrich it when available. Summaries reuse the Arbiter LLM layer (Gemini
when keyed, deterministic offline fallback otherwise). The refresh job pushes
new documents matching a user's subscription into the existing `notifications`
table, so government updates surface in the same in-app bell as case alerts.
"""
from __future__ import annotations

import logging
import threading

from ..database import get_conn
from ..arbiter import llm  # reuse Gemini-or-offline generation + LANGUAGES
from . import sources, store

log = logging.getLogger("visionscan.govintel.service")

CATEGORIES = ["GR", "Notification", "Circular", "Act", "Rule", "Judgment", "Scheme"]
REGIONS = ["central", "gujarat"]

_seed_lock = threading.Lock()
_seeded = False
_related_map: dict[str, list[str]] = {}


# --------------------------------------------------------------- seeding / cache
def _ensure_seed() -> None:
    """Persist the bundled corpus into gov_documents once (idempotent), and build
    the explicit related-doc map. Chroma seeding is handled in store.py."""
    global _seeded
    if _seeded:
        return
    with _seed_lock:
        if _seeded:
            return
        corpus = store.load_bundled_corpus()
        with get_conn() as conn:
            for d in corpus:
                kw = ", ".join(d.get("keywords", []) or [])
                conn.execute(
                    "INSERT OR IGNORE INTO gov_documents "
                    "(id, title, doc_type, department, ministry, region, date, "
                    " summary, body, keywords, source_url, language, origin) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'bundled')",
                    (d["id"], d["title"], d["doc_type"], d.get("department"),
                     d.get("ministry"), d.get("region"), d.get("date"),
                     d.get("summary"), d.get("body"), kw, d.get("source_url"),
                     d.get("language", "en")),
                )
                _related_map[d["id"]] = d.get("related_ids", []) or []
        store.corpus_size()  # warms the Chroma collection
        _seeded = True


def _row_doc(row) -> dict:
    d = dict(row)
    if isinstance(d.get("keywords"), str):
        d["keywords"] = [k.strip() for k in d["keywords"].split(",") if k.strip()]
    return d


def get_document(doc_id: str) -> dict | None:
    _ensure_seed()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM gov_documents WHERE id = ?", (doc_id,)).fetchone()
    return _row_doc(row) if row else None


def document_count() -> int:
    """Total indexed documents — Chroma when semantic, else the SQLite cache."""
    if store.semantic_enabled():
        n = store.corpus_size()
        if n:
            return n
    _ensure_seed()
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) c FROM gov_documents").fetchone()["c"]


# --------------------------------------------------------------- keyword search
def _kw_hit(row) -> dict:
    d = dict(row)
    return {
        "id": d["id"], "title": d["title"], "doc_type": d["doc_type"],
        "department": d.get("department"), "ministry": d.get("ministry"),
        "region": d.get("region"), "date": d.get("date"),
        "summary": d.get("summary"), "source_url": d.get("source_url"),
        "language": d.get("language"), "keywords": d.get("keywords"),
        "origin": d.get("origin"), "score": d.get("_score"),
    }


def _keyword_search(query: str, chroma_filters: dict, k: int) -> list[dict]:
    """SQLite lexical search used when ChromaDB is unavailable (offline fallback)."""
    clauses, params = [], []
    if chroma_filters.get("doc_type"):
        clauses.append("doc_type = ?"); params.append(chroma_filters["doc_type"])
    if chroma_filters.get("region"):
        clauses.append("region = ?"); params.append(chroma_filters["region"])
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(
            f"SELECT * FROM gov_documents{where}", params).fetchall()]

    terms = [t for t in query.lower().split() if t]
    scored = []
    for r in rows:
        title = (r.get("title") or "").lower()
        kw = (r.get("keywords") or "").lower()
        summ = (r.get("summary") or "").lower()
        body = (r.get("body") or "").lower()
        if terms:
            s = sum(3 * title.count(t) + 2 * kw.count(t) + summ.count(t)
                    + 0.2 * body.count(t) for t in terms)
            if s <= 0:
                continue
            r["_score"] = round(min(1.0, s / (len(terms) * 4.0)), 4)
        else:
            r["_score"] = None
        scored.append(r)
    if terms:
        scored.sort(key=lambda r: r["_score"] or 0, reverse=True)
    else:
        scored.sort(key=lambda r: r.get("date") or "", reverse=True)
    return [_kw_hit(r) for r in scored[:k]]


# --------------------------------------------------------------- search
def _post_filter(hits: list[dict], department: str = "", date_from: str = "",
                 date_to: str = "") -> list[dict]:
    out = []
    dep = (department or "").lower()
    for h in hits:
        if dep and dep not in (h.get("department") or "").lower():
            continue
        d = h.get("date") or ""
        if date_from and d and d < date_from:
            continue
        if date_to and d and d > date_to:
            continue
        out.append(h)
    return out


def search(query: str = "", doc_type: str = "", region: str = "",
           department: str = "", date_from: str = "", date_to: str = "",
           k: int = 20) -> dict:
    _ensure_seed()
    chroma_filters = {}
    if doc_type:
        chroma_filters["doc_type"] = doc_type
    if region:
        chroma_filters["region"] = region

    q = (query or "").strip()
    semantic = store.semantic_enabled()
    if q:
        # over-fetch so python-side dept/date filters still leave a full page
        if semantic:
            hits = store.retrieve(q, k=k * 3, filters=chroma_filters or None)
        else:
            hits = _keyword_search(q, chroma_filters, k=k * 3)
        _log_search(q)
    else:
        if semantic:
            hits = store.list_all(filters=chroma_filters or None, limit=k * 3)
        else:
            hits = _keyword_search("", chroma_filters, k=k * 3)

    hits = _post_filter(hits, department, date_from, date_to)[:k]

    counts: dict[str, int] = {}
    for h in hits:
        counts[h["doc_type"]] = counts.get(h["doc_type"], 0) + 1

    return {
        "query": q,
        "count": len(hits),
        "results": hits,
        "categories": counts,
        "llm_online": llm.is_online(),
    }


# --------------------------------------------------------------- cross-linking
def related(doc_id: str, k: int = 6) -> dict:
    _ensure_seed()
    doc = get_document(doc_id)
    if not doc:
        return {"doc_id": doc_id, "related": [], "grouped": {}}

    picked: dict[str, dict] = {}
    # 1) explicit curated links (bundled corpus)
    for rid in _related_map.get(doc_id, []):
        rd = get_document(rid)
        if rd:
            rd = {**rd, "score": 1.0, "link_type": "curated"}
            picked[rid] = rd
    # 2) semantic neighbours over title+summary (or lexical fallback)
    query = f"{doc.get('title','')} {doc.get('summary','')} {doc.get('keywords','') if isinstance(doc.get('keywords'),str) else ' '.join(doc.get('keywords') or [])}"
    if store.semantic_enabled():
        neighbours = store.retrieve(query, k=k + 4)
    else:
        neighbours = _keyword_search(query, {}, k=k + 4)
    for h in neighbours:
        if h["id"] == doc_id or h["id"] in picked:
            continue
        picked[h["id"]] = {**h, "link_type": "semantic"}
        if len(picked) >= k:
            break

    rel = list(picked.values())
    grouped: dict[str, list[dict]] = {}
    for r in rel:
        grouped.setdefault(r["doc_type"], []).append(r)
    return {"doc_id": doc_id, "related": rel, "grouped": grouped}


# --------------------------------------------------------------- summarisation
def summarize(doc_id: str = "", text: str = "", language: str = "en") -> dict:
    _ensure_seed()
    title = ""
    source = text or ""
    if doc_id:
        doc = get_document(doc_id)
        if doc:
            title = doc.get("title", "")
            source = doc.get("body") or doc.get("summary") or ""
    source = (source or "").strip()
    if not source:
        return {"summary": "No document text available to summarise.",
                "llm_used": False, "language": language}

    prompt = (
        "Summarise the following Indian government / legal document for a citizen "
        "in 3-5 short bullet points. Capture the purpose, who it applies to, key "
        "provisions or eligibility, and any important dates or deadlines. Do not "
        "invent facts beyond the text.\n\n"
        f"TITLE: {title}\n\nDOCUMENT:\n{source[:6000]}"
    )
    out = llm.generate(prompt, language=language)
    if out is None:
        out = _extractive_summary(title, source)
        llm_used = False
    else:
        llm_used = True
    return {"summary": out, "llm_used": llm_used, "language": language,
            "disclaimer": _DISCLAIMER}


def _extractive_summary(title: str, source: str) -> str:
    """Deterministic offline fallback: lead sentences as bullets."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", source.strip())
    bullets = [s.strip() for s in sentences if len(s.strip()) > 30][:4]
    if not bullets:
        bullets = [source[:300]]
    head = f"Summary of “{title}”:\n" if title else "Summary:\n"
    return head + "\n".join(f"• {b}" for b in bullets)


# --------------------------------------------------------------- suggest / trending
def suggest(prefix: str, limit: int = 8) -> list[str]:
    _ensure_seed()
    p = (prefix or "").strip().lower()
    if not p:
        return []
    pool: set[str] = set()
    with get_conn() as conn:
        for row in conn.execute("SELECT title, keywords FROM gov_documents"):
            for tok in (row["keywords"] or "").split(","):
                tok = tok.strip()
                if tok and p in tok.lower():
                    pool.add(tok)
            t = (row["title"] or "").strip()
            if p in t.lower():
                pool.add(t if len(t) <= 60 else t[:57] + "…")
    ranked = sorted(pool, key=lambda s: (not s.lower().startswith(p), len(s)))
    return ranked[:limit]


def trending(limit: int = 8) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT query, COUNT(*) c FROM gov_search_log "
            "GROUP BY lower(query) ORDER BY c DESC, MAX(created_at) DESC LIMIT ?",
            (limit,)).fetchall()
    live = [r["query"] for r in rows if r["query"].strip()]
    seed = ["pension", "cyber crime", "scholarship", "land records",
            "ration card", "data protection", "rti", "ayushman"]
    seen, out = set(), []
    for q in live + seed:
        ql = q.lower()
        if ql in seen:
            continue
        seen.add(ql)
        out.append(q)
        if len(out) >= limit:
            break
    return out


def _log_search(query: str) -> None:
    try:
        with get_conn() as conn:
            conn.execute("INSERT INTO gov_search_log (query) VALUES (?)", (query.strip(),))
    except Exception:  # pragma: no cover
        pass


def departments() -> list[str]:
    _ensure_seed()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT department FROM gov_documents "
            "WHERE department IS NOT NULL AND department <> '' ORDER BY department"
        ).fetchall()
    return [r["department"] for r in rows]


# --------------------------------------------------------------- bookmarks
def list_bookmarks(user_id: int) -> list[dict]:
    _ensure_seed()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT d.* FROM gov_bookmarks b JOIN gov_documents d ON d.id = b.doc_id "
            "WHERE b.user_id = ? ORDER BY b.created_at DESC", (user_id,)).fetchall()
    return [_row_doc(r) for r in rows]


def add_bookmark(user_id: int, doc_id: str) -> None:
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO gov_bookmarks (user_id, doc_id) VALUES (?, ?)",
                     (user_id, doc_id))


def remove_bookmark(user_id: int, doc_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM gov_bookmarks WHERE user_id = ? AND doc_id = ?",
                     (user_id, doc_id))


# --------------------------------------------------------------- subscriptions
def list_subscriptions(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM gov_subscriptions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)).fetchall()
    return [dict(r) for r in rows]


def add_subscription(user_id: int, query: str = "", doc_type: str = "",
                     region: str = "") -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO gov_subscriptions (user_id, query, doc_type, region) "
            "VALUES (?,?,?,?)", (user_id, query.strip(), doc_type or None, region or None))
        sub_id = cur.lastrowid
    return {"id": sub_id, "query": query, "doc_type": doc_type, "region": region}


def remove_subscription(user_id: int, sub_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM gov_subscriptions WHERE id = ? AND user_id = ?",
                     (sub_id, user_id))


def _sub_matches(sub: dict, doc: dict) -> bool:
    if sub.get("doc_type") and sub["doc_type"] != doc.get("doc_type"):
        return False
    if sub.get("region") and sub["region"] != doc.get("region"):
        return False
    q = (sub.get("query") or "").strip().lower()
    if q:
        blob = f"{doc.get('title','')} {doc.get('summary','')} {doc.get('keywords','')}".lower()
        if not any(term in blob for term in q.split()):
            return False
    return True


def _notify_gov(user_id: int, message: str, link: str) -> None:
    """Insert a gov-update alert into the shared notifications table (with link)."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO notifications (user_id, type, message, link) VALUES (?,?,?,?)",
            (user_id, "gov_update", message, link))


# --------------------------------------------------------------- refresh
def refresh() -> dict:
    """Poll the free government feeds, index new docs, and alert subscribers.

    Offline-safe: if no feed is reachable, returns zero counts without error.
    """
    _ensure_seed()
    docs = sources.fetch_all()
    new_docs: list[dict] = []
    with get_conn() as conn:
        for d in docs:
            exists = conn.execute("SELECT 1 FROM gov_documents WHERE id = ?",
                                  (d["id"],)).fetchone()
            if exists:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO gov_documents "
                "(id, title, doc_type, department, ministry, region, date, "
                " summary, body, keywords, source_url, language, origin) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'live')",
                (d["id"], d["title"], d["doc_type"], d.get("department"),
                 d.get("ministry"), d.get("region"), d.get("date"),
                 d.get("summary"), d.get("body"),
                 ", ".join(d.get("keywords", []) or []), d.get("source_url"),
                 d.get("language", "en")))
            new_docs.append(d)

    if new_docs:
        try:
            store.upsert_docs(new_docs)
        except Exception:  # pragma: no cover
            log.warning("GovIntel: chroma upsert of live docs failed", exc_info=True)

    alerts = _fan_out(new_docs)
    log.info("GovIntel refresh: %d fetched, %d new, %d alerts",
             len(docs), len(new_docs), alerts)
    return {"fetched": len(docs), "new": len(new_docs), "alerts": alerts,
            "feeds": sources.feed_catalog()}


def _fan_out(new_docs: list[dict]) -> int:
    if not new_docs:
        return 0
    with get_conn() as conn:
        subs = [dict(r) for r in conn.execute(
            "SELECT * FROM gov_subscriptions").fetchall()]
    alerts = 0
    for doc in new_docs:
        for sub in subs:
            if _sub_matches(sub, doc):
                msg = f"New {doc.get('doc_type','update')}: {doc.get('title','')}"
                _notify_gov(sub["user_id"], msg, doc.get("source_url") or "")
                alerts += 1
    return alerts


_DISCLAIMER = (
    "AI-generated summary of a public document for convenience only. Always "
    "verify against the official source before relying on it."
)
