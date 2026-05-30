"""Embedding layer — CLIP ViT-B/32 via HuggingFace transformers.

Produces L2-normalized 512-dim vectors so that inner-product search in FAISS
(IndexFlatIP) is equivalent to cosine similarity. The model loads lazily on
first use and is cached as a process-wide singleton, so importing this module
is cheap (important for fast API startup and for environments where CLIP may
not be needed in a given run).
"""
from __future__ import annotations

import threading
from typing import List, Union

import numpy as np
from PIL import Image

from ..config import get_settings

_lock = threading.Lock()
_model = None
_processor = None
_device = None


def _ensure_loaded() -> None:
    global _model, _processor, _device
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        import torch
        from transformers import CLIPModel, CLIPProcessor

        settings = get_settings()
        _device = settings.resolve_device()
        model = CLIPModel.from_pretrained(settings.clip_model_name)
        model.to(_device)
        model.eval()
        _processor = CLIPProcessor.from_pretrained(settings.clip_model_name)
        _model = model


def is_loaded() -> bool:
    return _model is not None


def warmup() -> None:
    """Eagerly load CLIP so the first real query/ingest isn't blocked on it."""
    _ensure_loaded()


def _normalize(vecs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1e-12
    return (vecs / norms).astype("float32")


def embed_images(images: Union[Image.Image, List[Image.Image]]) -> np.ndarray:
    """Embed one or more PIL RGB images. Returns (N, 512) float32, normalized."""
    _ensure_loaded()
    import torch

    if isinstance(images, Image.Image):
        images = [images]

    with torch.no_grad():
        inputs = _processor(images=images, return_tensors="pt").to(_device)
        feats = _model.get_image_features(**inputs)
    return _normalize(feats.cpu().numpy())


def embed_text(texts: Union[str, List[str]]) -> np.ndarray:
    """Embed one or more text queries. Returns (N, 512) float32, normalized."""
    _ensure_loaded()
    import torch

    if isinstance(texts, str):
        texts = [texts]

    with torch.no_grad():
        inputs = _processor(
            text=texts, return_tensors="pt", padding=True, truncation=True
        ).to(_device)
        feats = _model.get_text_features(**inputs)
    return _normalize(feats.cpu().numpy())
