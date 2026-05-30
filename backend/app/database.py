"""SQLite metadata store for VisionScan.

We use plain sqlite3 (no ORM) for zero-dependency, offline-friendly operation.
The DB holds video records, extracted keyframes, object detections, and faces.
Vector data itself lives in FAISS; the DB stores the faiss_id <-> frame mapping.

Tables
------
videos      : one row per ingested video / camera feed
frames      : one row per extracted keyframe (with its CLIP faiss_id)
detections  : YOLO object detections, many per frame
faces       : InsightFace detections, many per frame (with face faiss_id)
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename      TEXT NOT NULL,
    path          TEXT NOT NULL,
    camera_id     TEXT NOT NULL DEFAULT 'CAM-1',
    fps           REAL,
    duration_sec  REAL,
    frame_count   INTEGER,
    keyframe_count INTEGER DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'pending',  -- pending|processing|ready|error
    error         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS frames (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id       INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    frame_number   INTEGER NOT NULL,
    timestamp_sec  REAL NOT NULL,
    thumbnail_path TEXT NOT NULL,
    clip_faiss_id  INTEGER,                  -- row in the CLIP FAISS index
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_frames_video ON frames(video_id);
CREATE INDEX IF NOT EXISTS idx_frames_clip ON frames(clip_faiss_id);

CREATE TABLE IF NOT EXISTS detections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id    INTEGER NOT NULL REFERENCES frames(id) ON DELETE CASCADE,
    label       TEXT NOT NULL,
    confidence  REAL NOT NULL,
    x1 REAL, y1 REAL, x2 REAL, y2 REAL,
    obj_faiss_id INTEGER                        -- row in the object-crop CLIP index
);
CREATE INDEX IF NOT EXISTS idx_det_frame ON detections(frame_id);
CREATE INDEX IF NOT EXISTS idx_det_label ON detections(label);
-- idx_det_obj is created in _migrate(), after the column is guaranteed to exist
-- (older DBs created the table without obj_faiss_id).

CREATE TABLE IF NOT EXISTS faces (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id      INTEGER NOT NULL REFERENCES frames(id) ON DELETE CASCADE,
    face_faiss_id INTEGER,                    -- row in the face FAISS index
    det_score     REAL,
    x1 REAL, y1 REAL, x2 REAL, y2 REAL
);
CREATE INDEX IF NOT EXISTS idx_faces_frame ON faces(frame_id);
CREATE INDEX IF NOT EXISTS idx_faces_faiss ON faces(face_faiss_id);
"""


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # better concurrency for bg tasks
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    """Lightweight, idempotent migrations for DBs created by older versions."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(detections)")}
    if "obj_faiss_id" not in cols:
        conn.execute("ALTER TABLE detections ADD COLUMN obj_faiss_id INTEGER")
    # Safe now that the column is guaranteed to exist (fresh + migrated DBs).
    conn.execute("CREATE INDEX IF NOT EXISTS idx_det_obj ON detections(obj_faiss_id)")


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Context-managed connection that commits on success, rolls back on error."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
