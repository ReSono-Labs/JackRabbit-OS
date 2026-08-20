from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS import_operations (
            operation_id TEXT PRIMARY KEY,
            resource_kind TEXT NOT NULL CHECK (resource_kind IN ('skill', 'plugin', 'creation')),
            identity TEXT NOT NULL,
            candidate_hash TEXT NOT NULL,
            target_path TEXT NOT NULL,
            backup_path TEXT NOT NULL,
            staged_path TEXT NOT NULL,
            started_at TEXT NOT NULL
        )
        """
    )
