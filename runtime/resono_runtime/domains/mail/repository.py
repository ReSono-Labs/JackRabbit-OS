from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import sqlite3
import hashlib
from uuid import NAMESPACE_URL, uuid4, uuid5

from resono_runtime.domains.mail.models import MailAccount, MailAccountConfiguration
from resono_runtime.domains.mail.connector import RemoteFolderSnapshot
from resono_runtime.storage.database import RuntimeDatabase


MAX_MAIL_ACCOUNTS = 3


class MailAccountLimitError(ValueError):
    pass


class MailRepository:
    """Owns Mail SQL, including the transactional three-account boundary."""

    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def create_account(self, configuration: MailAccountConfiguration, credential_envelope: str) -> MailAccount:
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            count = int(connection.execute("SELECT COUNT(*) FROM mail_accounts").fetchone()[0])
            if count >= MAX_MAIL_ACCOUNTS:
                raise MailAccountLimitError("This R1 already has three Mail accounts.")
            connection.execute(
                """
                INSERT INTO connections(
                    connection_id, kind, label, enabled, health_state, source_owner,
                    created_at, updated_at
                ) VALUES (?, 'mail', ?, 1, 'unconfigured', 'mail', ?, ?)
                """,
                (configuration.account_id, configuration.label, now, now),
            )
            connection.execute(
                "INSERT INTO connection_credential_envelopes(connection_id, envelope, updated_at) VALUES (?, ?, ?)",
                (configuration.account_id, credential_envelope, now),
            )
            connection.execute(
                """
                INSERT INTO mail_accounts(
                    account_id, label, email_address, username,
                    imap_host, imap_port, imap_security,
                    smtp_host, smtp_port, smtp_security,
                    next_sync_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    configuration.account_id,
                    configuration.label,
                    configuration.email_address.casefold(),
                    configuration.username,
                    configuration.imap_host,
                    configuration.imap_port,
                    configuration.imap_security,
                    configuration.smtp_host,
                    configuration.smtp_port,
                    configuration.smtp_security,
                    now,
                    now,
                    now,
                ),
            )
            connection.commit()
        account = self.get_account(configuration.account_id)
        if account is None:
            raise RuntimeError("Mail account was not persisted.")
        return account

    def ensure_capacity(self) -> None:
        with self._database.connect() as connection:
            count = int(connection.execute("SELECT COUNT(*) FROM mail_accounts").fetchone()[0])
        if count >= MAX_MAIL_ACCOUNTS:
            raise MailAccountLimitError("This R1 already has three Mail accounts.")

    def get_account(self, account_id: str) -> MailAccount | None:
        with self._database.connect() as connection:
            row = connection.execute(_ACCOUNT_SELECT + " WHERE m.account_id = ?", (account_id,)).fetchone()
        return _account(row)

    def list_accounts(self) -> tuple[MailAccount, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(_ACCOUNT_SELECT + " ORDER BY m.label, m.account_id").fetchall()
        return tuple(item for row in rows if (item := _account(row)) is not None)

    def remove_account_local(self, account_id: str) -> bool:
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE connections SET enabled = 0, health_state = 'disabled', updated_at = ? WHERE connection_id = ?",
                (datetime.now(UTC).isoformat(), account_id),
            )
            cursor = connection.execute("DELETE FROM connections WHERE connection_id = ? AND kind = 'mail'", (account_id,))
            connection.execute("DELETE FROM connection_credential_envelopes WHERE connection_id = ?", (account_id,))
            connection.commit()
        return cursor.rowcount > 0

    def due_accounts(self, now: str) -> tuple[MailAccount, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                _ACCOUNT_SELECT
                + " WHERE c.enabled = 1 AND (m.next_sync_at IS NULL OR m.next_sync_at <= ?) ORDER BY m.next_sync_at, m.account_id",
                (now,),
            ).fetchall()
        return tuple(item for row in rows if (item := _account(row)) is not None)

    def begin_sync(self, account_id: str) -> str:
        run_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT last_sync_state, sync_lease_until FROM mail_accounts WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            if row is None or (row[0] == "syncing" and row[1] is not None and row[1] > now):
                raise ValueError("Mailbox synchronization is unavailable or already running.")
            connection.execute(
                "UPDATE mail_accounts SET last_sync_state = 'syncing', sync_lease_until = ?, last_sync_detail = NULL, updated_at = ? WHERE account_id = ?",
                ((datetime.now(UTC) + timedelta(minutes=10)).isoformat(), now, account_id),
            )
            connection.execute(
                "INSERT INTO mail_sync_runs(run_id, account_id, started_at, state) VALUES (?, ?, ?, 'running')",
                (run_id, account_id, now),
            )
            connection.commit()
        return run_id

    def store_snapshot(self, account_id: str, snapshot: RemoteFolderSnapshot) -> int:
        folder_id = str(uuid5(NAMESPACE_URL, f"mail-folder:{account_id}:{snapshot.folder.name}"))
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO mail_folders(
                    folder_id, account_id, remote_name, delimiter, attributes_json,
                    special_use, uid_validity, uid_next, last_synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, remote_name) DO UPDATE SET
                    delimiter = excluded.delimiter,
                    attributes_json = excluded.attributes_json,
                    special_use = excluded.special_use,
                    uid_validity = excluded.uid_validity,
                    uid_next = excluded.uid_next,
                    last_synced_at = excluded.last_synced_at,
                    sync_cursor_uid = CASE
                        WHEN mail_folders.uid_validity IS NOT excluded.uid_validity THEN 0
                        ELSE mail_folders.sync_cursor_uid
                    END,
                    sync_complete = 0
                """,
                (
                    folder_id, account_id, snapshot.folder.name, snapshot.folder.delimiter,
                    json.dumps(snapshot.folder.attributes), snapshot.folder.special_use,
                    snapshot.uid_validity, snapshot.uid_next, now,
                ),
            )
            remote_keys: list[tuple[int, int]] = []
            for message in snapshot.messages:
                message_id = str(uuid5(NAMESPACE_URL, f"mail-message:{folder_id}:{snapshot.uid_validity}:{message.uid}"))
                remote_keys.append((snapshot.uid_validity, message.uid))
                connection.execute(
                    """
                    INSERT INTO mail_messages(
                        message_id, account_id, folder_id, uid_validity, remote_uid,
                        rfc_message_id, subject, sender_json, recipients_json, sent_at,
                        received_at, flags_json, body_text, body_html, raw_size, synchronized_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(folder_id, uid_validity, remote_uid) DO UPDATE SET
                        rfc_message_id = excluded.rfc_message_id,
                        subject = excluded.subject,
                        sender_json = excluded.sender_json,
                        recipients_json = excluded.recipients_json,
                        sent_at = excluded.sent_at,
                        received_at = excluded.received_at,
                        flags_json = excluded.flags_json,
                        body_text = excluded.body_text,
                        body_html = excluded.body_html,
                        raw_size = excluded.raw_size,
                        synchronized_at = excluded.synchronized_at
                    """,
                    (
                        message_id, account_id, folder_id, snapshot.uid_validity, message.uid,
                        message.rfc_message_id, message.subject, json.dumps(message.sender),
                        json.dumps(message.recipients), message.sent_at, message.received_at,
                        json.dumps(message.flags), message.body_text, message.body_html,
                        message.raw_size, now,
                    ),
                )
                connection.execute("DELETE FROM mail_attachments WHERE message_id = ?", (message_id,))
                connection.executemany(
                    """
                    INSERT INTO mail_attachments(
                        attachment_id, message_id, part_id, filename, content_type,
                        content_disposition, content_id, byte_size
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            str(uuid5(NAMESPACE_URL, f"mail-attachment:{message_id}:{item.part_id}")),
                            message_id, item.part_id, item.filename, item.content_type,
                            item.content_disposition, item.content_id, item.byte_size,
                        )
                        for item in message.attachments
                    ],
                )
            if remote_keys:
                connection.execute(
                    "UPDATE mail_folders SET sync_cursor_uid = MAX(sync_cursor_uid, ?) WHERE folder_id = ?",
                    (max(uid for _, uid in remote_keys), folder_id),
                )
            connection.commit()
        return len(snapshot.messages)

    def folder_progress(self, account_id: str, remote_name: str, uid_validity: int) -> int:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT sync_cursor_uid, uid_validity FROM mail_folders WHERE account_id = ? AND remote_name = ?",
                (account_id, remote_name),
            ).fetchone()
        return int(row[0]) if row is not None and int(row[1] or 0) == uid_validity else 0

    def complete_folder(self, account_id: str, snapshot: RemoteFolderSnapshot, remote_uids: tuple[int, ...]) -> None:
        folder_id = str(uuid5(NAMESPACE_URL, f"mail-folder:{account_id}:{snapshot.folder.name}"))
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if remote_uids:
                connection.execute("CREATE TEMP TABLE mail_remote_uids(uid INTEGER PRIMARY KEY)")
                connection.executemany(
                    "INSERT INTO mail_remote_uids(uid) VALUES (?)",
                    ((uid,) for uid in remote_uids),
                )
                connection.execute(
                    """
                    DELETE FROM mail_messages
                    WHERE folder_id = ? AND (
                        uid_validity != ? OR
                        NOT EXISTS (
                            SELECT 1 FROM mail_remote_uids remote
                            WHERE remote.uid = mail_messages.remote_uid
                        )
                    )
                    """,
                    (folder_id, snapshot.uid_validity),
                )
                connection.execute("DROP TABLE mail_remote_uids")
            else:
                connection.execute("DELETE FROM mail_messages WHERE folder_id = ?", (folder_id,))
            connection.execute(
                "UPDATE mail_folders SET sync_cursor_uid = 0, sync_complete = 1, last_synced_at = ? WHERE folder_id = ?",
                (datetime.now(UTC).isoformat(), folder_id),
            )
            connection.commit()

    def reconcile_folders(self, account_id: str, remote_names: tuple[str, ...]) -> None:
        """Remove local folders only after one complete remote folder pass."""
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("CREATE TEMP TABLE mail_remote_folders(name TEXT PRIMARY KEY)")
            connection.executemany(
                "INSERT INTO mail_remote_folders(name) VALUES (?)",
                ((name,) for name in remote_names),
            )
            connection.execute(
                """
                DELETE FROM mail_folders
                WHERE account_id = ? AND NOT EXISTS (
                    SELECT 1 FROM mail_remote_folders remote
                    WHERE remote.name = mail_folders.remote_name
                )
                """,
                (account_id,),
            )
            connection.execute("DROP TABLE mail_remote_folders")
            connection.commit()

    def finish_sync(self, account_id: str, run_id: str, *, state: str, folders: int, messages: int, detail: str | None) -> None:
        now = datetime.now(UTC)
        next_sync = (now + timedelta(seconds=300 if state == "ready" else 15)).isoformat()
        terminal = "ready" if state == "ready" else "pending" if state == "timed_out" else "failed"
        connection_health = "ready" if terminal == "ready" else "syncing" if terminal == "pending" else "failed"
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE mail_sync_runs SET finished_at = ?, state = ?, folders_seen = ?, messages_seen = ?, detail = ? WHERE run_id = ? AND account_id = ?",
                (now.isoformat(), state, folders, messages, detail, run_id, account_id),
            )
            connection.execute(
                """
                UPDATE mail_accounts SET last_sync_at = ?, next_sync_at = ?,
                    last_sync_state = ?, last_sync_detail = ?, sync_lease_until = NULL, updated_at = ?
                WHERE account_id = ?
                """,
                (now.isoformat(), next_sync, terminal, detail, now.isoformat(), account_id),
            )
            connection.execute(
                "UPDATE connections SET health_state = ?, health_detail = ?, updated_at = ? WHERE connection_id = ?",
                (connection_health, detail, now.isoformat(), account_id),
            )
            connection.commit()

    def list_folders(self, account_id: str) -> tuple[dict[str, object], ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT folder_id, remote_name, delimiter, attributes_json, special_use,
                       uid_validity, uid_next, last_synced_at
                FROM mail_folders f WHERE account_id = ? AND """ + _VOICE_VISIBLE_FOLDER + " ORDER BY remote_name",
                (account_id,),
            ).fetchall()
        return tuple(
            {
                "folderId": row[0], "name": row[1], "delimiter": row[2],
                "attributes": json.loads(row[3]), "specialUse": row[4],
                "uidValidity": row[5], "uidNext": row[6], "lastSyncedAt": row[7],
            }
            for row in rows
        )

    def list_messages(self, account_id: str, *, folder_id: str | None = None, query: str | None = None, unread_only: bool = False, limit: int = 25) -> tuple[dict[str, object], ...]:
        clauses = ["m.account_id = ?", _VOICE_VISIBLE_FOLDER, "m.flags_json NOT LIKE '%\\\\Deleted%'"]
        parameters: list[object] = [account_id]
        if folder_id:
            clauses.append("m.folder_id = ?")
            parameters.append(folder_id)
        else:
            clauses.append("(f.special_use = 'inbox' OR UPPER(f.remote_name) = 'INBOX')")
        if query:
            clauses.append("(m.subject LIKE ? OR m.body_text LIKE ? OR m.sender_json LIKE ?)")
            pattern = f"%{query}%"
            parameters.extend((pattern, pattern, pattern))
        if unread_only:
            clauses.append("m.flags_json NOT LIKE '%\\\\Seen%'")
        parameters.append(max(1, min(limit, 100)))
        with self._database.connect() as connection:
            rows = connection.execute(
                """
                SELECT m.message_id, m.folder_id, f.remote_name, m.remote_uid,
                       m.rfc_message_id, m.subject, m.sender_json, m.recipients_json,
                       m.sent_at, m.received_at, m.flags_json, m.body_text, m.body_html,
                       m.raw_size, m.synchronized_at
                FROM mail_messages m JOIN mail_folders f ON f.folder_id = m.folder_id
                WHERE """ + " AND ".join(clauses) + " ORDER BY COALESCE(m.received_at, m.sent_at) DESC LIMIT ?",
                parameters,
            ).fetchall()
        return tuple(_message_view(row, include_body=False) for row in rows)

    def read_message(self, account_id: str, message_id: str) -> dict[str, object] | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT m.message_id, m.folder_id, f.remote_name, m.remote_uid,
                       m.rfc_message_id, m.subject, m.sender_json, m.recipients_json,
                       m.sent_at, m.received_at, m.flags_json, m.body_text, m.body_html,
                       m.raw_size, m.synchronized_at
                FROM mail_messages m JOIN mail_folders f ON f.folder_id = m.folder_id
                WHERE m.account_id = ? AND m.message_id = ? AND """ + _VOICE_VISIBLE_FOLDER + " AND m.flags_json NOT LIKE '%\\\\Deleted%'",
                (account_id, message_id),
            ).fetchone()
        return _message_view(row, include_body=True) if row is not None else None

    def message_target(self, account_id: str, message_id: str) -> tuple[str, int] | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT f.remote_name, m.remote_uid
                FROM mail_messages m JOIN mail_folders f ON f.folder_id = m.folder_id
                WHERE m.account_id = ? AND m.message_id = ? AND """ + _VOICE_VISIBLE_FOLDER + " AND m.flags_json NOT LIKE '%\\\\Deleted%'",
                (account_id, message_id),
            ).fetchone()
        return (str(row[0]), int(row[1])) if row is not None else None

    def attachment(self, account_id: str, attachment_id: str) -> dict[str, object] | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT a.attachment_id, a.message_id, a.part_id, a.filename,
                       a.content_type, a.content_disposition, a.content_id, a.byte_size
                FROM mail_attachments a
                JOIN mail_messages m ON m.message_id = a.message_id
                JOIN mail_folders f ON f.folder_id = m.folder_id
                WHERE m.account_id = ? AND a.attachment_id = ? AND """ + _VOICE_VISIBLE_FOLDER + " AND m.flags_json NOT LIKE '%\\\\Deleted%'",
                (account_id, attachment_id),
            ).fetchone()
        if row is None:
            return None
        return {"attachmentId": row[0], "messageId": row[1], "partId": row[2], "filename": row[3], "contentType": row[4], "contentDisposition": row[5], "contentId": row[6], "byteSize": row[7]}

    def attachment_target(self, account_id: str, attachment_id: str) -> tuple[str, int, str, int, str] | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """
                SELECT f.remote_name, m.remote_uid, a.part_id, a.byte_size, a.content_type
                FROM mail_attachments a
                JOIN mail_messages m ON m.message_id = a.message_id
                JOIN mail_folders f ON f.folder_id = m.folder_id
                WHERE m.account_id = ? AND a.attachment_id = ? AND """ + _VOICE_VISIBLE_FOLDER + " AND m.flags_json NOT LIKE '%\\\\Deleted%'",
                (account_id, attachment_id),
            ).fetchone()
        return (str(row[0]), int(row[1]), str(row[2]), int(row[3]), str(row[4])) if row else None

    def create_draft(self, account_id: str, *, recipients: tuple[str, ...], subject: str, body: str, voice_session_id: str, tool_call_id: str, compose_utterance_id: int) -> dict[str, object]:
        draft_id = str(uuid4())
        canonical = json.dumps({"accountId": account_id, "to": recipients, "subject": subject, "body": body}, sort_keys=True, separators=(",", ":"))
        content_hash = hashlib.sha256(canonical.encode()).hexdigest()
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute(
                """
                INSERT INTO mail_drafts(
                    draft_id, account_id, recipients_json, cc_json, bcc_json,
                    subject, body_text, content_hash, state, created_at, updated_at,
                    voice_session_id, compose_tool_call_id, compose_utterance_id
                ) VALUES (?, ?, ?, '[]', '[]', ?, ?, ?, 'pending_review', ?, ?, ?, ?, ?)
                """,
                (draft_id, account_id, json.dumps(recipients), subject, body, content_hash, now, now, voice_session_id, tool_call_id, compose_utterance_id),
            )
            connection.commit()
        return {"draftId": draft_id, "accountId": account_id, "to": list(recipients), "subject": subject, "body": body, "contentHash": content_hash, "state": "pending_review"}

    def claim_draft(self, draft_id: str, *, account_id: str, content_hash: str, voice_session_id: str, approval_utterance_id: int) -> dict[str, object] | None:
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT recipients_json, subject, body_text, content_hash, state, voice_session_id, compose_utterance_id
                FROM mail_drafts WHERE draft_id = ? AND account_id = ?
                """,
                (draft_id, account_id),
            ).fetchone()
            if row is None or row[3] != content_hash or row[4] != "pending_review" or row[5] != voice_session_id or approval_utterance_id <= int(row[6]):
                connection.rollback()
                return None
            connection.execute("UPDATE mail_drafts SET state = 'sending', updated_at = ? WHERE draft_id = ?", (now, draft_id))
            connection.commit()
        return {"to": tuple(json.loads(row[0])), "subject": row[1], "body": row[2]}

    def finish_draft(self, draft_id: str, *, sent: bool, sent_message_id: str | None = None) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE mail_drafts SET state = ?, sent_message_id = ?, updated_at = ? WHERE draft_id = ? AND state = 'sending'",
                ("sent" if sent else "failed", sent_message_id, datetime.now(UTC).isoformat(), draft_id),
            )
            connection.commit()

    def record_smtp_sent(self, draft_id: str, *, message_id: str, wire: bytes) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE mail_drafts SET state='sent', sent_message_id=?, sent_mime=?, sent_append_state='pending', updated_at=? WHERE draft_id=? AND state='sending'",
                (message_id, wire, datetime.now(UTC).isoformat(), draft_id),
            )
            connection.commit()

    def record_sent_append(self, draft_id: str, *, ready: bool, detail: str | None = None) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "UPDATE mail_drafts SET sent_append_state=?, sent_append_detail=?, sent_mime=CASE WHEN ? THEN NULL ELSE sent_mime END, updated_at=? WHERE draft_id=? AND state='sent'",
                ("ready" if ready else "failed", detail, int(ready), datetime.now(UTC).isoformat(), draft_id),
            )
            connection.commit()

    def pending_sent_appends(self, limit: int = 10) -> tuple[tuple[str, str, bytes], ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                "SELECT draft_id, account_id, sent_mime FROM mail_drafts WHERE state='sent' AND sent_append_state IN ('pending','failed') AND sent_mime IS NOT NULL ORDER BY updated_at LIMIT ?",
                (limit,),
            ).fetchall()
        return tuple((str(row[0]), str(row[1]), bytes(row[2])) for row in rows)


