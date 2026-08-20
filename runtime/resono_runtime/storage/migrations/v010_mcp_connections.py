from __future__ import annotations
import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript("""
    CREATE TABLE IF NOT EXISTS mcp_connections (
        connection_id TEXT PRIMARY KEY, display_name TEXT NOT NULL,
        transport TEXT NOT NULL CHECK(transport IN ('streamable-http','sse','stdio')),
        endpoint TEXT, command_json TEXT, configuration_hash TEXT NOT NULL,
        lifecycle_state TEXT NOT NULL CHECK(lifecycle_state IN ('draft','configured','connected','disabled','failed')),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS mcp_connection_audit (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT, connection_id TEXT NOT NULL,
        action TEXT NOT NULL, previous_hash TEXT, current_hash TEXT,
        changed_at TEXT NOT NULL, changed_by TEXT NOT NULL, change_reason TEXT NOT NULL
    );
    """)
