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

-- Saved searches: a named query + the full advanced-filter set (stored as JSON
-- in `filters`) that a user can re-run from the "Saved" tab. When alert=1 the
-- saved search rides the existing refresh fan-out, so matching fresh documents
-- raise a gov_update notification (same in-app bell as subscriptions).
CREATE TABLE IF NOT EXISTS gov_saved_searches (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    name       TEXT NOT NULL DEFAULT '',     -- friendly label (defaults to the query)
    query      TEXT NOT NULL DEFAULT '',
    filters    TEXT NOT NULL DEFAULT '{}',   -- JSON: doc_type/region/department/date_from/date_to
    alert      INTEGER NOT NULL DEFAULT 0,    -- 1 = notify on matching fresh docs
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_gov_saved_user ON gov_saved_searches(user_id);

-- Feed health: one row per feed, updated on every refresh so the insights strip
-- can show per-source last-success / last-attempt and item counts (source health).
CREATE TABLE IF NOT EXISTS gov_feed_status (
    feed_key      TEXT PRIMARY KEY,
    name          TEXT NOT NULL DEFAULT '',
    last_attempt  TEXT,
    last_success  TEXT,
    last_count    INTEGER NOT NULL DEFAULT 0,
    ok            INTEGER NOT NULL DEFAULT 0     -- 1 = last fetch returned >=0 items without error
);
"""
