from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    for statement in _FOUNDATION_SCHEMA:
        connection.execute(statement)
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(memory_embeddings)").fetchall()
    }
    if "memory_id" in columns:
        connection.execute(
            "CREATE TABLE memory_embeddings_v5 ("
            "source_id TEXT NOT NULL, source_type TEXT NOT NULL, "
            "embedding_model_key TEXT NOT NULL, dimensions INTEGER NOT NULL, "
            "embedding BLOB NOT NULL, content_text TEXT NOT NULL, "
            "created_at TEXT NOT NULL, "
            "PRIMARY KEY (source_id, source_type))"
        )
        connection.execute(
            "INSERT OR IGNORE INTO memory_embeddings_v5 "
            "SELECT memory_id, source_type, embedding_model_key, dimensions, "
            "embedding, content_text, created_at FROM memory_embeddings"
        )
        connection.execute("DROP TABLE memory_embeddings")
        connection.execute("ALTER TABLE memory_embeddings_v5 RENAME TO memory_embeddings")


_FOUNDATION_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS lifecycle_records ("
    "record_key TEXT PRIMARY KEY, record_value TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS provider_settings ("
    "setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS provider_directory ("
    "provider_id TEXT PRIMARY KEY, provider_name TEXT NOT NULL, "
    "sort_order INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS provider_model_catalog ("
    "provider_id TEXT NOT NULL, access_path TEXT NOT NULL, model_kind TEXT NOT NULL, "
    "model_id TEXT NOT NULL, model_label TEXT, sort_order INTEGER NOT NULL DEFAULT 0, "
    "enabled INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL, "
    "PRIMARY KEY (provider_id, access_path, model_kind, model_id), "
    "FOREIGN KEY(provider_id) REFERENCES provider_directory(provider_id))",
    "CREATE TABLE IF NOT EXISTS session_transcript_entries ("
    "session_id TEXT NOT NULL, entry_index INTEGER NOT NULL, role TEXT NOT NULL, "
    "event_type TEXT NOT NULL, text_content TEXT NOT NULL, created_at TEXT NOT NULL, "
    "PRIMARY KEY (session_id, entry_index))",
    "CREATE TABLE IF NOT EXISTS session_summaries ("
    "session_id TEXT PRIMARY KEY, summary_status TEXT NOT NULL, summarizer_model_key TEXT, "
    "transcript_text TEXT, summary_text TEXT, extracted_memory_count INTEGER NOT NULL DEFAULT 0, "
    "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS memory_records ("
    "memory_id TEXT PRIMARY KEY, session_id TEXT, memory_class TEXT NOT NULL, "
    "memory_key TEXT NOT NULL, content_text TEXT NOT NULL, confidence TEXT NOT NULL DEFAULT 'medium', "
    "sensitivity TEXT NOT NULL DEFAULT 'normal', status TEXT NOT NULL DEFAULT 'active', "
    "metadata_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS memory_embeddings ("
    "source_id TEXT NOT NULL, source_type TEXT NOT NULL, embedding_model_key TEXT NOT NULL, "
    "dimensions INTEGER NOT NULL, embedding BLOB NOT NULL, content_text TEXT NOT NULL, "
    "created_at TEXT NOT NULL, PRIMARY KEY (source_id, source_type))",
)
