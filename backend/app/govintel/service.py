"""GovIntel service layer — unified search, summarisation, cross-linking,
bookmarks, subscriptions, and feed refresh with notification fan-out.

The bundled corpus is the always-on backbone (works fully offline); live RSS
docs enrich it when available. Summaries reuse the Arbiter LLM layer (Gemini
when keyed, deterministic offline fallback otherwise). The refresh job pushes
new documents matching a user's subscription into the existing `notifications`
table, so government updates surface in the same in-app bell as case alerts.
"""
from __future__ import annotations

import json
import logging
import threading

from ..database import get_conn
from ..arbiter import llm  # reuse Gemini-or-offline generation + LANGUAGES
from . import categorize, sources, store

log = logging.getLogger("visionscan.govintel.service")

CATEGORIES = ["GR", "Notification", "Circular", "Act", "Rule", "Judgment", "Scheme"]
REGIONS = ["central", "gujarat"]
# Human-facing jurisdiction labels mapped onto the stored `region` value.
JURISDICTIONS = {"central": "Central (Government of India)", "gujarat": "Gujarat"}

_seed_lock = threading.Lock()
_seeded = False
_related_map: dict[str, list[str]] = {}

# Idempotent DDL for the tables this module owns beyond the base schema. Run from
# _ensure_seed() so the module is self-contained even on an older DB that predates
# saved-searches / feed-health (mirrors database._migrate's CREATE IF NOT EXISTS).
_EXTRA_TABLES = """
CREATE TABLE IF NOT EXISTS gov_saved_searches (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    name       TEXT NOT NULL DEFAULT '',
    query      TEXT NOT NULL DEFAULT '',
    filters    TEXT NOT NULL DEFAULT '{}',
    alert      INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_gov_saved_user ON gov_saved_searches(user_id);
CREATE TABLE IF NOT EXISTS gov_feed_status (
    feed_key      TEXT PRIMARY KEY,
    name          TEXT NOT NULL DEFAULT '',
    last_attempt  TEXT,
    last_success  TEXT,
    last_count    INTEGER NOT NULL DEFAULT 0,
    ok            INTEGER NOT NULL DEFAULT 0
);
"""


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
            conn.executescript(_EXTRA_TABLES)  # self-contained table provisioning
            for d in corpus:
                kw = ", ".join(d.get("keywords", []) or [])
                # Derive (and persist) department / jurisdiction once when the
                # corpus entry omits them, so advanced filters work uniformly and
                # we never recompute the heuristic per query.
                dept = d.get("department") or categorize.guess_department(
                    d.get("title", ""), d.get("summary", "") or d.get("body", ""))
                region = d.get("region") or categorize.guess_region(
                    d.get("title", ""), d.get("summary", "") or d.get("body", ""))
                conn.execute(
                    "INSERT OR IGNORE INTO gov_documents "
                    "(id, title, doc_type, department, ministry, region, date, "
                    " summary, body, keywords, source_url, language, origin) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'bundled')",
                    (d["id"], d["title"], d["doc_type"], dept,
                     d.get("ministry"), region, d.get("date"),
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
           jurisdiction: str = "", k: int = 20) -> dict:
    _ensure_seed()
    # `jurisdiction` is the citizen-facing label for `region` (Central vs
    # Gujarat); accept either so the advanced-filter UI can use the clearer term.
    region = region or jurisdiction
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
def _kw_set(doc: dict) -> set[str]:
    kw = doc.get("keywords")
    if isinstance(kw, str):
        kw = [k.strip() for k in kw.split(",")]
    return {k.lower() for k in (kw or []) if k}


def _act_family(doc: dict) -> str:
    """A coarse 'act family' key so a GR, its parent Act and a judgment that share
    a subject group together (e.g. 'rti', 'data', 'pension'). Offline, deterministic."""
    blob = f"{doc.get('id','')} {doc.get('title','')} {doc.get('keywords','')}".lower()
    for fam in ("rti", "right to information", "data protection", "dpdp", "pension",
                "cyber", "scholarship", "ration", "land record", "ayushman",
                "consumer", "gst", "rera", "labour", "sanhita"):
        if fam in blob:
            return fam.split()[0]
    # else the id stem before the first dash group (e.g. act-rti-2005 -> act)
    return (doc.get("id", "").split("-", 1)[0] or "").lower()


def _overlap_score(base: set[str], base_fam: str, base_type: str, cand: dict) -> tuple[float, str]:
    """Offline relatedness: keyword Jaccard + act-family + category bonuses.

    Returns (score, link_type) where link_type explains the strongest signal so
    the UI can label the chain (family / keyword / category)."""
    cand_kw = _kw_set(cand)
    inter = base & cand_kw
    union = base | cand_kw
    jacc = (len(inter) / len(union)) if union else 0.0
    score = 0.6 * jacc
    link = "keyword" if inter else "related"
    if base_fam and base_fam == _act_family(cand):
        score += 0.35
        link = "family"
    if base_type and base_type == cand.get("doc_type"):
        score += 0.05
    return round(min(1.0, score), 4), link


def related(doc_id: str, k: int = 6) -> dict:
    _ensure_seed()
    doc = get_document(doc_id)
    if not doc:
        return {"doc_id": doc_id, "related": [], "grouped": {}}

    base_kw = _kw_set(doc)
    base_fam = _act_family(doc)
    base_type = doc.get("doc_type")

    picked: dict[str, dict] = {}
    # 1) explicit curated links (bundled corpus, GR↔parent Act↔judgment chains)
    for rid in _related_map.get(doc_id, []):
        rd = get_document(rid)
        if rd:
            picked[rid] = {**rd, "score": 1.0, "link_type": "curated"}

    # 2) candidate pool — semantic neighbours when available, else the whole
    #    SQLite cache scored by offline keyword/metadata overlap.
    query = (f"{doc.get('title','')} {doc.get('summary','')} "
             f"{doc.get('keywords','') if isinstance(doc.get('keywords'), str) else ' '.join(doc.get('keywords') or [])}")
    if store.semantic_enabled():
        candidates = store.retrieve(query, k=k + 12)
    else:
        with get_conn() as conn:
            candidates = [_kw_hit(r) for r in conn.execute(
                "SELECT * FROM gov_documents").fetchall()]

    scored: list[dict] = []
    for h in candidates:
        if h["id"] == doc_id or h["id"] in picked:
            continue
        ov, link = _overlap_score(base_kw, base_fam, base_type, h)
        # keep a semantic neighbour even with no lexical overlap (Chroma already
        # vouched for it); otherwise require some overlap signal.
        sem = h.get("score") if store.semantic_enabled() else None
        if ov <= 0 and not sem:
            continue
        merged = ov if sem is None else round(max(ov, 0.45 + 0.55 * float(sem)), 4)
        scored.append({**h, "score": merged,
                       "link_type": link if ov >= 0.1 else "semantic"})

    scored.sort(key=lambda r: r["score"], reverse=True)
    for h in scored:
        if len(picked) >= k:
            break
        picked[h["id"]] = h

    rel = list(picked.values())
    rel.sort(key=lambda r: (r.get("link_type") != "curated", -(r.get("score") or 0)))
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


# --------------------------------------------------------------- saved searches
_SAVED_FILTER_KEYS = ("doc_type", "region", "department", "date_from", "date_to")


def _saved_row(row) -> dict:
    d = dict(row)
    try:
        d["filters"] = json.loads(d.get("filters") or "{}")
    except (ValueError, TypeError):
        d["filters"] = {}
    d["alert"] = bool(d.get("alert"))
    return d


def list_saved_searches(user_id: int) -> list[dict]:
    _ensure_seed()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM gov_saved_searches WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)).fetchall()
    return [_saved_row(r) for r in rows]


