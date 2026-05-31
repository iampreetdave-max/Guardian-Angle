"""Query layer — the unified router (layer 4).

Routes a query to the right backend and returns ranked, frame-level hits with
metadata resolved from SQLite:
  * text   : CLIP text embedding -> CLIP FAISS index
  * image  : CLIP image embedding (reference frame) -> CLIP FAISS index
  * face   : ArcFace embedding (suspect photo) -> face FAISS index -> frames
  * object : SQL filter over YOLO detections by label + confidence

All paths return the same SearchHit shape so the API and UI stay uniform.
Optional camera_id / video_id filters scope the search to a feed or case.
"""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from PIL import Image

from ..config import get_settings
from ..database import get_conn
from ..schemas import BBox, DetectionOut, EventFrame, SearchHit
from . import detection, embedding
from .index import get_clip_index, get_face_index, get_object_index
from .ingestion import format_timestamp


# Over-fetch from FAISS so post-filtering by camera/video still yields top_k.
_OVERFETCH = 6


def _group_into_events(hits: list[SearchHit], top_k: int) -> list[SearchHit]:
    """Collapse frames from the same camera that occur within event_gap_sec of
    each other into a single event, represented by the highest-scoring frame.

    Investigators care about *distinct moments*, not the 40 near-identical
    frames of a person loitering. Each returned hit carries event_count and the
    event's time span; events are ranked by their best frame's score.
    """
    if not hits:
        return []
    gap = get_settings().event_gap_sec

    # cluster within each video by temporal proximity
    by_video: dict[int, list[SearchHit]] = {}
    for h in hits:
        by_video.setdefault(h.video_id, []).append(h)

    events: list[SearchHit] = []
    for vhits in by_video.values():
        vhits.sort(key=lambda h: h.timestamp_sec)
        cluster: list[SearchHit] = [vhits[0]]
        for h in vhits[1:]:
            if h.timestamp_sec - cluster[-1].timestamp_sec <= gap:
                cluster.append(h)
            else:
                events.append(_event_from_cluster(cluster))
                cluster = [h]
        events.append(_event_from_cluster(cluster))

    events.sort(key=lambda h: h.score, reverse=True)
    return events[:top_k]


def _event_from_cluster(cluster: list[SearchHit]) -> SearchHit:
    best = max(cluster, key=lambda h: h.score)
    start = min(h.timestamp_sec for h in cluster)
    end = max(h.timestamp_sec for h in cluster)
    best.event_count = len(cluster)
    best.event_start_hms = format_timestamp(start)
    best.event_end_hms = format_timestamp(end)
    # Carry every frame of the event (chronological) so the UI can show all the
    # instances behind the count, not just the representative frame.
    if len(cluster) > 1:
        best.event_frames = [
            EventFrame(
                frame_id=h.frame_id,
                timestamp_sec=h.timestamp_sec,
                timestamp_hms=h.timestamp_hms,
                thumbnail_url=h.thumbnail_url,
                score=h.score,
            )
            for h in sorted(cluster, key=lambda h: h.timestamp_sec)
        ]
    return best


def _attach_detections(conn, frame_id: int) -> list[DetectionOut]:
    rows = conn.execute(
        "SELECT label, confidence, x1, y1, x2, y2 FROM detections "
        "WHERE frame_id = ? ORDER BY confidence DESC",
        (frame_id,),
    ).fetchall()
    return [
        DetectionOut(
            label=r["label"],
            confidence=r["confidence"],
            bbox=BBox(x1=r["x1"], y1=r["y1"], x2=r["x2"], y2=r["y2"]),
        )
        for r in rows
    ]


def _frame_row_to_hit(conn, frame_row, score: float, query_type: str) -> SearchHit:
    return SearchHit(
        frame_id=frame_row["frame_id"],
        video_id=frame_row["video_id"],
        camera_id=frame_row["camera_id"],
        filename=frame_row["filename"],
        timestamp_sec=frame_row["timestamp_sec"],
        timestamp_hms=format_timestamp(frame_row["timestamp_sec"]),
        thumbnail_url=f"/thumbnails/{frame_row['thumbnail_path']}",
        score=round(float(score), 4),
        query_type=query_type,  # type: ignore[arg-type]
        detections=_attach_detections(conn, frame_row["frame_id"]),
    )