_VOICE_VISIBLE_FOLDER = """
COALESCE(f.special_use, '') <> 'trash'
AND LOWER(f.remote_name) NOT LIKE '%trash%'
AND LOWER(f.remote_name) NOT LIKE '%deleted%'
AND LOWER(f.remote_name) NOT LIKE '%/bin'
AND LOWER(f.remote_name) NOT IN ('bin', 'recycle bin')
"""

_ACCOUNT_SELECT = """
SELECT m.account_id, m.label, m.email_address, m.username,
       m.imap_host, m.imap_port, m.imap_security,
       m.smtp_host, m.smtp_port, m.smtp_security,
       c.enabled,
       EXISTS(SELECT 1 FROM connection_credential_envelopes e WHERE e.connection_id = m.account_id),
       m.next_sync_at, m.last_sync_at, m.last_sync_state, m.last_sync_detail,
       m.created_at, m.updated_at
FROM mail_accounts m JOIN connections c ON c.connection_id = m.account_id
"""


def _account(row: sqlite3.Row | None) -> MailAccount | None:
    if row is None:
        return None
    return MailAccount(
        configuration=MailAccountConfiguration(
            account_id=row[0], label=row[1], email_address=row[2], username=row[3],
            imap_host=row[4], imap_port=row[5], imap_security=row[6],
            smtp_host=row[7], smtp_port=row[8], smtp_security=row[9],
        ),
        enabled=bool(row[10]), credential_present=bool(row[11]), next_sync_at=row[12],
        last_sync_at=row[13], last_sync_state=row[14], last_sync_detail=row[15],
        created_at=row[16], updated_at=row[17],
    )


def _message_view(row: object, *, include_body: bool) -> dict[str, object]:
    result: dict[str, object] = {
        "messageId": row[0], "folderId": row[1], "folder": row[2], "remoteUid": row[3],
        "rfcMessageId": row[4], "subject": row[5], "from": json.loads(row[6]),
        "recipients": json.loads(row[7]), "sentAt": row[8], "receivedAt": row[9],
        "flags": json.loads(row[10]), "rawSize": row[13], "synchronizedAt": row[14],
    }
    if include_body:
        result["bodyText"] = row[11]
        result["bodyHtml"] = row[12]
    return result
