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
    # Minimum relevance (cosine similarity) a frame must clear to be returned,
    # per modality. Without these the search pads to top_k with whatever ranks
    # highest — surfacing CLIP's noise floor (~0.65 for unrelated frames in
    # image-to-image) as bogus "matches". Ranges differ by modality: CLIP
    # image-to-image sits high (~0.6-0.85), CLIP text-to-image much lower
    # (~0.18-0.32), ArcFace face cosine ~0.2-0.7. Tunable via env.
    image_min_score: float = 0.72     # reference-image (CLIP) search
    text_min_score: float = 0.22      # natural-language (CLIP) search
    region_min_score: float = 0.22    # instance / "find every object" search
    face_min_score: float = 0.30      # suspect-face (ArcFace) search
    # CLIP text->image scores are compressed (genuine matches ~0.27, noise
    # ~0.23), so a flat floor can't separate them. For text/region we ALSO drop
    # anything that falls below this fraction of the best score — an adaptive
    # cutoff that trims the long noise tail while keeping a genuine cluster of
    # similar-scoring matches. Image/face keep their absolute floor only.
    text_rel_ratio: float = 0.88
    region_rel_ratio: float = 0.88

    # ---- Anomaly watch (always-on CCTV incident detection) ----
    # Hybrid detector: CLIP zero-shot scene scoring (fire/smoke/accident/
    # weapon/violence prompt ensembles, calibrated against "normal scene"
    # prompts) + YOLO object signals (COCO 'knife'; optional specialized
    # weights). Reuses the embeddings/detections the pipeline already
    # computes, so the per-frame cost is negligible.
    enable_anomaly: bool = True
    # A CLIP class only fires when its similarity beats the best "normal"
    # prompt by at least this margin. Calibrated empirically: anomaly frames
    # land at +0.03..+0.15 margin, normal scenes are negative (see
    # scripts/anomaly_selftest.py). Per-class overrides below.
    anomaly_conf_threshold: float = 0.03
    # Consecutive detections of the same type on the same feed within this
    # window collapse into one event (mirrors event_gap_sec for search).
    anomaly_event_gap_sec: float = 30.0
    # Only events at/above this NORMALIZED confidence (0..1 — CLIP margins are
    # rescaled onto the same scale YOLO confidences use) ping the admins.
    # Applies to live feeds only.
    anomaly_notify_threshold: float = 0.70
    # YOLO 'knife' (COCO) minimum confidence to register a weapon signal.
    anomaly_weapon_yolo_conf: float = 0.40
    # Optional path to a specialized .pt (e.g. a fire/weapon YOLO). Loaded
    # fail-soft: if missing/broken the CLIP layer still covers every class.
    anomaly_specialized_weights: str = ""
    # Per-class margin overrides, env as JSON:
    # VISIONSCAN_ANOMALY_CLASS_THRESHOLDS={"weapon": 0.32}
    anomaly_class_thresholds: dict[str, float] = {}

    # ---- Arbiter legal AI ----
    # If set, Arbiter uses Gemini for polished generation; otherwise it falls
    # back to offline, citation-grounded templates. Reads VISIONSCAN_GEMINI_API_KEY
    # or a plain GEMINI_API_KEY (resolved in arbiter/llm.py).
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ---- GovIntel (Unified Legal & Government Intelligence) ----
    # Bundled curated corpus works fully offline. The optional live layer polls
    # free, keyless government RSS feeds; disable it or tune the timeout here.
    govintel_enable: bool = True            # allow the live RSS feed layer
    govintel_feed_timeout: int = 6          # seconds per feed fetch (best-effort)
    govintel_auto_refresh: bool = False     # opt-in hourly background feed poll

    # ---- Platform auth ----
    # CHANGE in production via VISIONSCAN_JWT_SECRET. Default is dev-only.
    jwt_secret: str = "cityshield-dev-secret-change-me"
    jwt_expire_hours: int = 12
    seed_demo_users: bool = True   # seed admin/officer/citizen accounts on first run
    # Also seed ~20 generic Ahmedabad incidents (public-sourced approximations,
    # see docs/AHMEDABAD_CRIME_DATA.md) so the City Map and analytics demo well.
    seed_demo_data: bool = True
    # When True, the VisionScan + Arbiter API routes also require a valid login
    # token (production). Default False keeps the public, login-less demo working.
    require_auth: bool = False

    # ---- Security protocol ----
    # Login brute-force lockout: this many failures within the window → 429.
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15
    # In-memory per-IP rate limiting (token buckets, no external store).
    enable_rate_limit: bool = True
    rate_limit_default_per_min: int = 120
    rate_limit_login_per_min: int = 10
    rate_limit_upload_per_min: int = 20
    # Upload caps (enforced while streaming, with magic-number sniffing).
    max_video_upload_mb: int = 500
    max_image_upload_mb: int = 15
    # Arbiter prompt-injection guard: hard cap on untrusted text fed to the LLM.
    arbiter_max_input_chars: int = 4000

    def assert_secure(self) -> None:
        """Refuse to run a production (require_auth=True) deployment on the
        well-known dev JWT secret. Dev/demo mode is unaffected."""
        if self.require_auth and self.jwt_secret == "cityshield-dev-secret-change-me":
            raise RuntimeError(
                "VISIONSCAN_REQUIRE_AUTH is enabled but VISIONSCAN_JWT_SECRET "
                "is still the dev default — set a strong secret before "
                "exposing this deployment."
            )

    # ---- Email (hybrid: SMTP if configured, else offline outbox) ----
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@cityshield.local"

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