def _resolve_clip_hits(
    faiss_hits: list[tuple[int, float]],
    query_type: str,
    camera_id: Optional[str],
    video_id: Optional[int],
) -> list[SearchHit]:
    """Resolve all FAISS hits to SearchHits (sorted by score, not truncated —
    truncation/grouping happens in the caller)."""
    if not faiss_hits:
        return []
    id_to_score = {fid: score for fid, score in faiss_hits}
    placeholders = ",".join("?" for _ in id_to_score)
    sql = (
        "SELECT f.id AS frame_id, f.video_id, f.timestamp_sec, f.thumbnail_path, "
        "f.clip_faiss_id, v.camera_id, v.filename "
        "FROM frames f JOIN videos v ON v.id = f.video_id "
        f"WHERE f.clip_faiss_id IN ({placeholders})"
    )
    params: list = list(id_to_score.keys())
    if camera_id:
        sql += " AND v.camera_id = ?"
        params.append(camera_id)
    if video_id:
        sql += " AND f.video_id = ?"
        params.append(video_id)

    hits: list[SearchHit] = []
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        for r in rows:
            score = id_to_score.get(r["clip_faiss_id"], 0.0)
            hits.append(_frame_row_to_hit(conn, r, score, query_type))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits


def _filter_relevance(
    hits: list[SearchHit], min_score: float, rel_ratio: float = 0.0
) -> list[SearchHit]:
    """Drop frames that aren't real matches. Two complementary cutoffs:
      * absolute floor (min_score) — kills CLIP's noise floor for image/face;
      * relative floor (rel_ratio * best_score) — for compressed CLIP text
        scores, trims the long tail that drops well below the top match while
        keeping a cluster of similarly-strong hits.
    The effective floor is the max of the two, so an all-noise query (low top
    score) still returns nothing rather than a wall of near-ties.
    """
    if not hits or (min_score <= 0 and rel_ratio <= 0):
        return hits
    top = max(h.score for h in hits)
    floor = max(min_score, top * rel_ratio)
    return [h for h in hits if h.score >= floor]


def _finalize(
    hits: list[SearchHit], top_k: int, group: bool,
    min_score: float = 0.0, rel_ratio: float = 0.0,
) -> list[SearchHit]:
    """Apply the relevance floor, then either group into events (default) or
    return the top_k raw frames."""
    hits = _filter_relevance(hits, min_score, rel_ratio)
    if group:
        return _group_into_events(hits, top_k)
    return hits[:top_k]


def search_text(
    query: str,
    top_k: int,
    camera_id: Optional[str] = None,
    video_id: Optional[int] = None,
    group: bool = True,
) -> list[SearchHit]:
    vec = embedding.embed_text(query)[0]
    faiss_hits = get_clip_index().search(vec, top_k * _OVERFETCH)
    hits = _resolve_clip_hits(faiss_hits, "text", camera_id, video_id)
    s = get_settings()
    return _finalize(hits, top_k, group, s.text_min_score, s.text_rel_ratio)


def search_image(
    image_bgr: np.ndarray,
    top_k: int,
    camera_id: Optional[str] = None,
    video_id: Optional[int] = None,
    group: bool = True,
) -> list[SearchHit]:
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    vec = embedding.embed_images(Image.fromarray(rgb))[0]
    faiss_hits = get_clip_index().search(vec, top_k * _OVERFETCH)
    hits = _resolve_clip_hits(faiss_hits, "image", camera_id, video_id)
    return _finalize(hits, top_k, group, get_settings().image_min_score)


def search_face(
    image_bgr: np.ndarray,
    top_k: int,
    camera_id: Optional[str] = None,
    video_id: Optional[int] = None,
    group: bool = True,
) -> list[SearchHit]:
    ref = detection.embed_reference_face(image_bgr)
    if ref is None:
        return []
    faiss_hits = get_face_index().search(ref, top_k * _OVERFETCH)
    if not faiss_hits:
        return []

    # face faiss id -> best score per frame (a frame may hold several faces)
    id_to_score = {fid: score for fid, score in faiss_hits}
    placeholders = ",".join("?" for _ in id_to_score)
    sql = (
        "SELECT fa.face_faiss_id, f.id AS frame_id, f.video_id, f.timestamp_sec, "
        "f.thumbnail_path, v.camera_id, v.filename "
        "FROM faces fa JOIN frames f ON f.id = fa.frame_id "
        "JOIN videos v ON v.id = f.video_id "
        f"WHERE fa.face_faiss_id IN ({placeholders})"
    )
    params: list = list(id_to_score.keys())
    if camera_id:
        sql += " AND v.camera_id = ?"
        params.append(camera_id)
    if video_id:
        sql += " AND f.video_id = ?"
        params.append(video_id)

    best_per_frame: dict[int, SearchHit] = {}
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        for r in rows:
            score = id_to_score.get(r["face_faiss_id"], 0.0)
            fid = r["frame_id"]
            if fid in best_per_frame and best_per_frame[fid].score >= score:
                continue
            best_per_frame[fid] = _frame_row_to_hit(conn, r, score, "face")
    hits = sorted(best_per_frame.values(), key=lambda h: h.score, reverse=True)
    return _finalize(hits, top_k, group, get_settings().face_min_score)


