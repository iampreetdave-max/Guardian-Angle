"""GovIntel vector store — ChromaDB over the bundled corpus + cached live docs.

Mirrors the offline-first pattern proven in arbiter/store.py: a persistent
ChromaDB collection using Chroma's built-in MiniLM ONNX embedder (no API key, no
torch, fully offline after a one-time model download). The bundled curated corpus
is indexed on first use; live RSS docs are upserted as they arrive. Retrieval is
local and instant — the semantic layer behind unified gov/legal search.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from ..config import get_settings

log = logging.getLogger("visionscan.govintel.store")

_CORPUS_PATH = Path(__file__).parent / "corpus" / "gov_corpus.json"
_COLLECTION = "gov_corpus"

_lock = threading.Lock()
_collection = None
_chroma_ok: bool | None = None


def load_bundled_corpus() -> list[dict]:
    return json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))


def semantic_enabled() -> bool:
    """True if ChromaDB is importable, so semantic retrieval is available.

    When False (e.g. a lightweight/field deployment without the RAG stack), the
    service layer falls back to a SQLite keyword search — the module stays fully
    functional, just lexical instead of semantic.
    """
    global _chroma_ok
    if _chroma_ok is None:
        try:
            import chromadb  # noqa: F401
            _chroma_ok = True
        except Exception:
            _chroma_ok = False
            log.warning("GovIntel: chromadb unavailable — using keyword search")
    return _chroma_ok


def _doc_text(d: dict) -> str:
    """The text Chroma embeds — title + summary + body + keywords for recall."""
    return (
        f"{d.get('doc_type', '')}: {d.get('title', '')}. "
        f"Department: {d.get('department', '')}. "
        f"{d.get('summary', '')} {d.get('body', '')} "
        f"Keywords: {', '.join(d.get('keywords', []) if isinstance(d.get('keywords'), list) else [d.get('keywords', '')])}."
    )


def _metadata(d: dict) -> dict:
    kw = d.get("keywords", [])
    if isinstance(kw, list):
        kw = ", ".join(kw)
    return {
        "title": d.get("title", "") or "",
        "doc_type": d.get("doc_type", "") or "",
        "department": d.get("department", "") or "",
        "ministry": d.get("ministry", "") or "",
        "region": d.get("region", "") or "",
        "date": d.get("date", "") or "",
        "summary": d.get("summary", "") or "",
        "source_url": d.get("source_url", "") or "",
        "language": d.get("language", "en") or "en",
        "keywords": kw or "",
        "origin": d.get("origin", "bundled") or "bundled",
    }


def _ensure_collection():
    global _collection
    if _collection is not None:
        return _collection
    with _lock:
        if _collection is not None:
            return _collection
        import chromadb

        settings = get_settings()
        chroma_dir = settings.data_dir / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(chroma_dir))
        coll = client.get_or_create_collection(
            _COLLECTION, metadata={"hnsw:space": "cosine"}
        )

        corpus = load_bundled_corpus()
        if coll.count() < len(corpus):
            coll.upsert(
                ids=[d["id"] for d in corpus],
                documents=[_doc_text(d) for d in corpus],
                metadatas=[_metadata(d) for d in corpus],
            )
            log.info("GovIntel corpus indexed: %d documents", len(corpus))
        _collection = coll
        return _collection


def upsert_docs(docs: list[dict]) -> int:
    """Add/update documents (e.g. freshly fetched live feed items) in the index."""
    if not docs or not semantic_enabled():
        return 0
    coll = _ensure_collection()
    coll.upsert(
        ids=[d["id"] for d in docs],
        documents=[_doc_text(d) for d in docs],
        metadatas=[_metadata(d) for d in docs],
    )
    return len(docs)


def _build_where(filters: dict | None) -> dict | None:
    """Translate flat filters into a ChromaDB `where` clause."""
    if not filters:
        return None
    clauses = [{k: {"$eq": v}} for k, v in filters.items() if v]
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _hit(meta: dict, _id: str, dist: float | None) -> dict:
    score = round(max(0.0, 1.0 - float(dist)), 4) if dist is not None else None
    return {
        "id": _id,
        "title": meta.get("title"),
        "doc_type": meta.get("doc_type"),
        "department": meta.get("department"),
        "ministry": meta.get("ministry"),
        "region": meta.get("region"),
        "date": meta.get("date"),
        "summary": meta.get("summary"),
        "source_url": meta.get("source_url"),
        "language": meta.get("language"),
        "keywords": meta.get("keywords"),
        "origin": meta.get("origin"),
        "score": score,
    }


def retrieve(query: str, k: int = 12, filters: dict | None = None) -> list[dict]:
    """Top-k semantically relevant gov documents, with optional metadata filters."""
    coll = _ensure_collection()
    res = coll.query(query_texts=[query], n_results=k, where=_build_where(filters))
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    ids = res.get("ids", [[]])[0]
    # zip order must match _hit(meta, _id, dist). Zipping dists before ids bound
    # the distance to _id and the id to dist, so every semantic search raised
    # ValueError: could not convert string to float -> HTTP 500.
    return [_hit(m, i, d) for m, i, d in zip(metas, ids, dists)]


def list_all(filters: dict | None = None, limit: int = 200) -> list[dict]:
    """Return documents matching filters without a semantic query (browse mode)."""
    coll = _ensure_collection()
    res = coll.get(where=_build_where(filters), limit=limit)
    metas = res.get("metadatas", []) or []
    ids = res.get("ids", []) or []
    out = [_hit(m, i, None) for m, i in zip(metas, ids)]
    # newest first
    out.sort(key=lambda d: d.get("date") or "", reverse=True)
    return out


def get_doc(doc_id: str) -> dict | None:
    coll = _ensure_collection()
    res = coll.get(ids=[doc_id])
    metas = res.get("metadatas", []) or []
    ids = res.get("ids", []) or []
    if not ids:
        return None
    return _hit(metas[0], ids[0], None)


def corpus_size() -> int:
    if not semantic_enabled():
        return 0
    try:
        return _ensure_collection().count()
    except Exception:
        return 0
