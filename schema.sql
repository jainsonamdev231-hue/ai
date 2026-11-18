-- OmniBrain AI Permanent SQLite Database Schema

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL DEFAULT 'default',
    sender TEXT NOT NULL,
    message TEXT NOT NULL,
    ai_model TEXT DEFAULT 'council',
    language_tag TEXT DEFAULT 'auto',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_vault (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_key TEXT UNIQUE NOT NULL,
    fact_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id);
