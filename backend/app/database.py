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
        # CityShield platform tables (auth, cases, complaints, …)
        from .platform.schema import PLATFORM_SCHEMA

        conn.executescript(PLATFORM_SCHEMA)
        # GovIntel tables (gov document cache, bookmarks, subscriptions)
        from .govintel.schema import GOVINTEL_SCHEMA

        conn.executescript(GOVINTEL_SCHEMA)
        # CrimeGPT tables (unified case data pool, diary, generated documents)
        from .crimegpt.schema import CRIMEGPT_SCHEMA

        conn.executescript(CRIMEGPT_SCHEMA)
        _migrate(conn)
        conn.commit()
    # seed demo accounts on first run (after tables exist)
    try:
        from .config import get_settings
        from .platform.seed import seed_demo

        if get_settings().seed_demo_users:
            seed_demo()
    except Exception:  # pragma: no cover - never block startup on seeding
        import logging
        logging.getLogger("visionscan").warning("demo seeding skipped", exc_info=True)


def _migrate(conn: sqlite3.Connection) -> None:
    """Lightweight, idempotent migrations for DBs created by older versions."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(detections)")}
    if "obj_faiss_id" not in cols:
        conn.execute("ALTER TABLE detections ADD COLUMN obj_faiss_id INTEGER")
    # Safe now that the column is guaranteed to exist (fresh + migrated DBs).
    conn.execute("CREATE INDEX IF NOT EXISTS idx_det_obj ON detections(obj_faiss_id)")

    # GovIntel alerts carry a source link; older notifications tables lack it.
    ncols = {r["name"] for r in conn.execute("PRAGMA table_info(notifications)")}
    if ncols and "link" not in ncols:
        conn.execute("ALTER TABLE notifications ADD COLUMN link TEXT")

    # City Map: complaints gain an Ahmedabad locality + centroid coordinates.
    ccols = {r["name"] for r in conn.execute("PRAGMA table_info(complaints)")}
    if ccols:
        if "area" not in ccols:
            conn.execute("ALTER TABLE complaints ADD COLUMN area TEXT")
        if "lat" not in ccols:
            conn.execute("ALTER TABLE complaints ADD COLUMN lat REAL")
        if "lng" not in ccols:
            conn.execute("ALTER TABLE complaints ADD COLUMN lng REAL")
        # NCRP/1930-style structured cybercrime intake: fraud taxonomy + the
        # money-loss / channel / timing fields the 1930 helpline triages on.
        if "cyber_category" not in ccols:
            conn.execute("ALTER TABLE complaints ADD COLUMN cyber_category TEXT")
        if "amount_lost" not in ccols:
            conn.execute("ALTER TABLE complaints ADD COLUMN amount_lost REAL")
        if "fraud_channel" not in ccols:
            conn.execute("ALTER TABLE complaints ADD COLUMN fraud_channel TEXT")
        if "hours_since_incident" not in ccols:
            conn.execute("ALTER TABLE complaints ADD COLUMN hours_since_incident REAL")

    # City Map: cameras/feeds can be tagged with a locality so anomaly events
    # become mappable.
    vcols = {r["name"] for r in conn.execute("PRAGMA table_info(videos)")}
    if vcols and "area" not in vcols:
        conn.execute("ALTER TABLE videos ADD COLUMN area TEXT")

    # Closed-loop incident response: a live anomaly auto-spawns a geo-tagged
    # case; the originating event remembers its case (NULL until/unless one is
    # created) so the Live Alerts panel can link to it and we can dedupe within
    # the debounce window.
    aecols = {r["name"] for r in conn.execute("PRAGMA table_info(anomaly_events)")}
    if aecols and "case_id" not in aecols:
        conn.execute("ALTER TABLE anomaly_events ADD COLUMN case_id INTEGER")

    # Token revocation: bumping a user's token_version invalidates every JWT
    # issued before the bump (logout-all, account disable, password reset).
    ucols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
    if ucols and "token_version" not in ucols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0")


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
