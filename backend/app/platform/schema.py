"""SQLite schema for the CityShield platform layer (auth, cases, complaints…).

Lives in the same SQLite database as the VisionScan metadata. Applied
idempotently from database.init_db() so it never disturbs existing tables.
"""

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
    read         INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, read);

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

CREATE TABLE IF NOT EXISTS email_outbox (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    to_email   TEXT NOT NULL,
    subject    TEXT NOT NULL,
    body       TEXT NOT NULL,
    sent       INTEGER NOT NULL DEFAULT 0,   -- 1 if delivered via SMTP, 0 = outbox only
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""
