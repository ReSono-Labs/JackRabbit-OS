from __future__ import annotations

import sqlite3


def apply(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS mail_accounts (
            account_id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            email_address TEXT NOT NULL UNIQUE COLLATE NOCASE,
            username TEXT NOT NULL,
            imap_host TEXT NOT NULL,
            imap_port INTEGER NOT NULL CHECK (imap_port BETWEEN 1 AND 65535),
            imap_security TEXT NOT NULL CHECK (imap_security IN ('tls', 'starttls')),
            smtp_host TEXT NOT NULL,
            smtp_port INTEGER NOT NULL CHECK (smtp_port BETWEEN 1 AND 65535),
            smtp_security TEXT NOT NULL CHECK (smtp_security IN ('tls', 'starttls')),
            sync_interval_seconds INTEGER NOT NULL DEFAULT 300 CHECK (sync_interval_seconds = 300),
            next_sync_at TEXT,
            last_sync_at TEXT,
            last_sync_state TEXT NOT NULL DEFAULT 'pending' CHECK (
                last_sync_state IN ('pending', 'syncing', 'ready', 'failed', 'disabled')
            ),
            last_sync_detail TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES connections(connection_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS mail_folders (
            folder_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            remote_name TEXT NOT NULL,
            delimiter TEXT,
            attributes_json TEXT NOT NULL,
            special_use TEXT,
            uid_validity INTEGER,
            uid_next INTEGER,
            highest_modseq INTEGER,
            last_synced_at TEXT,
            UNIQUE(account_id, remote_name),
            FOREIGN KEY (account_id) REFERENCES mail_accounts(account_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS mail_messages (
            message_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            folder_id TEXT NOT NULL,
            uid_validity INTEGER NOT NULL,
            remote_uid INTEGER NOT NULL,
            rfc_message_id TEXT,
            subject TEXT NOT NULL,
            sender_json TEXT NOT NULL,
            recipients_json TEXT NOT NULL,
            sent_at TEXT,
            received_at TEXT,
            flags_json TEXT NOT NULL,
            body_text TEXT,
            body_html TEXT,
            raw_size INTEGER NOT NULL,
            synchronized_at TEXT NOT NULL,
            UNIQUE(folder_id, uid_validity, remote_uid),
            FOREIGN KEY (account_id) REFERENCES mail_accounts(account_id) ON DELETE CASCADE,
            FOREIGN KEY (folder_id) REFERENCES mail_folders(folder_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS mail_messages_account_date_idx
            ON mail_messages(account_id, received_at DESC);
        CREATE TABLE IF NOT EXISTS mail_attachments (
            attachment_id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            part_id TEXT NOT NULL,
            filename TEXT,
            content_type TEXT NOT NULL,
            content_disposition TEXT,
            content_id TEXT,
            byte_size INTEGER NOT NULL,
            UNIQUE(message_id, part_id),
            FOREIGN KEY (message_id) REFERENCES mail_messages(message_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS mail_sync_runs (
            run_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            state TEXT NOT NULL CHECK (state IN ('running', 'ready', 'failed', 'timed_out')),
            folders_seen INTEGER NOT NULL DEFAULT 0,
            messages_seen INTEGER NOT NULL DEFAULT 0,
            detail TEXT,
            FOREIGN KEY (account_id) REFERENCES mail_accounts(account_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS mail_drafts (
            draft_id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            recipients_json TEXT NOT NULL,
            cc_json TEXT NOT NULL,
            bcc_json TEXT NOT NULL,
            subject TEXT NOT NULL,
            body_text TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('pending_review', 'sending', 'sent', 'failed')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            sent_message_id TEXT,
            FOREIGN KEY (account_id) REFERENCES mail_accounts(account_id) ON DELETE CASCADE
        );
        """
    )
