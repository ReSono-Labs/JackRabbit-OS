from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS connection_credential_envelopes (
            connection_id TEXT PRIMARY KEY,
            envelope TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
