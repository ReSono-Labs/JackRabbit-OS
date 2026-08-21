from __future__ import annotations

from dataclasses import asdict
import json
import base64
from time import monotonic
from uuid import uuid4

from resono_runtime.domains.mail.connector import ImapSmtpConnector, MailCredentials
from resono_runtime.domains.mail.models import MailAccount, MailAccountConfiguration
from resono_runtime.domains.mail.repository import MailRepository
from resono_runtime.security.credentials import ConnectionCredentialEnvelopes
from resono_runtime.storage.connection_credentials import ConnectionCredentialRepository


SYNC_PAGE_SIZE = 10
SYNC_WORK_SECONDS = 45


class MailService:
    def __init__(
        self,
        repository: MailRepository,
        credential_store: ConnectionCredentialRepository,
        envelopes: ConnectionCredentialEnvelopes,
        connector: ImapSmtpConnector,
    ) -> None:
        self._repository = repository
        self._credential_store = credential_store
        self._envelopes = envelopes
        self._connector = connector

    def connect_account(self, *, label: str, email_address: str, username: str, password: str, imap_host: str, imap_port: int, imap_security: str, smtp_host: str, smtp_port: int, smtp_security: str) -> MailAccount:
        self._repository.ensure_capacity()
        account_id = str(uuid4())
        credentials = MailCredentials(email_address.casefold(), username, password, imap_host, imap_port, imap_security, smtp_host, smtp_port, smtp_security)
        self._connector.validate(credentials)
        envelope = self._envelopes.seal(account_id, json.dumps(asdict(credentials), separators=(",", ":")))
        configuration = MailAccountConfiguration(account_id, label.strip(), email_address.casefold(), username, imap_host, imap_port, imap_security, smtp_host, smtp_port, smtp_security)
        return self._repository.create_account(configuration, envelope)

    def credentials(self, account_id: str) -> MailCredentials:
        envelope = self._credential_store.get_envelope(account_id)
        if envelope is None:
            raise ValueError("Mail account credentials are unavailable.")
        value = json.loads(self._envelopes.open(account_id, envelope))
        return MailCredentials(**value)

    def sync(self, account_id: str) -> None:
        run_id = self._repository.begin_sync(account_id)
        folders_seen = 0
        messages_seen = 0
        started = monotonic()
        try:
            credentials = self.credentials(account_id)
            with self._connector.imap_session(credentials) as client:
                folders = self._connector.list_folders(client)
                for folder in folders:
                    index = self._connector.index_folder(client, folder)
                    metadata = self._connector.fetch_page(
                        client,
                        index,
                        (),
                        deadline=started + SYNC_WORK_SECONDS,
                    )
                    self._repository.store_snapshot(account_id, metadata)
                    cursor = self._repository.folder_progress(account_id, folder.name, index.uid_validity)
                    remaining = tuple(uid for uid in index.uids if uid > cursor)
                    while remaining:
                        page = self._connector.fetch_page(
                            client,
                            index,
                            remaining[:SYNC_PAGE_SIZE],
                            deadline=started + SYNC_WORK_SECONDS,
                        )
                        if not page.messages:
                            raise TimeoutError("Mailbox synchronization yielded for another account.")
                        messages_seen += self._repository.store_snapshot(account_id, page)
                        cursor = page.messages[-1].uid
                        remaining = tuple(uid for uid in remaining if uid > cursor)
                    self._repository.complete_folder(
                        account_id,
                        metadata,
                        index.uids,
                    )
                    folders_seen += 1
                self._repository.reconcile_folders(
                    account_id,
                    tuple(folder.name for folder in folders),
                )
            self._repository.finish_sync(account_id, run_id, state="ready", folders=folders_seen, messages=messages_seen, detail=None)
        except TimeoutError:
            self._repository.finish_sync(account_id, run_id, state="timed_out", folders=folders_seen, messages=messages_seen, detail="Synchronization is incomplete and will resume shortly.")
        except Exception:
            self._repository.finish_sync(account_id, run_id, state="failed", folders=folders_seen, messages=messages_seen, detail="Mailbox synchronization failed.")
            raise

    def prepare_send(self, account_id: str, *, recipients: tuple[str, ...], subject: str, body: str, voice_session_id: str, tool_call_id: str, user_utterance_id: int) -> dict[str, object]:
        if not voice_session_id or not tool_call_id or user_utterance_id <= 0:
            raise ValueError("A trusted Voice invocation is required to compose Mail.")
        if not recipients or any("@" not in value for value in recipients):
            raise ValueError("At least one valid recipient is required.")
        if not subject.strip() or not body.strip():
            raise ValueError("Mail subject and body are required.")
        return self._repository.create_draft(account_id, recipients=recipients, subject=subject.strip(), body=body.strip(), voice_session_id=voice_session_id, tool_call_id=tool_call_id, compose_utterance_id=user_utterance_id)

    def confirm_send(self, account_id: str, *, draft_id: str, content_hash: str, voice_session_id: str, user_utterance: str, user_utterance_id: int) -> dict[str, object]:
        if not voice_session_id:
            raise ValueError("A trusted Voice invocation is required to send Mail.")
        claim = self._repository.claim_draft(draft_id, account_id=account_id, content_hash=content_hash, voice_session_id=voice_session_id, approval_utterance_id=user_utterance_id)
        if claim is None:
            raise ValueError("The reviewed Mail draft is stale, changed, or already used.")
        try:
            credentials = self.credentials(account_id)
            message_id, wire = self._connector.send_smtp(credentials, claim["to"], claim["subject"], claim["body"])
        except Exception:
            self._repository.finish_draft(draft_id, sent=False)
            raise
        self._repository.record_smtp_sent(draft_id, message_id=message_id, wire=wire)
        try:
            self._connector.append_sent(credentials, wire)
        except Exception:
            self._repository.record_sent_append(draft_id, ready=False, detail="Sent-folder copy is pending retry.")
            return {"state": "sent_unfiled", "draftId": draft_id, "messageId": message_id}
        self._repository.record_sent_append(draft_id, ready=True)
        return {"state": "sent", "draftId": draft_id, "messageId": message_id}

    def retry_sent_appends(self) -> None:
        for draft_id, account_id, wire in self._repository.pending_sent_appends():
            try:
                self._connector.append_sent(self.credentials(account_id), wire)
            except Exception:
                self._repository.record_sent_append(draft_id, ready=False, detail="Sent-folder copy retry failed.")
            else:
                self._repository.record_sent_append(draft_id, ready=True)

    def set_read_state(self, account_id: str, message_id: str, *, read: bool) -> None:
        folder, uid = self._required_target(account_id, message_id)
        self._connector.set_read_state(self.credentials(account_id), folder, uid, read=read)

    def read_attachment(self, account_id: str, attachment_id: str) -> dict[str, object]:
        metadata = self._repository.attachment(account_id, attachment_id)
        target = self._repository.attachment_target(account_id, attachment_id)
        if metadata is None or target is None:
            raise ValueError("Mail attachment was not found.")
        folder, uid, part_id, byte_size, content_type = target
        content = self._connector.fetch_attachment(self.credentials(account_id), folder, uid, part_id, byte_size, content_type)
        result = dict(metadata)
        if content_type.casefold() in {"text/plain", "text/html"}:
            result["text"] = content.decode("utf-8", errors="replace")
        else:
            result["base64"] = base64.b64encode(content).decode("ascii")
        return result

    def move_message(self, account_id: str, message_id: str, destination: str) -> None:
        folder, uid = self._required_target(account_id, message_id)
        self._connector.move(self.credentials(account_id), folder, destination, uid)

    def archive_message(self, account_id: str, message_id: str) -> None:
        archive = next((item for item in self._repository.list_folders(account_id) if item["specialUse"] == "archive"), None)
        if archive is None:
            raise ValueError("This mailbox has no safe Archive folder.")
        self.move_message(account_id, message_id, str(archive["name"]))

    def create_folder(self, account_id: str, name: str) -> None:
        self._connector.create_folder(self.credentials(account_id), name)

    def rename_folder(self, account_id: str, source: str, destination: str) -> None:
        self._connector.rename_folder(self.credentials(account_id), source, destination)

    def _required_target(self, account_id: str, message_id: str) -> tuple[str, int]:
        target = self._repository.message_target(account_id, message_id)
        if target is None:
            raise ValueError("Mail message was not found in the local synchronized store.")
        return target
