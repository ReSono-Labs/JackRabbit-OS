from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS mcp_connection_routing (
            audience TEXT PRIMARY KEY,
            connection_id TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_mcp_connection_routing_connection
            ON mcp_connection_routing(connection_id);
        """
    )
