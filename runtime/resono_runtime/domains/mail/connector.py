from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.policy import default
from email.utils import format_datetime, getaddresses, make_msgid, parsedate_to_datetime
import imaplib
import re
import smtplib
import ssl
from time import monotonic
from typing import Iterator

from resono_runtime.security.outbound import validate_public_host


PROVIDER_TIMEOUT_SECONDS = 20
SYNC_LIMIT_SECONDS = 600
MAX_ATTACHMENT_BYTES = 1024 * 1024
SUPPORTED_ATTACHMENT_TYPES = frozenset({"text/plain", "text/html", "application/pdf", "image/jpeg", "image/png"})
_FORBIDDEN_FOLDER_TERMS = frozenset({"trash", "junk", "spam", "bin"})


@dataclass(frozen=True, slots=True)
class MailCredentials:
    email_address: str
    username: str
    password: str
    imap_host: str
    imap_port: int
    imap_security: str
    smtp_host: str
    smtp_port: int
    smtp_security: str


@dataclass(frozen=True, slots=True)
class RemoteFolder:
    name: str
    delimiter: str | None
    attributes: tuple[str, ...]
    special_use: str | None


@dataclass(frozen=True, slots=True)
class RemoteAttachment:
    part_id: str
    filename: str | None
    content_type: str
    content_disposition: str | None
    content_id: str | None
    byte_size: int


@dataclass(frozen=True, slots=True)
class RemoteMessage:
    uid: int
    rfc_message_id: str | None
    subject: str
    sender: tuple[tuple[str, str], ...]
    recipients: tuple[tuple[str, str], ...]
    sent_at: str | None
    received_at: str | None
    flags: tuple[str, ...]
    body_text: str | None
    body_html: str | None
    raw_size: int
    attachments: tuple[RemoteAttachment, ...]


@dataclass(frozen=True, slots=True)
class RemoteFolderSnapshot:
    folder: RemoteFolder
    uid_validity: int
    uid_next: int | None
    messages: tuple[RemoteMessage, ...]


@dataclass(frozen=True, slots=True)
class RemoteFolderIndex:
    folder: RemoteFolder
    uid_validity: int
    uid_next: int | None
    uids: tuple[int, ...]


class MailProviderError(RuntimeError):
    pass


