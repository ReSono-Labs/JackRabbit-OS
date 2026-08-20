"""Schema for the global, auditable agent-audience routing boundary."""

from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS agent_audience_bindings (
            resource_kind TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            audience TEXT NOT NULL CHECK (audience IN ('voice', 'text', 'both')),
            active INTEGER NOT NULL CHECK (active IN (0, 1)),
            changed_at TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            change_reason TEXT NOT NULL,
            PRIMARY KEY (resource_kind, resource_id)
        );
        CREATE TABLE IF NOT EXISTS agent_audience_audit (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_kind TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            previous_audience TEXT CHECK (previous_audience IN ('voice', 'text', 'both')),
            new_audience TEXT CHECK (new_audience IN ('voice', 'text', 'both')),
            action TEXT NOT NULL CHECK (action IN ('set', 'disable', 'remove')),
            changed_at TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            change_reason TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS agent_audience_bindings_active_idx
            ON agent_audience_bindings (active, audience, resource_kind);
        CREATE INDEX IF NOT EXISTS agent_audience_audit_resource_idx
            ON agent_audience_audit (resource_kind, resource_id, audit_id);
        """
    )