def search_regions(
    query: str,
    top_k: int,
    camera_id: Optional[str] = None,
    video_id: Optional[int] = None,
    label: Optional[str] = None,
) -> list[SearchHit]:
    """Instance-level search: match the query against individual detected-object
    crops (not whole frames), so 'red car' returns every matching car as its own
    hit with the specific bounding box. This is what makes 'find all 5 red cars'
    work where whole-frame CLIP would surface only the most prominent one."""
    vec = embedding.embed_text(query)[0]
    faiss_hits = get_object_index().search(vec, top_k * _OVERFETCH)
    if not faiss_hits:
        return []
    id_to_score = {fid: score for fid, score in faiss_hits}
    placeholders = ",".join("?" for _ in id_to_score)
    sql = (
        "SELECT d.obj_faiss_id, d.label, d.x1, d.y1, d.x2, d.y2, "
        "f.id AS frame_id, f.video_id, f.timestamp_sec, f.thumbnail_path, "
        "v.camera_id, v.filename "
        "FROM detections d JOIN frames f ON f.id = d.frame_id "
        "JOIN videos v ON v.id = f.video_id "
        f"WHERE d.obj_faiss_id IN ({placeholders})"
    )
    params: list = list(id_to_score.keys())
    if camera_id:
        sql += " AND v.camera_id = ?"
        params.append(camera_id)
    if video_id:
        sql += " AND f.video_id = ?"
        params.append(video_id)
    if label:
        sql += " AND d.label = ?"
        params.append(label.lower())

    hits: list[SearchHit] = []
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        for r in rows:
            score = id_to_score.get(r["obj_faiss_id"], 0.0)
            hit = _frame_row_to_hit(conn, r, score, "object")
            hit.match_label = r["label"]
            hit.match_bbox = BBox(x1=r["x1"], y1=r["y1"], x2=r["x2"], y2=r["y2"])
            hits.append(hit)
    # one hit per object instance, ranked by similarity (no temporal grouping —
    # the whole point is to surface every instance). Apply the relevance floor
    # so weak crops don't pad the list.
    hits.sort(key=lambda h: h.score, reverse=True)
    s = get_settings()
    hits = _filter_relevance(hits, s.region_min_score, s.region_rel_ratio)
    return hits[:top_k]


def search_object(
    label: str,
    top_k: int,
    min_confidence: float,
    camera_id: Optional[str] = None,
    video_id: Optional[int] = None,
    group: bool = True,
) -> list[SearchHit]:
    sql = (
        "SELECT f.id AS frame_id, f.video_id, f.timestamp_sec, f.thumbnail_path, "
        "v.camera_id, v.filename, MAX(d.confidence) AS best "
        "FROM detections d JOIN frames f ON f.id = d.frame_id "
        "JOIN videos v ON v.id = f.video_id "
        "WHERE d.label = ? AND d.confidence >= ?"
    )
    params: list = [label.lower(), min_confidence]
    if camera_id:
        sql += " AND v.camera_id = ?"
        params.append(camera_id)
    if video_id:
        sql += " AND f.video_id = ?"
        params.append(video_id)
    # over-fetch frames so temporal grouping has material to collapse
    sql += " GROUP BY f.id ORDER BY best DESC LIMIT ?"
    params.append(top_k * _OVERFETCH)

    hits: list[SearchHit] = []
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        for r in rows:
            hits.append(_frame_row_to_hit(conn, r, r["best"], "object"))
    return _finalize(hits, top_k, group)
