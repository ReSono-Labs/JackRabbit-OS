from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS plugin_catalog (
        plugin_name TEXT PRIMARY KEY, content_hash TEXT NOT NULL, install_path TEXT NOT NULL,
        lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN ('installed','enabled','disabled')),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS plugin_catalog_audit (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT, plugin_name TEXT NOT NULL,
        action TEXT NOT NULL CHECK (action IN ('install','replace','enable','disable','remove')),
        previous_hash TEXT, current_hash TEXT, changed_at TEXT NOT NULL,
        changed_by TEXT NOT NULL, change_reason TEXT NOT NULL
    );
    """)
