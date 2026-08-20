from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    """Remove the obsolete image-to-text cache; Realtime receives raw images."""
    connection.executescript(
        """
        DROP INDEX IF EXISTS idx_direct_handoffs_cache;
        DROP TABLE IF EXISTS direct_handoffs;
        """
    )
