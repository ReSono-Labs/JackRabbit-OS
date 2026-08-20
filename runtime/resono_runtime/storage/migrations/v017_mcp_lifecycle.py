from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection_columns = {row["name"] for row in connection.execute("PRAGMA table_info(mcp_connections)")}
    for name, definition in {
        "protocol_version": "TEXT",
        "server_name": "TEXT",
        "server_version": "TEXT",
        "last_discovered_at": "TEXT",
        "health_detail": "TEXT",
    }.items():
        if name not in connection_columns:
            connection.execute(f"ALTER TABLE mcp_connections ADD COLUMN {name} {definition}")
    tool_columns = {row["name"] for row in connection.execute("PRAGMA table_info(mcp_discovered_tools)")}
    for name, definition in {
        "annotations_json": "TEXT NOT NULL DEFAULT '{}'",
        "enabled": "INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1))",
        "effect_class": "TEXT CHECK (effect_class IN ('read', 'local_write', 'external_write', 'destructive'))",
    }.items():
        if name not in tool_columns:
            connection.execute(f"ALTER TABLE mcp_discovered_tools ADD COLUMN {name} {definition}")