class ImapSmtpConnector:
    """Real provider connector with no fallback mutation path."""

    def validate(self, credentials: MailCredentials) -> None:
        with self.imap_session(credentials):
            pass
        with self.smtp_session(credentials):
            pass

    @contextmanager
    def imap_session(self, credentials: MailCredentials) -> Iterator[imaplib.IMAP4]:
        host = validate_public_host(credentials.imap_host, credentials.imap_port)
        context = ssl.create_default_context()
        if credentials.imap_security == "tls":
            client: imaplib.IMAP4 = imaplib.IMAP4_SSL(
                host, credentials.imap_port, ssl_context=context, timeout=PROVIDER_TIMEOUT_SECONDS
            )
        elif credentials.imap_security == "starttls":
            client = imaplib.IMAP4(host, credentials.imap_port, timeout=PROVIDER_TIMEOUT_SECONDS)
            client.starttls(ssl_context=context)
        else:
            raise MailProviderError("Unsupported IMAP security mode.")
        try:
            client.login(credentials.username, credentials.password)
            yield client
        finally:
            try:
                client.logout()
            except Exception:
                pass

    @contextmanager
    def smtp_session(self, credentials: MailCredentials) -> Iterator[smtplib.SMTP]:
        host = validate_public_host(credentials.smtp_host, credentials.smtp_port)
        context = ssl.create_default_context()
        if credentials.smtp_security == "tls":
            client: smtplib.SMTP = smtplib.SMTP_SSL(
                host, credentials.smtp_port, timeout=PROVIDER_TIMEOUT_SECONDS, context=context
            )
        elif credentials.smtp_security == "starttls":
            client = smtplib.SMTP(host, credentials.smtp_port, timeout=PROVIDER_TIMEOUT_SECONDS)
            client.ehlo()
            client.starttls(context=context)
            client.ehlo()
        else:
            raise MailProviderError("Unsupported SMTP security mode.")
        try:
            client.login(credentials.username, credentials.password)
            yield client
        finally:
            try:
                client.quit()
            except Exception:
                client.close()

    def list_folders(self, client: imaplib.IMAP4) -> tuple[RemoteFolder, ...]:
        status, values = client.list()
        if status != "OK":
            raise MailProviderError("Mailbox folders could not be listed.")
        folders = tuple(_parse_folder(value) for value in values or () if value)
        return tuple(folder for folder in folders if folder is not None)

    def snapshot_folder(
        self,
        client: imaplib.IMAP4,
        folder: RemoteFolder,
        *,
        started_at: float,
    ) -> RemoteFolderSnapshot:
        _within_sync_limit(started_at)
        status, _ = client.select(folder.name, readonly=True)
        if status != "OK":
            raise MailProviderError("Mailbox folder could not be opened.")
        uid_validity = _response_int(client, "UIDVALIDITY") or 1
        uid_next = _response_int(client, "UIDNEXT")
        status, values = client.uid("SEARCH", None, "ALL")
        if status != "OK":
            raise MailProviderError("Mailbox messages could not be enumerated.")
        uids = tuple(int(item) for item in (values[0].split() if values and values[0] else ()))
        messages: list[RemoteMessage] = []
        for uid in uids:
            _within_sync_limit(started_at)
            status, payload = client.uid("FETCH", str(uid), "(RFC822 FLAGS)")
            message = _parse_fetch(uid, status, payload)
            if message is not None:
                messages.append(message)
        return RemoteFolderSnapshot(folder, uid_validity, uid_next, tuple(messages))

    def index_folder(self, client: imaplib.IMAP4, folder: RemoteFolder) -> RemoteFolderIndex:
        status, _ = client.select(folder.name, readonly=True)
        if status != "OK":
            raise MailProviderError("Mailbox folder could not be opened.")
        uid_validity = _response_int(client, "UIDVALIDITY") or 1
        uid_next = _response_int(client, "UIDNEXT")
        status, values = client.uid("SEARCH", None, "ALL")
        if status != "OK":
            raise MailProviderError("Mailbox messages could not be enumerated.")
        uids = tuple(int(item) for item in (values[0].split() if values and values[0] else ()))
        return RemoteFolderIndex(folder, uid_validity, uid_next, uids)

    def fetch_page(self, client: imaplib.IMAP4, index: RemoteFolderIndex, uids: tuple[int, ...], *, deadline: float) -> RemoteFolderSnapshot:
        status, _ = client.select(index.folder.name, readonly=True)
        if status != "OK":
            raise MailProviderError("Mailbox folder could not be opened.")
        messages: list[RemoteMessage] = []
        for uid in uids:
            if monotonic() >= deadline:
                if messages:
                    break
                raise TimeoutError("Mailbox synchronization yielded for another account.")
            status, payload = client.uid("FETCH", str(uid), "(RFC822 FLAGS)")
            message = _parse_fetch(uid, status, payload)
            if message is not None:
                messages.append(message)
        return RemoteFolderSnapshot(index.folder, index.uid_validity, index.uid_next, tuple(messages))

    def set_read_state(self, credentials: MailCredentials, folder: str, uid: int, *, read: bool) -> None:
        with self.imap_session(credentials) as client:
            _select_mutable(client, folder)
            operation = "+FLAGS.SILENT" if read else "-FLAGS.SILENT"
            status, _ = client.uid("STORE", str(uid), operation, "(\\Seen)")
            if status != "OK":
                raise MailProviderError("Message read state could not be changed.")

    def move(self, credentials: MailCredentials, source: str, destination: str, uid: int) -> None:
        _safe_destination(destination)
        with self.imap_session(credentials) as client:
            _select_mutable(client, source)
            capabilities = {value.decode().upper() if isinstance(value, bytes) else str(value).upper() for value in client.capabilities}
            if "MOVE" not in capabilities:
                raise MailProviderError("This provider does not support safe server-side move.")
            status, _ = client.uid("MOVE", str(uid), destination)
            if status != "OK":
                raise MailProviderError("Message could not be moved.")

    def create_folder(self, credentials: MailCredentials, name: str) -> None:
        _safe_destination(name)
        with self.imap_session(credentials) as client:
            status, _ = client.create(name)
            if status != "OK":
                raise MailProviderError("Mailbox folder could not be created.")

    def rename_folder(self, credentials: MailCredentials, source: str, destination: str) -> None:
        _safe_destination(source)
        _safe_destination(destination)
        with self.imap_session(credentials) as client:
            status, _ = client.rename(source, destination)
            if status != "OK":
                raise MailProviderError("Mailbox folder could not be renamed.")

    def send_smtp(self, credentials: MailCredentials, recipients: tuple[str, ...], subject: str, body: str) -> tuple[str, bytes]:
        message = EmailMessage()
        message["From"] = credentials.email_address
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message["Date"] = format_datetime(datetime.now(UTC))
        message_id = make_msgid(domain=credentials.email_address.partition("@")[2] or None)
        message["Message-ID"] = message_id
        message.set_content(body)
        wire = message.as_bytes()
        with self.smtp_session(credentials) as client:
            client.send_message(message)
        return message_id, wire

    def append_sent(self, credentials: MailCredentials, wire: bytes) -> None:
        message_id = BytesParser(policy=default).parsebytes(wire).get("Message-ID")
        if not message_id:
            raise MailProviderError("Sent message is missing its stable Message-ID.")
        with self.imap_session(credentials) as client:
            sent = next((folder for folder in self.list_folders(client) if folder.special_use == "sent"), None)
            if sent is None:
                raise MailProviderError("Message was sent but the provider Sent folder could not be resolved.")
            status, _ = client.select(sent.name, readonly=True)
            if status != "OK":
                raise MailProviderError("The provider Sent folder could not be opened.")
            status, matches = client.uid("SEARCH", None, "HEADER", "Message-ID", str(message_id))
            if status == "OK" and any(part.strip() for part in matches or () if isinstance(part, bytes)):
                return
            status, _ = client.append(sent.name, "(\\Seen)", imaplib.Time2Internaldate(datetime.now(UTC)), wire)
            if status != "OK":
                raise MailProviderError("Message was sent but could not be recorded in the Sent folder.")

    def fetch_attachment(self, credentials: MailCredentials, folder: str, uid: int, part_id: str, expected_size: int, content_type: str) -> bytes:
        if expected_size > MAX_ATTACHMENT_BYTES:
            raise MailProviderError("Attachment exceeds the one-megabyte Voice read limit.")
        if content_type.casefold() not in SUPPORTED_ATTACHMENT_TYPES:
            raise MailProviderError("Attachment type is not supported for Voice reading.")
        with self.imap_session(credentials) as client:
            status, _ = client.select(folder, readonly=True)
            if status != "OK":
                raise MailProviderError("Mailbox folder could not be opened.")
            status, payload = client.uid("FETCH", str(uid), "(RFC822)")
            raw = next((item[1] for item in payload or () if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], bytes)), None)
            if status != "OK" or raw is None:
                raise MailProviderError("Attachment message could not be fetched.")
        message = BytesParser(policy=default).parsebytes(raw)
        parts = tuple(message.walk() if message.is_multipart() else (message,))
        try:
            content = parts[int(part_id)].get_payload(decode=True) or b""
        except (ValueError, IndexError):
            raise MailProviderError("Attachment part is unavailable.") from None
        if len(content) > MAX_ATTACHMENT_BYTES:
            raise MailProviderError("Attachment exceeds the one-megabyte Voice read limit.")
        return content


