from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS connections (
            connection_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL CHECK (kind IN ('mail', 'mcp', 'calendar')),
            label TEXT NOT NULL,
            enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
            health_state TEXT NOT NULL CHECK (
                health_state IN ('unconfigured', 'ready', 'syncing', 'failed', 'disabled')
            ),
            health_detail TEXT,
            source_owner TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS connections_kind_idx ON connections(kind, label);
        """
    )
