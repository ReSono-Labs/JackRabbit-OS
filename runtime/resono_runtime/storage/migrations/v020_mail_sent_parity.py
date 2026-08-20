from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(mail_drafts)")}
    for name, definition in {
        "sent_mime": "BLOB",
        "sent_append_state": "TEXT CHECK (sent_append_state IN ('pending', 'ready', 'failed'))",
        "sent_append_detail": "TEXT",
    }.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE mail_drafts ADD COLUMN {name} {definition}")
