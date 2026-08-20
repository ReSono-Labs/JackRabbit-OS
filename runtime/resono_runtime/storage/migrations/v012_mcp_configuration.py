from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(mcp_connections)")}
    if "configuration_json" not in columns:
        connection.execute(
            "ALTER TABLE mcp_connections ADD COLUMN configuration_json TEXT NOT NULL DEFAULT '{}'"
        )
