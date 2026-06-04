"""SQLite schema for the CrimeGPT module — the unified case data pool.

Lives in the same SQLite database as the rest of CityShield and is applied
idempotently from database.init_db() so it never disturbs existing tables.

All tables reference the existing platform `cases(id)` so the data pool hangs
off a real investigation case. Generated documents are versioned in
`crimegpt_documents` (NOT the platform's own `case_documents` table — that one
stores free-text FIR/brief content; these are versioned, generated PDFs).
"""

CRIMEGPT_SCHEMA = """
-- Parties to a case: accused, victims, witnesses. Single-entry, reused across
-- every generated document.
CREATE TABLE IF NOT EXISTS case_parties (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,            -- accused|victim|witness
    name        TEXT NOT NULL,
    age         INTEGER,
    gender      TEXT,
    address     TEXT,
    phone       TEXT,
    id_proof    TEXT,                     -- e.g. "Aadhaar xxxx-1234"
    description TEXT,                     -- physical description / role notes
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cgpt_parties_case ON case_parties(case_id);

-- Seized articles / muddamal for the seizure receipt + chargesheet.
CREATE TABLE IF NOT EXISTS case_seizures (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id       INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    item          TEXT NOT NULL,
    quantity      TEXT,
    description   TEXT,
    seized_from   TEXT,                   -- party name / place
    seized_at     TEXT,                   -- ISO datetime or free text
    witness_names TEXT,                   -- panch witnesses (comma separated)
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cgpt_seizures_case ON case_seizures(case_id);

-- Recorded statements (BNSS s.180 / s.183) attributable to a party.
CREATE TABLE IF NOT EXISTS case_statements (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id        INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    party_id       INTEGER REFERENCES case_parties(id) ON DELETE SET NULL,
    statement_text TEXT NOT NULL,
    recorded_by    INTEGER REFERENCES users(id),
    recorded_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cgpt_stmts_case ON case_statements(case_id);

-- Chronological case diary (Roznamcha-style). entry_type tags the kind of
-- entry; auto-entries are written whenever a document is generated.
CREATE TABLE IF NOT EXISTS case_diary (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id    INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    entry_type TEXT NOT NULL DEFAULT 'note',  -- note|document|investigation|custody|seizure
    narrative  TEXT NOT NULL,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cgpt_diary_case ON case_diary(case_id);

-- Versioned generated documents. Regenerating the same doc_type bumps version.
-- We store a content_hash (sha256 of the PDF bytes) rather than the blob, so
-- the DB stays light; the PDF is streamed to the client on generation.
CREATE TABLE IF NOT EXISTS crimegpt_documents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id      INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    doc_type     TEXT NOT NULL,
    language     TEXT NOT NULL DEFAULT 'en',
    version      INTEGER NOT NULL DEFAULT 1,
    file_path    TEXT,                    -- optional on-disk copy (unused by default)
    content_hash TEXT,                    -- sha256 of the generated PDF bytes
    generated_by INTEGER REFERENCES users(id),
    generated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cgpt_docs_case ON crimegpt_documents(case_id);
CREATE INDEX IF NOT EXISTS idx_cgpt_docs_type ON crimegpt_documents(case_id, doc_type);
"""
