"""Vector search layer — FAISS IndexFlatIP wrapped in IndexIDMap2.

Two independent indexes are maintained:
  * CLIP index  (512-dim) — semantic frame search (text & reference-image)
  * Face index  (512-dim) — ArcFace suspect matching

IndexFlatIP gives exact inner-product (== cosine on normalized vectors) search,
which is the right call for forensic work: no approximation, fully explainable
scores. We wrap it in IndexIDMap2 so each vector carries an explicit, stable id
that we map back to a DB frame/face row — and so a video's vectors can be
removed cleanly when a case is deleted.

Indexes are persisted to disk and reloaded on startup, supporting the offline
field-deployment requirement (process the footage once, search repeatedly).
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import faiss
import numpy as np


class IndexManager:
    def __init__(self, path: Path, dim: int):
        self.path = path
        self.dim = dim
        self._lock = threading.Lock()
        self._index: Optional[faiss.IndexIDMap2] = None
        self._counter_path = path.with_suffix(".counter")
        self._next_id = 0
        self._load()

    # ---------- persistence ----------
    def _new_index(self) -> faiss.IndexIDMap2:
        return faiss.IndexIDMap2(faiss.IndexFlatIP(self.dim))

    def _load(self) -> None:
        if self.path.exists():
            self._index = faiss.read_index(str(self.path))
        else:
            self._index = self._new_index()
        if self._counter_path.exists():
            self._next_id = int(self._counter_path.read_text().strip() or "0")

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self._index, str(self.path))
            self._counter_path.write_text(str(self._next_id))

    # ---------- mutations ----------
    def add(self, vectors: np.ndarray) -> list[int]:
        """Add (N, dim) normalized float32 vectors. Returns the assigned ids."""
        vectors = np.ascontiguousarray(vectors.astype("float32"))
        n = vectors.shape[0]
        with self._lock:
            ids = np.arange(self._next_id, self._next_id + n, dtype="int64")
            self._index.add_with_ids(vectors, ids)
            self._next_id += n
        return ids.tolist()

    def remove(self, ids: list[int]) -> None:
        if not ids:
            return
        with self._lock:
            self._index.remove_ids(np.array(ids, dtype="int64"))

    # ---------- search ----------
    def search(self, query: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        """Return [(faiss_id, score), ...] sorted by descending score."""
        if self._index.ntotal == 0:
            return []
        query = np.ascontiguousarray(query.astype("float32")).reshape(1, -1)
        k = min(top_k, self._index.ntotal)
        scores, ids = self._index.search(query, k)
        out: list[tuple[int, float]] = []
        for fid, score in zip(ids[0], scores[0]):
            if fid == -1:
                continue
            out.append((int(fid), float(score)))
        return out

    @property
    def ntotal(self) -> int:
        return self._index.ntotal if self._index is not None else 0


# ---- Process-wide singletons ----
_clip_index: Optional[IndexManager] = None
_face_index: Optional[IndexManager] = None
_init_lock = threading.Lock()


def get_clip_index() -> IndexManager:
    global _clip_index
    if _clip_index is None:
        with _init_lock:
            if _clip_index is None:
                from ..config import get_settings

                s = get_settings()
                _clip_index = IndexManager(s.clip_index_path, s.clip_embed_dim)
    return _clip_index


def get_face_index() -> IndexManager:
    global _face_index
    if _face_index is None:
        with _init_lock:
            if _face_index is None:
                from ..config import get_settings

                s = get_settings()
                _face_index = IndexManager(s.face_index_path, s.face_embed_dim)
    return _face_index
