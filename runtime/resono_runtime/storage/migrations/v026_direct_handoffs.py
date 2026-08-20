from __future__ import annotations
import sqlite3
def apply(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS direct_handoffs (handoff_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, file_key TEXT NOT NULL UNIQUE, filename TEXT NOT NULL, mime_type TEXT NOT NULL, content_hash TEXT NOT NULL, question_hash TEXT NOT NULL, model_key TEXT NOT NULL, inspection_markdown TEXT NOT NULL, created_at TEXT NOT NULL)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_direct_handoffs_cache ON direct_handoffs(content_hash,question_hash,model_key,created_at DESC)")
