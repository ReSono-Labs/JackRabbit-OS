from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MailAccountConfiguration:
    account_id: str
    label: str
    email_address: str
    username: str
    imap_host: str
    imap_port: int
    imap_security: str
    smtp_host: str
    smtp_port: int
    smtp_security: str


@dataclass(frozen=True, slots=True)
class MailAccount:
    configuration: MailAccountConfiguration
    enabled: bool
    credential_present: bool
    next_sync_at: str | None
    last_sync_at: str | None
    last_sync_state: str
    last_sync_detail: str | None
    created_at: str
    updated_at: str