def add_saved_search(user_id: int, name: str = "", query: str = "",
                     filters: dict | None = None, alert: bool = False) -> dict:
    _ensure_seed()
    clean = {k: (filters or {}).get(k) or "" for k in _SAVED_FILTER_KEYS}
    label = (name or query or "").strip()
    if not label:
        label = " · ".join(v for v in (clean["doc_type"], clean["region"],
                                       clean["department"]) if v) or "All updates"
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO gov_saved_searches (user_id, name, query, filters, alert) "
            "VALUES (?,?,?,?,?)",
            (user_id, label, (query or "").strip(), json.dumps(clean), 1 if alert else 0))
        sid = cur.lastrowid
    return {"id": sid, "name": label, "query": query, "filters": clean, "alert": alert}


def remove_saved_search(user_id: int, search_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM gov_saved_searches WHERE id = ? AND user_id = ?",
                     (search_id, user_id))


def run_saved_search(user_id: int, search_id: int, k: int = 24) -> dict:
    _ensure_seed()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM gov_saved_searches WHERE id = ? AND user_id = ?",
            (search_id, user_id)).fetchone()
    if not row:
        return {}
    s = _saved_row(row)
    f = s["filters"]
    return search(query=s["query"], doc_type=f.get("doc_type", ""),
                  region=f.get("region", ""), department=f.get("department", ""),
                  date_from=f.get("date_from", ""), date_to=f.get("date_to", ""), k=k)


