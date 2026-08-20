from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(import_operations)")}
    if "phase" not in columns:
        connection.execute(
            "ALTER TABLE import_operations ADD COLUMN phase TEXT NOT NULL DEFAULT 'planned' "
            "CHECK (phase IN ('planned', 'backup_secured', 'activated'))"
        )
