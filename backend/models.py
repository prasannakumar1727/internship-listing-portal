"""Table structures for the Internship Listing Portal (SQLite)."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS internships (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    company         TEXT NOT NULL,
    location        TEXT NOT NULL,
    domain          TEXT NOT NULL,
    duration_months INTEGER NOT NULL CHECK (duration_months > 0),
    stipend         INTEGER NOT NULL DEFAULT 0 CHECK (stipend >= 0),  -- Rs per month
    work_mode       TEXT NOT NULL CHECK (work_mode IN ('Remote','Onsite','Hybrid')),
    description     TEXT NOT NULL,
    requirements    TEXT NOT NULL,   -- one item per line
    benefits        TEXT NOT NULL,   -- one item per line
    deadline        TEXT NOT NULL,   -- YYYY-MM-DD
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    internship_id INTEGER NOT NULL REFERENCES internships(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL,
    phone         TEXT NOT NULL,
    resume_link   TEXT,
    resume_file   TEXT,              -- stored (renamed) file name
    cover_note    TEXT,
    status        TEXT NOT NULL DEFAULT 'Received'
                  CHECK (status IN ('Received','Shortlisted','Rejected')),
    applied_date  TEXT NOT NULL DEFAULT (date('now')),
    UNIQUE (email, internship_id)    -- blocks duplicate applications
);

CREATE INDEX IF NOT EXISTS idx_int_filters ON internships(location, domain, work_mode);
"""
