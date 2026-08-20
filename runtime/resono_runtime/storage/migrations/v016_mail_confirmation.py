from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(mail_drafts)")}
    additions = {
        "voice_session_id": "TEXT NOT NULL DEFAULT ''",
        "compose_tool_call_id": "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in additions.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE mail_drafts ADD COLUMN {name} {definition}")
