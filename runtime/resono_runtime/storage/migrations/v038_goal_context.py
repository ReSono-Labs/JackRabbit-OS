from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        ALTER TABLE background_agent_runs ADD COLUMN goal_type TEXT NOT NULL DEFAULT 'general';
        ALTER TABLE background_agent_runs ADD COLUMN context_summary TEXT NOT NULL DEFAULT '';
        ALTER TABLE background_agent_runs ADD COLUMN expected_result TEXT NOT NULL DEFAULT '';
        ALTER TABLE background_agent_runs ADD COLUMN scope TEXT NOT NULL DEFAULT '';
        ALTER TABLE background_agent_runs ADD COLUMN exclusions_json TEXT NOT NULL DEFAULT '[]';
        ALTER TABLE background_agent_runs ADD COLUMN source_requirements TEXT NOT NULL DEFAULT '';
        ALTER TABLE background_agent_runs ADD COLUMN workspace_destination TEXT;
        """
    )
