"""SQLite schema for the GovIntel module (gov document cache, bookmarks,
subscriptions, search log).

Lives in the same SQLite database as the rest of CityShield. Applied
idempotently from database.init_db() so it never disturbs existing tables.
The `notifications` table (defined in platform/schema.py) is reused for alerts.
"""

GOVINTEL_SCHEMA = """
CREATE TABLE IF NOT EXISTS gov_documents (
    id          TEXT PRIMARY KEY,            -- stable doc id (bundled or feed hash)
    title       TEXT NOT NULL,
    doc_type    TEXT NOT NULL,               -- GR|Notification|Circular|Act|Rule|Judgment|Scheme
    department  TEXT,
    ministry    TEXT,
    region      TEXT,                         -- central|gujarat
    date        TEXT,                         -- ISO date (issue/publish date)
    summary     TEXT,
    body        TEXT,
    keywords    TEXT,                         -- comma-separated
    source_url  TEXT,
    language    TEXT DEFAULT 'en',
    origin      TEXT NOT NULL DEFAULT 'bundled',  -- bundled|live
    fetched_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_gov_type ON gov_documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_gov_region ON gov_documents(region);
CREATE INDEX IF NOT EXISTS idx_gov_date ON gov_documents(date);

CREATE TABLE IF NOT EXISTS gov_bookmarks (
    user_id    INTEGER NOT NULL REFERENCES users(id),
    doc_id     TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, doc_id)
);

CREATE TABLE IF NOT EXISTS gov_subscriptions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    query      TEXT NOT NULL DEFAULT '',     -- keyword/topic to watch (e.g. "pension")
    doc_type   TEXT,                          -- optional category filter
    region     TEXT,                          -- optional central|gujarat filter
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_gov_sub_user ON gov_subscriptions(user_id);

CREATE TABLE IF NOT EXISTS gov_search_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    query      TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_gov_searchlog_q ON gov_search_log(query);
"""
