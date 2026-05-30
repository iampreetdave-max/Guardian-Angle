"""Pydantic request/response models — the API contract."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------- Videos ----------
class VideoOut(BaseModel):
    id: int
    filename: str
    camera_id: str
    fps: Optional[float] = None
    duration_sec: Optional[float] = None
    frame_count: Optional[int] = None
    keyframe_count: int = 0
    status: str
    error: Optional[str] = None
    created_at: str
    # For live/stream feeds: the source URL so the UI can show a live preview.
    stream_url: Optional[str] = None
    is_live: bool = False


class PublicFeed(BaseModel):
    id: str
    name: str
    location: str
    category: str = "Public"
    url: str
    note: str = ""
    verified: bool = False


class StreamIn(BaseModel):
    url: str = Field(..., description="Public stream URL (RTSP/HLS/MJPEG or YouTube-live)")
    camera_id: str = Field("STREAM-1", description="Label for this feed")
    duration_sec: float = Field(30.0, ge=5.0, le=600.0,
                                description="How long to capture from the live feed")
    max_frames: Optional[int] = Field(
        None, ge=1, le=2000, description="Optional cap on kept keyframes")


# ---------- Detections / faces attached to a frame ----------
class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DetectionOut(BaseModel):
    label: str
    confidence: float
    bbox: BBox


# ---------- Search ----------
QueryType = Literal["text", "image", "object", "face"]


class TextQueryIn(BaseModel):
    query: str = Field(..., description="Natural-language description to search for")
    top_k: int = Field(30, ge=1, le=200)
    camera_id: Optional[str] = Field(None, description="Restrict to one camera")
    video_id: Optional[int] = None
    group_events: bool = Field(True, description="Collapse nearby frames into events")


class ObjectQueryIn(BaseModel):
    label: str = Field(..., description="YOLO class name, e.g. 'car', 'person'")
    top_k: int = Field(30, ge=1, le=200)
    min_confidence: float = Field(0.35, ge=0.0, le=1.0)
    camera_id: Optional[str] = None
    video_id: Optional[int] = None
    group_events: bool = Field(True, description="Collapse nearby frames into events")


class SearchHit(BaseModel):
    frame_id: int
    video_id: int
    camera_id: str
    filename: str
    timestamp_sec: float
    timestamp_hms: str
    thumbnail_url: str
    score: float = Field(..., description="Similarity / confidence, 0-1")
    query_type: QueryType
    detections: list[DetectionOut] = []
    # Event grouping: when on, this hit is the best frame of a temporal event.
    event_count: int = Field(1, description="Frames collapsed into this event")
    event_start_hms: Optional[str] = None
    event_end_hms: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    query_type: QueryType
    count: int
    hits: list[SearchHit]


# ---------- Reports ----------
class ReportRequest(BaseModel):
    case_title: str = "VisionScan Investigation Report"
    investigator: str = ""
    query: str = ""
    query_type: QueryType = "text"
    frame_ids: list[int] = Field(..., description="Frames to include, in order")


# ---------- System ----------
class HealthOut(BaseModel):
    status: str
    device: str
    models: dict[str, bool]
    videos: int
    indexed_frames: int
