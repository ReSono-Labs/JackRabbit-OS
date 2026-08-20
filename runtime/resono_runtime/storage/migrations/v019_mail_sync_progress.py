from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    account_columns = {row["name"] for row in connection.execute("PRAGMA table_info(mail_accounts)")}
    if "sync_lease_until" not in account_columns:
        connection.execute("ALTER TABLE mail_accounts ADD COLUMN sync_lease_until TEXT")
    folder_columns = {row["name"] for row in connection.execute("PRAGMA table_info(mail_folders)")}
    if "sync_cursor_uid" not in folder_columns:
        connection.execute("ALTER TABLE mail_folders ADD COLUMN sync_cursor_uid INTEGER NOT NULL DEFAULT 0")
    if "sync_complete" not in folder_columns:
        connection.execute("ALTER TABLE mail_folders ADD COLUMN sync_complete INTEGER NOT NULL DEFAULT 0 CHECK (sync_complete IN (0, 1))")
