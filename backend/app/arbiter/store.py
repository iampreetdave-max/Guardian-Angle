"""Legal corpus vector store — ChromaDB with offline default embeddings.

The IPC / IT Act / CrPC corpus is embedded once into a persistent ChromaDB
collection using Chroma's built-in MiniLM ONNX embedder (no API key, no torch,
fully offline after a one-time ~80MB model download). Retrieval is then instant
and local — the RAG layer for FIR drafting, section lookup, and citizen Q&A.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from ..config import get_settings

log = logging.getLogger("visionscan.arbiter.store")

_CORPUS_PATH = Path(__file__).parent / "corpus" / "legal_corpus.json"
_COLLECTION = "legal_corpus"

_lock = threading.Lock()
_collection = None


def _load_corpus() -> list[dict]:
    return json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))


def _doc_text(entry: dict) -> str:
    return (
        f"{entry['act']} Section {entry['section']}: {entry['title']}. "
        f"{entry['summary']} Punishment: {entry.get('punishment', 'N/A')}. "
        f"Keywords: {', '.join(entry.get('keywords', []))}."
    )


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

        corpus = _load_corpus()
        if coll.count() < len(corpus):
            # (re)build — idempotent upsert of all sections
            coll.upsert(
                ids=[e["id"] for e in corpus],
                documents=[_doc_text(e) for e in corpus],
                metadatas=[
                    {
                        "act": e["act"],
                        "section": e["section"],
                        "title": e["title"],
                        "summary": e["summary"],
                        "punishment": e.get("punishment", ""),
                        "category": e.get("category", ""),
                        "cognizable": str(e.get("cognizable", "")),
                        "bailable": str(e.get("bailable", "")),
                    }
                    for e in corpus
                ],
            )
            log.info("Arbiter corpus indexed: %d sections", len(corpus))
        _collection = coll
        return _collection


def retrieve(query: str, k: int = 5, act: str | None = None) -> list[dict]:
    """Return the top-k most relevant legal sections for a query.
    Each result includes the section metadata and a 0-1 relevance score."""
    coll = _ensure_collection()
    where = {"act": act} if act else None
    res = coll.query(query_texts=[query], n_results=k, where=where)
    out: list[dict] = []
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    ids = res.get("ids", [[]])[0]
    for meta, dist, _id in zip(metas, dists, ids):
        out.append(
            {
                "id": _id,
                "act": meta.get("act"),
                "section": meta.get("section"),
                "title": meta.get("title"),
                "summary": meta.get("summary"),
                "punishment": meta.get("punishment"),
                "category": meta.get("category"),
                "cognizable": meta.get("cognizable"),
                "bailable": meta.get("bailable"),
                # cosine distance -> similarity (0..1)
                "score": round(max(0.0, 1.0 - float(dist)), 4),
                "citation": f"{meta.get('act')} Section {meta.get('section')}",
            }
        )
    return out


def corpus_size() -> int:
    try:
        return _ensure_collection().count()
    except Exception:
        return 0
