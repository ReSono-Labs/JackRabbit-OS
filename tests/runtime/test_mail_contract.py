from __future__ import annotations

import tempfile
import unittest
import inspect
import hashlib
from contextlib import contextmanager
from pathlib import Path

from resono_runtime.domains.mail.connector import RemoteFolder, RemoteFolderIndex, RemoteFolderSnapshot, RemoteMessage
from resono_runtime.domains.mail.repository import MailAccountLimitError, MailRepository
from resono_runtime.domains.mail.service import MailService
from resono_runtime.domains.mail.tools import MAIL_TOOL_NAMES
from resono_runtime.domains.mail import tools as mail_tools
from resono_runtime.security.credentials import ConnectionCredentialEnvelopes
from resono_runtime.storage.connection_credentials import ConnectionCredentialRepository
from resono_runtime.storage.database import RuntimeDatabase


class MailContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = RuntimeDatabase(Path(self.temporary.name) / "runtime.sqlite3")
        self.database.migrate()
        self.repository = MailRepository(self.database)
        self.connector = _Connector()
        self.bridge = _Bridge()
        self.service = MailService(
            self.repository,
            ConnectionCredentialRepository(self.database),
            ConnectionCredentialEnvelopes(self.bridge),
            self.connector,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_three_accounts_and_full_paged_sync(self) -> None:
        accounts = [self._connect(index) for index in range(3)]
        with self.assertRaises(MailAccountLimitError):
            self._connect(3)
        self.service.sync(accounts[0].configuration.account_id)
        messages = self.repository.list_messages(accounts[0].configuration.account_id, limit=100)
        self.assertEqual(12, len(messages))
        self.assertGreaterEqual(self.connector.fetch_count, 2)
        self.assertEqual("ready", self.repository.get_account(accounts[0].configuration.account_id).last_sync_state)
        self.connector.folders = ()
        self.service.sync(accounts[0].configuration.account_id)
        self.assertEqual((), self.repository.list_folders(accounts[0].configuration.account_id))

    def test_sqlite_contains_only_an_opaque_credential_envelope(self) -> None:
        account = self._connect(0)
        with self.database.connect() as connection:
            envelope = str(connection.execute(
                "SELECT envelope FROM connection_credential_envelopes WHERE connection_id = ?",
                (account.configuration.account_id,),
            ).fetchone()[0])
        self.assertTrue(envelope.startswith("test-sealed:"))
        self.assertNotIn("secret", envelope)
        self.assertNotIn("password", envelope)
        self.assertEqual("secret", self.service.credentials(account.configuration.account_id).password)

    def test_confirmed_send_is_single_use_and_sent_copy_retries_without_resend(self) -> None:
        account = self._connect(0)
        draft = self.service.prepare_send(
            account.configuration.account_id,
            recipients=("person@example.net",),
            subject="Review",
            body="Approved body",
            voice_session_id="voice-session",
            tool_call_id="compose-call",
            user_utterance_id=1,
        )
        with self.assertRaisesRegex(ValueError, "stale, changed, or already used"):
            self.service.confirm_send(
                account.configuration.account_id,
                draft_id=draft["draftId"],
                content_hash=draft["contentHash"],
                voice_session_id="voice-session",
                user_utterance="Yes, send it.",
                user_utterance_id=1,
            )
        with self.assertRaisesRegex(ValueError, "not explicitly approved"):
            self.service.confirm_send(
                account.configuration.account_id,
                draft_id=draft["draftId"],
                content_hash=draft["contentHash"],
                voice_session_id="voice-session",
                user_utterance="Please draft that message.",
                user_utterance_id=2,
            )
        self.connector.fail_first_append = True
        result = self.service.confirm_send(
            account.configuration.account_id,
            draft_id=draft["draftId"],
            content_hash=draft["contentHash"],
            voice_session_id="voice-session",
            user_utterance="Yes, send it.",
            user_utterance_id=2,
        )
        self.assertEqual("sent_unfiled", result["state"])
        with self.assertRaises(ValueError):
            self.service.confirm_send(
                account.configuration.account_id,
                draft_id=draft["draftId"],
                content_hash=draft["contentHash"],
                voice_session_id="voice-session",
                user_utterance="Yes, send it.",
                user_utterance_id=3,
            )
        self.service.retry_sent_appends()
        self.assertEqual(1, self.connector.smtp_count)
        self.assertEqual(2, self.connector.append_count)

    def test_destructive_mail_capabilities_are_absent(self) -> None:
        forbidden = ("delete", "trash", "expunge", "purge", "empty_trash")
        self.assertFalse(any(term in name for name in MAIL_TOOL_NAMES for term in forbidden))
        self.assertFalse(any(hasattr(self.connector, name) for name in ("delete", "trash", "expunge", "purge")))
        tool_source = inspect.getsource(mail_tools)
        self.assertNotIn('"approved"', tool_source)
        self.assertIn("context.user_utterance", tool_source)

    def _connect(self, index: int):
        return self.service.connect_account(
            label=f"Account {index}",
            email_address=f"user{index}@example.com",
            username=f"user{index}",
            password="secret",
            imap_host="imap.example.com",
            imap_port=993,
            imap_security="tls",
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_security="tls",
        )


class _Bridge:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def sealConnectionCredential(self, record_name: str, plaintext: str) -> str:
        envelope = "test-sealed:" + hashlib.sha256(f"{record_name}\0{plaintext}".encode()).hexdigest()
        self.values[envelope] = plaintext
        return envelope

    def openConnectionCredential(self, record_name: str, envelope: str) -> str:
        del record_name
        return self.values[envelope]


class _Connector:
    def __init__(self) -> None:
        self.fetch_count = 0
        self.smtp_count = 0
        self.append_count = 0
        self.fail_first_append = False
        self.folders = (RemoteFolder("INBOX", "/", ("\\Inbox",), "inbox"),)

    def validate(self, credentials) -> None:
        del credentials

    @contextmanager
    def imap_session(self, credentials):
        del credentials
        yield object()

    def list_folders(self, client):
        del client
        return self.folders

    def index_folder(self, client, folder):
        del client
        return RemoteFolderIndex(folder, 1, 13, tuple(range(1, 13)))

    def fetch_page(self, client, index, uids, *, deadline):
        del client, deadline
        self.fetch_count += 1
        messages = tuple(
            RemoteMessage(uid, f"<{uid}@example.com>", f"Message {uid}", (("Sender", "sender@example.com"),), (("User", "user@example.com"),), None, None, (), "Body", None, 4, ())
            for uid in uids
        )
        return RemoteFolderSnapshot(index.folder, index.uid_validity, index.uid_next, messages)

    def send_smtp(self, credentials, recipients, subject, body):
        del credentials, recipients, subject, body
        self.smtp_count += 1
        return "<sent@example.com>", b"exact mime"

    def append_sent(self, credentials, wire):
        del credentials, wire
        self.append_count += 1
        if self.fail_first_append and self.append_count == 1:
            raise RuntimeError("append failed")


if __name__ == "__main__":
    unittest.main()
