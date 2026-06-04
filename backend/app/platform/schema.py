"""SQLite schema for the CityShield platform layer (auth, cases, complaints…).

Lives in the same SQLite database as the VisionScan metadata. Applied
idempotently from database.init_db() so it never disturbs existing tables.

Also hosts the complaint-create request model: ComplaintIn started out as a
plain title/description form but now carries the NCRP/1930 structured
cybercrime intake fields, so it validates against the cyber fraud taxonomy in
constants/cyber.py.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ..constants.cyber import category_keys, FRAUD_CHANNELS


# ---- complaints (NCRP/1930-style structured cybercrime intake) ----
class ComplaintIn(BaseModel):
    """Citizen complaint payload. The cyber_* fields are optional and only set
    when the citizen files via the Cybercrime form; setting cyber_category is
    what flips the complaint into the cyber_fraud track (see routes)."""

    title: str
    description: str
    category: Optional[str] = None
    location: Optional[str] = None
    area: Optional[str] = None        # Ahmedabad locality (constants/ahmedabad.py)
    # ---- structured cybercrime intake (NCRP / 1930) ----
    cyber_category: Optional[str] = None    # key in constants/cyber.CYBER_CATEGORIES
    amount_lost: Optional[float] = Field(None, ge=0)   # ₹ money lost, if any
    fraud_channel: Optional[str] = None     # how it happened (FRAUD_CHANNELS)
    hours_since_incident: Optional[float] = Field(None, ge=0)  # for golden-hour nudge

    @field_validator("cyber_category")
    @classmethod
    def _check_category(cls, v: Optional[str]) -> Optional[str]:
        if v not in (None, "") and v not in category_keys():
            raise ValueError(f"cyber_category must be one of {category_keys()}")
        return v or None

    @field_validator("fraud_channel")
    @classmethod
    def _check_channel(cls, v: Optional[str]) -> Optional[str]:
        if v not in (None, "") and v not in FRAUD_CHANNELS:
            raise ValueError(f"fraud_channel must be one of {list(FRAUD_CHANNELS)}")
        return v or None


PLATFORM_SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    station      TEXT DEFAULT 'Ahmedabad Cyber Crime Branch',
    lead_user_id INTEGER,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'citizen',  -- citizen|officer|lead|admin
    team_id       INTEGER REFERENCES teams(id),
    phone         TEXT,
    badge_no      TEXT,
    active        INTEGER NOT NULL DEFAULT 1,
    reset_token   TEXT,
    reset_expires TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

CREATE TABLE IF NOT EXISTS complaints (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    citizen_id     INTEGER NOT NULL REFERENCES users(id),
    title          TEXT NOT NULL,
    description    TEXT NOT NULL,
    category       TEXT,
    location       TEXT,
    status         TEXT NOT NULL DEFAULT 'submitted',
        -- submitted|under_review|assigned|converted|rejected
    severity       TEXT,                              -- low|medium|high|critical
    priority       INTEGER,
    response_message TEXT,
    assigned_team_id INTEGER REFERENCES teams(id),
    case_id        INTEGER,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_complaints_citizen ON complaints(citizen_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);

CREATE TABLE IF NOT EXISTS cases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    description     TEXT,
    complaint_id    INTEGER REFERENCES complaints(id),
    created_by      INTEGER NOT NULL REFERENCES users(id),
    assigned_team_id INTEGER REFERENCES teams(id),
    status          TEXT NOT NULL DEFAULT 'open',     -- open|active|closed
    severity        TEXT DEFAULT 'medium',
    priority        INTEGER DEFAULT 3,
    citizen_visible INTEGER NOT NULL DEFAULT 0,
    citizen_id      INTEGER REFERENCES users(id),
    verdict         TEXT,
    closed_by       INTEGER REFERENCES users(id),
    closed_at       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_team ON cases(assigned_team_id);

CREATE TABLE IF NOT EXISTS case_assignments (
    case_id      INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    role_on_case TEXT DEFAULT 'investigator',
    assigned_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (case_id, user_id)
);

CREATE TABLE IF NOT EXISTS evidence (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id    INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL,            -- frame|video|file|report|note
    ref        TEXT,                     -- frame_id / video_id / url / path
    caption    TEXT,
    visibility TEXT NOT NULL DEFAULT 'team',  -- team|station|department|citizen
    added_by   INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence(case_id);

CREATE TABLE IF NOT EXISTS case_documents (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id    INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    doc_type   TEXT NOT NULL,            -- FIR|brief|chargesheet|other
    title      TEXT NOT NULL,
    content    TEXT,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_docs_case ON case_documents(case_id);

CREATE TABLE IF NOT EXISTS case_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    sender_id   INTEGER NOT NULL REFERENCES users(id),
    sender_role TEXT NOT NULL,
    body        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_msg_case ON case_messages(case_id);

CREATE TABLE IF NOT EXISTS case_meetings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id      INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,             -- ISO datetime the team should be available
    duration_min INTEGER DEFAULT 60,
    location     TEXT DEFAULT 'Ahmedabad Cyber Crime Branch',
    notes        TEXT,
    created_by   INTEGER NOT NULL REFERENCES users(id),
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_meetings_case ON case_meetings(case_id);

CREATE TABLE IF NOT EXISTS ratings (
    case_id    INTEGER PRIMARY KEY REFERENCES cases(id) ON DELETE CASCADE,
    citizen_id INTEGER NOT NULL REFERENCES users(id),
    stars      INTEGER NOT NULL,
    comment    TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notifications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    type         TEXT NOT NULL,
    message      TEXT NOT NULL,
    case_id      INTEGER,
    complaint_id INTEGER,
    link         TEXT,                          -- optional URL (e.g. GovIntel source)
    read         INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, read);

-- Always-on CCTV anomaly watch: one row per debounced incident (consecutive
-- detections of the same type on the same feed collapse into one event).
-- References the VisionScan core tables (same SQLite file, created earlier
-- in init_db), so the FKs are valid by the time this schema is applied.
CREATE TABLE IF NOT EXISTS anomaly_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    frame_id    INTEGER REFERENCES frames(id) ON DELETE SET NULL,
    type        TEXT NOT NULL,             -- fire|smoke|accident|weapon|violence
    confidence  REAL NOT NULL,
    source      TEXT NOT NULL,             -- clip|yolo|clip+yolo
    x1 REAL, y1 REAL, x2 REAL, y2 REAL,    -- optional bbox (object signals)
    status      TEXT NOT NULL DEFAULT 'new',   -- new|acknowledged|dismissed
    peak_count  INTEGER NOT NULL DEFAULT 1,    -- frames merged into this event
    last_ts_sec REAL,                      -- newest grouped frame timestamp
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_anom_status ON anomaly_events(status);
CREATE INDEX IF NOT EXISTS idx_anom_video ON anomaly_events(video_id, type);

-- Government/admin city-wide alerts (disasters, advisories). The broadcast
-- row is the durable record + powers the "active alert" banner; delivery to
-- each user is fanned out into the notifications table at send time.
CREATE TABLE IF NOT EXISTS broadcasts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kind       TEXT NOT NULL DEFAULT 'advisory',  -- disaster|advisory
    title      TEXT NOT NULL,
    message    TEXT NOT NULL,
    area       TEXT,                              -- optional Ahmedabad locality
    severity   TEXT NOT NULL DEFAULT 'medium',    -- low|medium|high|critical
    link       TEXT,
    expires_at TEXT,                              -- ISO; NULL = until deactivated
    active     INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_broadcasts_active ON broadcasts(active);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id   INTEGER,
    action     TEXT NOT NULL,
    entity     TEXT,
    entity_id  INTEGER,
    detail     TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity, entity_id);

-- Login attempt journal: powers brute-force lockout + security event review.
CREATE TABLE IF NOT EXISTS login_attempts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT NOT NULL,
    ip         TEXT,
    ok         INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_login_attempts ON login_attempts(email, created_at);

-- Tiny key/value store for runtime switches (e.g. emergency lockdown).
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Patrol check-ins: ground truth for the predictive patrol-routing loop.
CREATE TABLE IF NOT EXISTS patrol_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    officer_id INTEGER NOT NULL REFERENCES users(id),
    area       TEXT NOT NULL,
    note       TEXT,
    status     TEXT NOT NULL DEFAULT 'clear',  -- clear|incident|followup
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_patrol_area ON patrol_logs(area, created_at);

CREATE TABLE IF NOT EXISTS email_outbox (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    to_email   TEXT NOT NULL,
    subject    TEXT NOT NULL,
    body       TEXT NOT NULL,
    sent       INTEGER NOT NULL DEFAULT 0,   -- 1 if delivered via SMTP, 0 = outbox only
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""
