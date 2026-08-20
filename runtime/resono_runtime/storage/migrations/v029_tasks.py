from __future__ import annotations
import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE tasks (
            task_id TEXT PRIMARY KEY,
            task_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','completed')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            completed_at TEXT
        );
        CREATE INDEX tasks_active_order ON tasks(status, created_at, task_id);

        CREATE TABLE task_pending_actions (
            action_id TEXT PRIMARY KEY,
            task_id TEXT,
            operation TEXT NOT NULL CHECK(operation IN ('add','edit','complete','remove')),
            payload_json TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('pending_review','executing','completed','failed')),
            voice_session_id TEXT NOT NULL,
            tool_call_id TEXT NOT NULL,
            prepared_utterance_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX task_pending_actions_expiry ON task_pending_actions(state, expires_at);
        """
    )