# --------------------------------------------------------------- insights / trending strip
def insights() -> dict:
    """Small dashboard payload for the panel header: counts by type & jurisdiction,
    most-bookmarked documents, latest fetch timestamp and per-feed source health."""
    _ensure_seed()
    with get_conn() as conn:
        by_type = {r["doc_type"]: r["c"] for r in conn.execute(
            "SELECT doc_type, COUNT(*) c FROM gov_documents GROUP BY doc_type")}
        by_jur = {r["region"]: r["c"] for r in conn.execute(
            "SELECT region, COUNT(*) c FROM gov_documents "
            "WHERE region IS NOT NULL AND region <> '' GROUP BY region")}
        total = conn.execute("SELECT COUNT(*) c FROM gov_documents").fetchone()["c"]
        live = conn.execute(
            "SELECT COUNT(*) c FROM gov_documents WHERE origin = 'live'").fetchone()["c"]
        latest = conn.execute(
            "SELECT MAX(fetched_at) m FROM gov_documents").fetchone()["m"]
        top = conn.execute(
            "SELECT b.doc_id, COUNT(*) c, d.title, d.doc_type, d.region "
            "FROM gov_bookmarks b JOIN gov_documents d ON d.id = b.doc_id "
            "GROUP BY b.doc_id ORDER BY c DESC, MAX(b.created_at) DESC LIMIT 5"
        ).fetchall()
        feeds = [dict(r) for r in conn.execute(
            "SELECT * FROM gov_feed_status ORDER BY name").fetchall()]
        saved = conn.execute("SELECT COUNT(*) c FROM gov_saved_searches").fetchone()["c"]
        marks = conn.execute("SELECT COUNT(*) c FROM gov_bookmarks").fetchone()["c"]

    most_bookmarked = [{"doc_id": r["doc_id"], "title": r["title"],
                        "doc_type": r["doc_type"], "region": r["region"],
                        "count": r["c"]} for r in top]
    # If no refresh has run yet, surface the static feed catalog as "not yet polled"
    if not feeds:
        feeds = [{"feed_key": f["key"], "name": f["name"], "ok": None,
                  "last_attempt": None, "last_success": None, "last_count": 0}
                 for f in sources.feed_catalog()]
    return {
        "total_documents": total,
        "live_documents": live,
        "by_type": by_type,
        "by_jurisdiction": by_jur,
        "jurisdiction_labels": JURISDICTIONS,
        "latest_fetched": latest,
        "most_bookmarked": most_bookmarked,
        "total_bookmarks": marks,
        "total_saved_searches": saved,
        "feeds": feeds,
        "semantic": store.semantic_enabled(),
        "llm_online": llm.is_online(),
    }


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
    docs, statuses = sources.fetch_all_with_status()
    _record_feed_status(statuses)
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


def _record_feed_status(statuses: list[dict]) -> None:
    """Upsert per-feed health rows so the insights strip can show source health."""
    if not statuses:
        return
    try:
        with get_conn() as conn:
            for s in statuses:
                conn.execute(
                    "INSERT INTO gov_feed_status "
                    "(feed_key, name, last_attempt, last_success, last_count, ok) "
                    "VALUES (?,?,?,?,?,?) "
                    "ON CONFLICT(feed_key) DO UPDATE SET "
                    "  name=excluded.name, last_attempt=excluded.last_attempt, "
                    "  last_count=excluded.last_count, ok=excluded.ok, "
                    "  last_success=CASE WHEN excluded.ok=1 "
                    "    THEN excluded.last_attempt ELSE gov_feed_status.last_success END",
                    (s["feed_key"], s["name"], s["attempted_at"],
                     s["attempted_at"] if s["ok"] else None,
                     s["last_count"], 1 if s["ok"] else 0))
    except Exception:  # pragma: no cover - never let health logging break refresh
        log.debug("GovIntel: feed status record failed", exc_info=True)


def _saved_alert_matches(saved: dict, doc: dict) -> bool:
    """A saved search with alert=1 behaves like a subscription over its filters."""
    f = saved.get("filters") or {}
    if f.get("doc_type") and f["doc_type"] != doc.get("doc_type"):
        return False
    if f.get("region") and f["region"] != doc.get("region"):
        return False
    dep = (f.get("department") or "").lower()
    if dep and dep not in (doc.get("department") or "").lower():
        return False
    q = (saved.get("query") or "").strip().lower()
    if q:
        blob = f"{doc.get('title','')} {doc.get('summary','')} {doc.get('keywords','')}".lower()
        if not any(term in blob for term in q.split()):
            return False
    return True


def _fan_out(new_docs: list[dict]) -> int:
    if not new_docs:
        return 0
    with get_conn() as conn:
        subs = [dict(r) for r in conn.execute(
            "SELECT * FROM gov_subscriptions").fetchall()]
        saved = [_saved_row(r) for r in conn.execute(
            "SELECT * FROM gov_saved_searches WHERE alert = 1").fetchall()]
    alerts = 0
    for doc in new_docs:
        # de-dupe so a user watching the same topic via both a subscription and a
        # saved-search alert only gets one notification per fresh document.
        notified: set[int] = set()
        for sub in subs:
            if _sub_matches(sub, doc) and sub["user_id"] not in notified:
                msg = f"New {doc.get('doc_type','update')}: {doc.get('title','')}"
                _notify_gov(sub["user_id"], msg, doc.get("source_url") or "")
                notified.add(sub["user_id"])
                alerts += 1
        for sv in saved:
            if sv["user_id"] in notified:
                continue
            if _saved_alert_matches(sv, doc):
                msg = f"New {doc.get('doc_type','update')}: {doc.get('title','')}"
                _notify_gov(sv["user_id"], msg, doc.get("source_url") or "")
                notified.add(sv["user_id"])
                alerts += 1
    return alerts


_DISCLAIMER = (
    "AI-generated summary of a public document for convenience only. Always "
    "verify against the official source before relying on it."
)
