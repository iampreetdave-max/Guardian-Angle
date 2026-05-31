"""REST API routes for VisionScan."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import Response

from ..config import get_settings
from ..platform.security import auth_gate
from ..core import detection, embedding
from ..core import query_router as qr
from ..core.index import get_clip_index, get_face_index
from ..database import get_conn
from ..feeds import load_feeds
from ..schemas import (
    HealthOut,
    ObjectQueryIn,
    PublicFeed,
    RegionQueryIn,
    ReportRequest,
    SearchResponse,
    StreamIn,
    TextQueryIn,
    VideoOut,
)
from ..core.index import get_object_index
from ..services import report as report_svc
from ..services import stream as stream_svc
from ..services.pipeline import process_video
from ..services.stream import process_stream, start_live, stop_live

router = APIRouter()

_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


# ------------------------------------------------------------------ system
@router.get("/health", response_model=HealthOut, tags=["system"])
def health() -> HealthOut:
    settings = get_settings()
    with get_conn() as conn:
        n_videos = conn.execute("SELECT COUNT(*) c FROM videos").fetchone()["c"]
    return HealthOut(
        status="ok",
        device=settings.resolve_device(),
        models={
            "clip": embedding.is_loaded(),
            "yolo": detection.yolo_available(),
            "face": detection.face_available(),
        },
        videos=n_videos,
        indexed_frames=get_clip_index().ntotal,
    )


# ------------------------------------------------------------------ videos
@router.post("/videos", response_model=VideoOut, tags=["videos"])
async def upload_video(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    camera_id: str = Form("CAM-1"),
    _user: dict | None = Depends(auth_gate),
) -> VideoOut:
    settings = get_settings()
    ext = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in _VIDEO_EXTS:
        raise HTTPException(400, f"Unsupported video type: {ext}")

    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = settings.videos_dir / stored_name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO videos (filename, path, camera_id, status) "
            "VALUES (?, ?, ?, 'pending')",
            (file.filename, str(dest), camera_id),
        )
        video_id = cur.lastrowid

    # kick off processing in the background so the request returns immediately
    background.add_task(process_video, video_id)
    return _video_out(video_id)


@router.get("/feeds", response_model=list[PublicFeed], tags=["videos"])
def list_public_feeds() -> list[PublicFeed]:
    """Bundled catalog of intentionally-public, click-to-load live feeds."""
    return [PublicFeed(**f) for f in load_feeds()]


@router.post("/streams", response_model=VideoOut, tags=["videos"])
def ingest_stream(
    body: StreamIn, background: BackgroundTasks,
    _user: dict | None = Depends(auth_gate),
) -> VideoOut:
    """Capture a bounded window from a public live stream and analyze it.

    Use only with intentionally-public feeds (e.g. government traffic cameras,
    public YouTube-live street cams). The stream URL is stored as the feed's
    'path' and processed exactly like an uploaded video.
    """
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO videos (filename, path, camera_id, status) "
            "VALUES (?, ?, ?, 'pending')",
            (f"[live] {body.url[:80]}", body.url, body.camera_id),
        )
        video_id = cur.lastrowid

    background.add_task(
        process_stream, video_id, body.url, body.duration_sec, body.max_frames
    )
    return _video_out(video_id)


@router.post("/streams/live", response_model=VideoOut, tags=["videos"])
def start_live_feed(body: StreamIn, _user: dict | None = Depends(auth_gate)) -> VideoOut:
    """Start a continuous LIVE monitoring session on a public feed: the stream
    is watched and indexed in real time until stopped, so it can be viewed and
    searched live. Use only with intentionally-public feeds."""
    video_id = start_live(body.url, body.camera_id)
    return _video_out(video_id)


@router.post("/videos/{video_id}/stop", response_model=VideoOut, tags=["videos"])
def stop_live_feed(video_id: int, _user: dict | None = Depends(auth_gate)) -> VideoOut:
    """Stop a running live session (finalizes the feed as a searchable video)."""
    stop_live(video_id)
    return _video_out(video_id)


@router.get("/videos", response_model=list[VideoOut], tags=["videos"])
def list_videos(_user: dict | None = Depends(auth_gate)) -> list[VideoOut]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM videos ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_video(r) for r in rows]


@router.get("/videos/{video_id}", response_model=VideoOut, tags=["videos"])
def get_video(video_id: int, _user: dict | None = Depends(auth_gate)) -> VideoOut:
    return _video_out(video_id)


@router.delete("/videos/{video_id}", tags=["videos"])
def delete_video(video_id: int, _user: dict | None = Depends(auth_gate)) -> dict:
    settings = get_settings()
    with get_conn() as conn:
        vid = conn.execute(
            "SELECT path FROM videos WHERE id = ?", (video_id,)
        ).fetchone()
        if vid is None:
            raise HTTPException(404, "Video not found")

        clip_ids = [
            r["clip_faiss_id"]
            for r in conn.execute(
                "SELECT clip_faiss_id FROM frames WHERE video_id = ? "
                "AND clip_faiss_id IS NOT NULL",
                (video_id,),
            ).fetchall()
        ]
        face_ids = [
            r["face_faiss_id"]
            for r in conn.execute(
                "SELECT fa.face_faiss_id FROM faces fa "
                "JOIN frames f ON f.id = fa.frame_id "
                "WHERE f.video_id = ? AND fa.face_faiss_id IS NOT NULL",
                (video_id,),
            ).fetchall()
        ]
        obj_ids = [
            r["obj_faiss_id"]
            for r in conn.execute(
                "SELECT d.obj_faiss_id FROM detections d "
                "JOIN frames f ON f.id = d.frame_id "
                "WHERE f.video_id = ? AND d.obj_faiss_id IS NOT NULL",
                (video_id,),
            ).fetchall()
        ]
        conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))

    get_clip_index().remove(clip_ids)
    get_clip_index().save()
    get_face_index().remove(face_ids)
    get_face_index().save()
    get_object_index().remove(obj_ids)
    get_object_index().save()

    # remove stored files (videos.path is stored as an absolute path)
    try:
        Path(vid["path"]).unlink(missing_ok=True)
    except Exception:
        pass
    shutil.rmtree(settings.thumbnails_dir / str(video_id), ignore_errors=True)
    return {"deleted": video_id}


@router.post("/reindex", tags=["videos"])
def reindex_objects(background: BackgroundTasks, _user: dict | None = Depends(auth_gate)) -> dict:
    """Backfill region-level (object-crop) embeddings for footage processed
    before this feature existed, by re-running the pipeline on file-based
    videos. Live/stream feeds (no re-readable source) are skipped."""
    from ..services.pipeline import reindex_video

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, path FROM videos WHERE status = 'ready'"
        ).fetchall()
    targets = [
        r["id"] for r in rows
        if isinstance(r["path"], str)
        and r["path"].split("://", 1)[0] not in ("http", "https", "rtsp", "rtmp")
        and Path(r["path"]).exists()
    ]
    for vid in targets:
        background.add_task(reindex_video, vid)
    return {"reindexing": targets, "count": len(targets)}


# ------------------------------------------------------------------ search
@router.post("/search/text", response_model=SearchResponse, tags=["search"])
def search_text(body: TextQueryIn, _user: dict | None = Depends(auth_gate)) -> SearchResponse:
    hits = qr.search_text(
        body.query, body.top_k, body.camera_id, body.video_id, body.group_events
    )
    return SearchResponse(
        query=body.query, query_type="text", count=len(hits), hits=hits
    )


@router.post("/search/region", response_model=SearchResponse, tags=["search"])
def search_region(body: RegionQueryIn, _user: dict | None = Depends(auth_gate)) -> SearchResponse:
    """Instance-level search: returns every matching detected object (e.g. all
    five red cars) as its own hit with its bounding box."""
    hits = qr.search_regions(
        body.query, body.top_k, body.camera_id, body.video_id, body.label
    )
    return SearchResponse(
        query=body.query, query_type="object", count=len(hits), hits=hits
    )


@router.post("/search/object", response_model=SearchResponse, tags=["search"])
def search_object(body: ObjectQueryIn, _user: dict | None = Depends(auth_gate)) -> SearchResponse:
    hits = qr.search_object(
        body.label, body.top_k, body.min_confidence, body.camera_id,
        body.video_id, body.group_events,
    )
    return SearchResponse(
        query=body.label, query_type="object", count=len(hits), hits=hits
    )


@router.post("/search/image", response_model=SearchResponse, tags=["search"])
async def search_image(
    file: UploadFile = File(...),
    top_k: int = Form(30),
    camera_id: Optional[str] = Form(None),
    video_id: Optional[int] = Form(None),
    group_events: bool = Form(True),
    _user: dict | None = Depends(auth_gate),
) -> SearchResponse:
    frame = _decode_upload(await file.read())
    hits = qr.search_image(frame, top_k, camera_id, video_id, group_events)
    return SearchResponse(
        query=f"[image:{file.filename}]", query_type="image",
        count=len(hits), hits=hits,
    )


@router.post("/search/face", response_model=SearchResponse, tags=["search"])
async def search_face(
    file: UploadFile = File(...),
    top_k: int = Form(30),
    camera_id: Optional[str] = Form(None),
    video_id: Optional[int] = Form(None),
    group_events: bool = Form(True),
    _user: dict | None = Depends(auth_gate),
) -> SearchResponse:
    if not detection.face_available():
        raise HTTPException(503, "Face recognition model is not available")
    frame = _decode_upload(await file.read())
    hits = qr.search_face(frame, top_k, camera_id, video_id, group_events)
    return SearchResponse(
        query=f"[face:{file.filename}]", query_type="face",
        count=len(hits), hits=hits,
    )


# ------------------------------------------------------------------ report
@router.post("/report", tags=["report"])
def generate_report(body: ReportRequest, _user: dict | None = Depends(auth_gate)) -> Response:
    if not body.frame_ids:
        raise HTTPException(400, "No frames provided for the report")
    pdf = report_svc.build_report(
        case_title=body.case_title,
        investigator=body.investigator,
        query=body.query,
        query_type=body.query_type,
        frame_ids=body.frame_ids,
    )
    headers = {"Content-Disposition": 'attachment; filename="visionscan_report.pdf"'}
    return Response(content=pdf, media_type="application/pdf", headers=headers)


# ------------------------------------------------------------------ helpers
def _decode_upload(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Could not decode uploaded image")
    return img


def _row_to_video(r) -> VideoOut:
    path = r["path"]
    is_stream = isinstance(path, str) and path.split("://", 1)[0] in (
        "http", "https", "rtsp", "rtmp"
    )
    return VideoOut(
        id=r["id"], filename=r["filename"], camera_id=r["camera_id"],
        fps=r["fps"], duration_sec=r["duration_sec"], frame_count=r["frame_count"],
        keyframe_count=r["keyframe_count"], status=r["status"], error=r["error"],
        created_at=r["created_at"],
        stream_url=path if is_stream else None,
        is_live=stream_svc.is_live(r["id"]),
    )


def _video_out(video_id: int) -> VideoOut:
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
    if r is None:
        raise HTTPException(404, "Video not found")
    return _row_to_video(r)
