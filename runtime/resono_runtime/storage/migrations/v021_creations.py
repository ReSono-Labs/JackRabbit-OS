from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    operation_sql_row = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='import_operations'").fetchone()
    if operation_sql_row is not None and "'creation'" not in str(operation_sql_row[0]):
        connection.executescript(
            """
            ALTER TABLE import_operations RENAME TO import_operations_v018;
            CREATE TABLE import_operations (
                operation_id TEXT PRIMARY KEY,
                resource_kind TEXT NOT NULL CHECK (resource_kind IN ('skill', 'plugin', 'creation')),
                identity TEXT NOT NULL,
                candidate_hash TEXT NOT NULL,
                target_path TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                staged_path TEXT NOT NULL,
                started_at TEXT NOT NULL
            );
            INSERT INTO import_operations SELECT * FROM import_operations_v018;
            DROP TABLE import_operations_v018;
            """
        )
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS creation_catalog (
            creation_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            install_path TEXT NOT NULL,
            lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN ('installed', 'enabled', 'disabled')),
            generation INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS creation_catalog_state (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            generation INTEGER NOT NULL
        );
        INSERT OR IGNORE INTO creation_catalog_state(singleton, generation) VALUES (1, 0);
        CREATE TABLE IF NOT EXISTS creation_catalog_audit (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            creation_id TEXT NOT NULL,
            action TEXT NOT NULL,
            previous_hash TEXT,
            current_hash TEXT,
            changed_at TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            change_reason TEXT NOT NULL
        );
        """
    )
