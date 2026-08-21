from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.execute(
        "ALTER TABLE background_agent_runs ADD COLUMN recipe TEXT NOT NULL DEFAULT 'self_review_v1'"
    )
    connection.execute(
        "ALTER TABLE background_agent_settings ADD COLUMN default_recipe TEXT NOT NULL DEFAULT 'self_review_v1'"
    )
