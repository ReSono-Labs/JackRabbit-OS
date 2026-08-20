from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(creation_catalog)")}
    if "source_type" not in columns:
        connection.execute("ALTER TABLE creation_catalog ADD COLUMN source_type TEXT NOT NULL DEFAULT 'local_archive' CHECK (source_type IN ('local_archive','rabbit_qr_link'))")
    if "entry_url" not in columns:
        connection.execute("ALTER TABLE creation_catalog ADD COLUMN entry_url TEXT")
    if "icon_url" not in columns:
        connection.execute("ALTER TABLE creation_catalog ADD COLUMN icon_url TEXT")
    if "theme_color" not in columns:
        connection.execute("ALTER TABLE creation_catalog ADD COLUMN theme_color TEXT NOT NULL DEFAULT '#79f2dd'")
