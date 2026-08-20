from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(mail_drafts)")}
    if "compose_utterance_id" not in columns:
        connection.execute(
            "ALTER TABLE mail_drafts ADD COLUMN compose_utterance_id INTEGER NOT NULL DEFAULT 0"
        )
