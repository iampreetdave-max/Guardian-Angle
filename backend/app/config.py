"""Central configuration for VisionScan.

All paths, model names, and tunable thresholds live here so the rest of the
codebase never hard-codes them. Values can be overridden via environment
variables (prefixed VISIONSCAN_) or a .env file — important for switching
between a dev laptop and a field deployment.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root = backend/  (this file lives in backend/app/config.py)
BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BACKEND_ROOT.parent / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VISIONSCAN_",
        env_file=".env",
        extra="ignore",
    )

    # ---- Storage layout ----
    data_dir: Path = DEFAULT_DATA_DIR
    # Subdirectories are derived from data_dir in the properties below.

    # ---- Device ----
    # "auto" picks cuda if available, else cpu. Override with "cpu"/"cuda".
    device: str = "auto"

    # ---- Embedding layer (CLIP) ----
    clip_model_name: str = "openai/clip-vit-base-patch32"
    clip_embed_dim: int = 512

    # ---- Detection layer ----
    yolo_model_name: str = "yolov8n.pt"          # nano = fast, field-friendly
    yolo_conf_threshold: float = 0.35
    enable_detection: bool = True                 # YOLO object detection
    enable_face: bool = True                      # InsightFace ArcFace
    face_model_name: str = "buffalo_l"
    face_embed_dim: int = 512

    # ---- Ingestion / keyframe sampling ----
    # Adaptive sampler: a frame is kept if EITHER the scene-change (histogram)
    # delta OR the motion delta exceeds its threshold, but never more often
    # than min_frame_interval_sec and at least every max_frame_interval_sec.
    scene_change_threshold: float = 0.45          # histogram correlation drop
    motion_threshold: float = 18.0                # mean abs frame diff
    min_frame_interval_sec: float = 0.5           # don't keep frames faster than this
    max_frame_interval_sec: float = 5.0           # force-keep at least this often
    thumbnail_max_size: int = 480                 # px, longest edge

    # ---- Preprocessing ----
    enable_clahe: bool = True                     # low-light / IR enhancement
    clahe_clip_limit: float = 2.0
    clahe_grid_size: int = 8

    # ---- Query defaults ----
    default_top_k: int = 30
    # Frames from the same camera within this many seconds collapse into one
    # "event" (so an investigator sees distinct moments, not 50 near-identical
    # frames of someone standing still).
    event_gap_sec: float = 6.0

    # ---- Arbiter legal AI ----
    # If set, Arbiter uses Gemini for polished generation; otherwise it falls
    # back to offline, citation-grounded templates. Reads VISIONSCAN_GEMINI_API_KEY
    # or a plain GEMINI_API_KEY (resolved in arbiter/llm.py).
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ---- Server ----
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ---------- Derived paths ----------
    @property
    def videos_dir(self) -> Path:
        return self.data_dir / "videos"

    @property
    def thumbnails_dir(self) -> Path:
        return self.data_dir / "thumbnails"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "visionscan.db"

    @property
    def clip_index_path(self) -> Path:
        return self.index_dir / "clip.faiss"

    @property
    def face_index_path(self) -> Path:
        return self.index_dir / "face.faiss"

    @property
    def object_index_path(self) -> Path:
        return self.index_dir / "object_clip.faiss"

    def ensure_dirs(self) -> None:
        for p in (self.videos_dir, self.thumbnails_dir, self.index_dir):
            p.mkdir(parents=True, exist_ok=True)

    def resolve_device(self) -> str:
        if self.device != "auto":
            return self.device
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
