from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CalendarAccountConfiguration:
    account_id: str
    provider_type: str
    label: str
    endpoint: str | None
    calendar_path: str | None


@dataclass(frozen=True, slots=True)
class CalendarCapabilities:
    can_create: bool
    can_update: bool
    can_delete: bool


@dataclass(frozen=True, slots=True)
class CalendarAccount:
    configuration: CalendarAccountConfiguration
    capabilities: CalendarCapabilities
    enabled: bool
    credential_present: bool
    next_sync_at: str | None
    last_sync_at: str | None
    last_sync_state: str
    last_sync_detail: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    event_id: str
    account_id: str
    provider_event_id: str
    recurrence_id: str
    title: str
    starts_at: str
    ends_at: str | None
    timezone: str
    all_day: bool
    location: str | None
    calendar_name: str | None
    organizer: str | None
    description: str | None
    status: str
    editable: bool
    source_etag: str | None
    synchronized_at: str
