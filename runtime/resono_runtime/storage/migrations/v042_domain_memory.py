from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(memory_records)").fetchall()
    }
    additions = (
        ("subject_id", "TEXT NOT NULL DEFAULT 'primary'"),
        ("domain", "TEXT NOT NULL DEFAULT 'personal'"),
        ("memory_type", "TEXT NOT NULL DEFAULT 'fact'"),
        ("current_version", "INTEGER NOT NULL DEFAULT 1"),
        ("valid_from", "TEXT"),
        ("valid_to", "TEXT"),
        ("last_confirmed_at", "TEXT"),
    )
    for name, declaration in additions:
        if name not in columns:
            connection.execute(f"ALTER TABLE memory_records ADD COLUMN {name} {declaration}")
    connection.executescript(
        """
        UPDATE memory_records SET
            domain = CASE memory_class
                WHEN 'preference' THEN 'personal'
                WHEN 'relationship' THEN 'relationship'
                WHEN 'environment' THEN 'environment'
                ELSE 'personal' END,
            memory_type = CASE memory_class
                WHEN 'preference' THEN 'preference'
                ELSE 'fact' END,
            last_confirmed_at = COALESCE(last_confirmed_at, updated_at);

        CREATE TABLE IF NOT EXISTS memory_record_versions (
            memory_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            content_text TEXT NOT NULL,
            confidence TEXT NOT NULL,
            sensitivity TEXT NOT NULL,
            status TEXT NOT NULL,
            valid_from TEXT,
            valid_to TEXT,
            reviewer_model TEXT,
            reviewer_contract_version INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (memory_id, version_number),
            FOREIGN KEY(memory_id) REFERENCES memory_records(memory_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS memory_evidence (
            evidence_id TEXT PRIMARY KEY,
            memory_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            entry_index INTEGER,
            source_type TEXT NOT NULL,
            source_authority TEXT NOT NULL,
            supporting_excerpt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(memory_id, version_number, session_id, entry_index, source_type),
            FOREIGN KEY(memory_id, version_number)
                REFERENCES memory_record_versions(memory_id, version_number) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS memory_ingestions (
            session_id TEXT NOT NULL,
            reviewer_contract_version INTEGER NOT NULL,
            transcript_fingerprint TEXT NOT NULL,
            state TEXT NOT NULL,
            reviewer_model TEXT,
            candidate_count INTEGER NOT NULL DEFAULT 0,
            stored_count INTEGER NOT NULL DEFAULT 0,
            error_code TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            PRIMARY KEY(session_id, reviewer_contract_version)
        );

        CREATE TABLE IF NOT EXISTS memory_pending_actions (
            action_id TEXT PRIMARY KEY,
            action_kind TEXT NOT NULL,
            memory_id TEXT NOT NULL,
            proposed_content TEXT,
            voice_session_id TEXT,
            prepared_utterance_id INTEGER,
            state TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY(memory_id) REFERENCES memory_records(memory_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_memory_records_identity
            ON memory_records(subject_id, domain, memory_type, memory_key, status);
        CREATE INDEX IF NOT EXISTS idx_memory_evidence_session
            ON memory_evidence(session_id, entry_index);

        INSERT OR IGNORE INTO memory_record_versions(
            memory_id, version_number, content_text, confidence, sensitivity, status,
            valid_from, valid_to, reviewer_model, reviewer_contract_version, created_at)
        SELECT memory_id, 1, content_text, confidence, sensitivity, status,
               valid_from, valid_to, NULL, 1, created_at
        FROM memory_records;
        """
    )
