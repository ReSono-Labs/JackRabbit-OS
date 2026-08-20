from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS mcp_discovered_tools (
            connection_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            exposed_name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            input_schema_json TEXT NOT NULL,
            discovered_at TEXT NOT NULL,
            PRIMARY KEY (connection_id, tool_name),
            FOREIGN KEY (connection_id) REFERENCES mcp_connections(connection_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS mcp_discovered_tools_connection_idx
            ON mcp_discovered_tools(connection_id, tool_name);
        """
    )
