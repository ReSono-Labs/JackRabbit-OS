from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE calendar_accounts (
            account_id TEXT PRIMARY KEY,
            provider_type TEXT NOT NULL CHECK(provider_type IN ('ics_file','ics_subscription','caldav')),
            label TEXT NOT NULL,
            endpoint TEXT,
            calendar_path TEXT,
            can_create INTEGER NOT NULL DEFAULT 0 CHECK(can_create IN (0,1)),
            can_update INTEGER NOT NULL DEFAULT 0 CHECK(can_update IN (0,1)),
            can_delete INTEGER NOT NULL DEFAULT 0 CHECK(can_delete IN (0,1)),
            next_sync_at TEXT,
            last_sync_at TEXT,
            last_sync_state TEXT NOT NULL DEFAULT 'pending'
                CHECK(last_sync_state IN ('pending','syncing','ready','failed')),
            last_sync_detail TEXT,
            sync_lease_until TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES connections(connection_id) ON DELETE CASCADE
        );

        CREATE TABLE calendar_events (
            event_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            provider_event_id TEXT NOT NULL,
            recurrence_id TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            starts_at TEXT NOT NULL,
            ends_at TEXT,
            timezone TEXT NOT NULL,
            all_day INTEGER NOT NULL DEFAULT 0 CHECK(all_day IN (0,1)),
            location TEXT,
            calendar_name TEXT,
            organizer TEXT,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'confirmed'
                CHECK(status IN ('tentative','confirmed','cancelled')),
            editable INTEGER NOT NULL DEFAULT 0 CHECK(editable IN (0,1)),
            source_etag TEXT,
            synchronized_at TEXT NOT NULL,
            UNIQUE(account_id, provider_event_id, recurrence_id),
            FOREIGN KEY(account_id) REFERENCES calendar_accounts(account_id) ON DELETE CASCADE
        );

        CREATE INDEX calendar_events_upcoming
            ON calendar_events(status, starts_at, ends_at, event_id);
        CREATE INDEX calendar_events_account
            ON calendar_events(account_id, provider_event_id, recurrence_id);

        CREATE TABLE calendar_pending_actions (
            action_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            event_id TEXT,
            operation TEXT NOT NULL CHECK(operation IN ('create','update','delete')),
            payload_json TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('pending_review','executing','completed','expired','failed')),
            voice_session_id TEXT NOT NULL,
            tool_call_id TEXT NOT NULL,
            prepared_utterance_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(account_id) REFERENCES calendar_accounts(account_id) ON DELETE CASCADE
        );
        CREATE INDEX calendar_pending_actions_expiry
            ON calendar_pending_actions(state, expires_at);
        """
    )