def _parse_folder(raw: bytes) -> RemoteFolder | None:
    text = raw.decode("utf-8", errors="replace")
    match = re.match(r'^\((?P<flags>[^)]*)\)\s+(?P<delimiter>"[^"]*"|NIL)\s+(?P<name>.+)$', text)
    if match is None:
        return None
    name = match.group("name").strip().strip('"')
    flags = tuple(value for value in match.group("flags").split() if value)
    lowered = {value.casefold() for value in flags}
    special = next((kind for token, kind in (("\\inbox", "inbox"), ("\\sent", "sent"), ("\\archive", "archive"), ("\\drafts", "drafts"), ("\\trash", "trash"), ("\\junk", "junk")) if token in lowered), None)
    if special is None and name.rsplit("/", 1)[-1].strip().casefold() in {"trash", "deleted", "deleted items", "bin", "recycle bin"}:
        special = "trash"
    delimiter_value = match.group("delimiter")
    delimiter = None if delimiter_value == "NIL" else delimiter_value.strip('"')
    return RemoteFolder(name, delimiter, flags, special)


def _parse_fetch(uid: int, status: str, payload: object) -> RemoteMessage | None:
    if status != "OK" or not isinstance(payload, list):
        return None
    raw = next((item[1] for item in payload if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], bytes)), None)
    if raw is None:
        return None
    flag_text = " ".join(item[0].decode("utf-8", errors="replace") for item in payload if isinstance(item, tuple) and isinstance(item[0], bytes))
    flag_match = re.search(r"FLAGS\s+\(([^)]*)\)", flag_text, re.IGNORECASE)
    flags = tuple(flag_match.group(1).split()) if flag_match else ()
    parsed = BytesParser(policy=default).parsebytes(raw)
    text, html, attachments = _parts(parsed)
    return RemoteMessage(
        uid=uid,
        rfc_message_id=parsed.get("Message-ID"),
        subject=_header(parsed.get("Subject")) or "(No subject)",
        sender=_addresses(parsed.get_all("From", [])),
        recipients=_addresses(parsed.get_all("To", []) + parsed.get_all("Cc", []) + parsed.get_all("Bcc", [])),
        sent_at=_date(parsed.get("Date")),
        received_at=_date(parsed.get("Date")),
        flags=flags,
        body_text=text,
        body_html=html,
        raw_size=len(raw),
        attachments=attachments,
    )


