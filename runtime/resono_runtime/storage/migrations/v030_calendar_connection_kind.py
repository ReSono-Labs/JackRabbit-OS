from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    """Widen the deployed connection discriminator without losing existing rows."""
    connection.executescript(
        """
        PRAGMA foreign_keys = OFF;
        CREATE TABLE connections_v30 (
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
        INSERT INTO connections_v30(
            connection_id, kind, label, enabled, health_state, health_detail,
            source_owner, created_at, updated_at
        )
        SELECT connection_id, kind, label, enabled, health_state, health_detail,
               source_owner, created_at, updated_at
        FROM connections;
        DROP TABLE connections;
        ALTER TABLE connections_v30 RENAME TO connections;
        CREATE INDEX connections_kind_idx ON connections(kind, label);
        PRAGMA foreign_keys = ON;
        """
    )