def _parts(message: Message) -> tuple[str | None, str | None, tuple[RemoteAttachment, ...]]:
    text: str | None = None
    html: str | None = None
    attachments: list[RemoteAttachment] = []
    for index, part in enumerate(message.walk() if message.is_multipart() else (message,)):
        disposition = part.get_content_disposition()
        content_type = part.get_content_type()
        payload = part.get_payload(decode=True) or b""
        if disposition == "attachment" or part.get_filename():
            attachments.append(RemoteAttachment(str(index), _header(part.get_filename()), content_type, disposition, part.get("Content-ID"), len(payload)))
        elif content_type == "text/plain" and text is None:
            text = part.get_content()
        elif content_type == "text/html" and html is None:
            html = part.get_content()
    return text, html, tuple(attachments)


def _header(value: str | None) -> str | None:
    return str(make_header(decode_header(value))) if value else None


def _addresses(values: list[str]) -> tuple[tuple[str, str], ...]:
    return tuple((_header(name) or "", address.casefold()) for name, address in getaddresses(values) if address)


def _date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def _response_int(client: imaplib.IMAP4, name: str) -> int | None:
    _, values = client.response(name)
    try:
        return int(values[0]) if values and values[0] else None
    except (TypeError, ValueError):
        return None


def _select_mutable(client: imaplib.IMAP4, folder: str) -> None:
    status, _ = client.select(folder, readonly=False)
    if status != "OK":
        raise MailProviderError("Mailbox folder could not be opened for update.")


def _safe_destination(name: str) -> None:
    normalized = name.strip()
    if not normalized or any(term in normalized.casefold().replace("-", " ").replace("_", " ").split() for term in _FORBIDDEN_FOLDER_TERMS):
        raise MailProviderError("Destructive mailbox destinations are not permitted.")


def _within_sync_limit(started_at: float) -> None:
    if monotonic() - started_at >= SYNC_LIMIT_SECONDS:
        raise TimeoutError("Mailbox synchronization reached its ten-minute limit.")
