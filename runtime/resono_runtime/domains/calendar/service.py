from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
import json
from uuid import NAMESPACE_URL, uuid4, uuid5

from resono_runtime.connectors.calendar import (
    CaldavCalendarCredentials,
    CaldavCalendarProviderClient,
    IcsCalendarCredentials,
    IcsCalendarEvent,
    IcsCalendarProviderClient,
)
from resono_runtime.connectors.calendar.caldav import CaldavCalendarCreateRequest
from resono_runtime.domains.calendar.models import CalendarAccount, CalendarAccountConfiguration, CalendarCapabilities, CalendarEvent
from resono_runtime.domains.calendar.repository import CalendarRepository
from resono_runtime.security.credentials import ConnectionCredentialEnvelopes
from resono_runtime.storage.connection_credentials import ConnectionCredentialRepository
from resono_runtime.tools import ToolInvocationContext, ToolInvocationResult


class CalendarService:
    def __init__(self, repository: CalendarRepository, credentials: ConnectionCredentialRepository, envelopes: ConnectionCredentialEnvelopes, ics: IcsCalendarProviderClient, caldav: CaldavCalendarProviderClient) -> None:
        self._repository = repository
        self._credentials = credentials
        self._envelopes = envelopes
        self._ics = ics
        self._caldav = caldav

    def connect_ics_subscription(self, *, label: str, feed_url: str) -> CalendarAccount:
        self._ics.validate_feed(credentials=IcsCalendarCredentials(feed_url))
        account = self._repository.create_account(CalendarAccountConfiguration(str(uuid4()), "ics_subscription", label.strip(), feed_url, None), None)
        self._repository.set_capabilities(account.configuration.account_id, CalendarCapabilities(False, False, False))
        self.sync(account.configuration.account_id)
        return self._required_account(account.configuration.account_id)

    def connect_ics_file(self, *, label: str, body: str) -> CalendarAccount:
        events = self._ics.parse(body)
        account_id = str(uuid4())
        envelope = self._envelopes.seal(account_id, json.dumps({"ics": body}, separators=(",", ":")))
        account = self._repository.create_account(CalendarAccountConfiguration(account_id, "ics_file", label.strip(), None, None), envelope)
        self._repository.set_capabilities(account_id, CalendarCapabilities(False, False, False))
        self._store(account, events)
        self._repository.finish_sync(account_id, ready=True, detail=None)
        return self._required_account(account_id)

    def connect_caldav(self, *, label: str, username: str, password: str, calendar_url: str) -> CalendarAccount:
        credentials = CaldavCalendarCredentials(username.strip(), password, calendar_url.strip())
        self._caldav.validate_calendar(credentials=credentials)
        capabilities = CalendarCapabilities(*self._caldav.discover_capabilities(credentials=credentials))
        account_id = str(uuid4())
        envelope = self._envelopes.seal(account_id, json.dumps(asdict(credentials), separators=(",", ":")))
        account = self._repository.create_account(CalendarAccountConfiguration(account_id, "caldav", label.strip(), calendar_url.strip(), calendar_url.strip()), envelope)
        self._repository.set_capabilities(account_id, capabilities)
        self.sync(account_id)
        return self._required_account(account_id)

    def sync(self, account_id: str) -> None:
        account = self._required_account(account_id)
        self._repository.begin_sync(account_id)
        try:
            now = datetime.now(UTC)
            if account.configuration.provider_type == "ics_subscription":
                events = self._ics.fetch_events(credentials=IcsCalendarCredentials(account.configuration.endpoint or ""), starts_at_from=now - timedelta(days=1), starts_at_to=now + timedelta(days=730), limit=1000)
            elif account.configuration.provider_type == "ics_file":
                events = self._ics.parse(str(self._credential_value(account_id)["ics"]))
            else:
                credentials = self._caldav_credentials(account)
                capabilities = CalendarCapabilities(*self._caldav.discover_capabilities(credentials=credentials))
                self._repository.set_capabilities(account_id, capabilities)
                events = self._caldav.fetch_events(credentials=credentials, starts_at_from=now - timedelta(days=1), starts_at_to=now + timedelta(days=730), limit=1000)
            self._store(self._required_account(account_id), events)
        except Exception:
            self._repository.finish_sync(account_id, ready=False, detail="Calendar synchronization failed.")
            raise
        self._repository.finish_sync(account_id, ready=True, detail=None)

    def invoke_tool(self, name: str, context: ToolInvocationContext, arguments: dict[str, object]) -> ToolInvocationResult:
        try:
            if name == "calendar_list_upcoming":
                value = [self._event_view(item) for item in self._repository.upcoming_events(datetime.now(UTC).isoformat(), limit=_limit(arguments))]
            elif name == "calendar_search":
                value = [self._event_view(item) for item in self._repository.search_upcoming(datetime.now(UTC).isoformat(), _required(arguments, "query"), limit=_limit(arguments))]
            elif name == "calendar_read_event":
                event = self._repository.get_event(_required(arguments, "eventId"))
                if event is None: raise ValueError("Calendar event was not found.")
                value = self._event_view(event)
            elif name == "calendar_confirm_action":
                value = self._confirm(context, arguments)
            elif name in {"calendar_create_event", "calendar_update_event", "calendar_delete_event"}:
                value = self._mutation(name, context, arguments)
            else:
                raise ValueError("Calendar tool is unavailable.")
            return ToolInvocationResult(json.dumps(value, separators=(",", ":")), {"result": value})
        except (ValueError, PermissionError, RuntimeError) as error:
            return ToolInvocationResult(str(error), is_error=True)

    def _mutation(self, name: str, context: ToolInvocationContext, arguments: dict[str, object]) -> dict[str, object]:
        operation = name.removeprefix("calendar_").removesuffix("_event")
        account_id = _required(arguments, "calendarAccountId")
        event_id = _optional(arguments, "eventId")
        payload = {key: value for key, value in arguments.items() if key not in {"calendarAccountId", "eventId", "actionId", "contentHash"}}
        if operation == "update":
            event = self._repository.get_event(event_id or "")
            if event is None or event.account_id != account_id: raise ValueError("Calendar event was not found.")
            original = {"title": event.title, "startsAt": event.starts_at, "endsAt": event.ends_at, "timezone": event.timezone, "allDay": event.all_day, "location": event.location, "description": event.description}
            payload = {key: value for key, value in {**original, **payload}.items() if value is not None}
        value = self._repository.create_pending_action(account_id=account_id, event_id=event_id, operation=operation, payload=payload, voice_session_id=context.voice_session_id or "", tool_call_id=context.tool_call_id or "", utterance_id=context.user_utterance_id or 0)
        value["confirmationRequired"] = True
        return value

    def _confirm(self, context: ToolInvocationContext, arguments: dict[str, object]) -> dict[str, object]:
        action_id = _required(arguments, "actionId")
        claim = self._repository.claim_pending_action(action_id=action_id, content_hash=_required(arguments, "contentHash"), voice_session_id=context.voice_session_id or "", approval_utterance_id=context.user_utterance_id or 0)
        try:
            self._execute(claim)
        except Exception:
            self._repository.finish_pending_action(action_id, completed=False)
            raise
        self._repository.finish_pending_action(action_id, completed=True)
        self.sync(str(claim["accountId"]))
        return {"state": "completed", "actionId": action_id}

    def _execute(self, claim: dict[str, object]) -> None:
        account = self._required_account(str(claim["accountId"]))
        credentials = self._caldav_credentials(account)
        payload = claim["payload"]
        if not isinstance(payload, dict): raise ValueError("Calendar action payload is invalid.")
        operation = str(claim["operation"])
        if operation == "delete":
            event = self._repository.get_event(str(claim["eventId"]))
            if event is None: raise ValueError("Calendar event was not found.")
            self._caldav.delete_event(credentials=credentials, provider_event_id=event.provider_event_id)
            return
        request = CaldavCalendarCreateRequest(title=_required(payload, "title"), starts_at=_date_time(payload, "startsAt"), ends_at=_optional_date_time(payload, "endsAt"), all_day=bool(payload.get("allDay", False)), description=_optional(payload, "description"), location=_optional(payload, "location"))
        if operation == "create":
            self._caldav.create_event(credentials=credentials, request=request, calendar_label=account.configuration.label)
        else:
            event = self._repository.get_event(str(claim["eventId"]))
            if event is None: raise ValueError("Calendar event was not found.")
            self._caldav.update_event(credentials=credentials, provider_event_id=event.provider_event_id, request=request, calendar_label=account.configuration.label)

    def _store(self, account: CalendarAccount, values: list[IcsCalendarEvent]) -> None:
        now = datetime.now(UTC).isoformat()
        editable = account.configuration.provider_type == "caldav" and (account.capabilities.can_update or account.capabilities.can_delete)
        events = tuple(CalendarEvent(str(uuid5(NAMESPACE_URL, f"calendar:{account.configuration.account_id}:{item.provider_event_id}:{item.recurrence_id}")), account.configuration.account_id, item.provider_event_id, item.recurrence_id, item.title, item.starts_at.astimezone(UTC).isoformat(), item.ends_at.astimezone(UTC).isoformat() if item.ends_at else None, "UTC", item.all_day, item.location, item.calendar_label or account.configuration.label, item.organizer, item.description, item.status, editable, None, now) for item in values)
        self._repository.replace_account_events(account.configuration.account_id, events)

    def _credential_value(self, account_id: str) -> dict[str, object]:
        envelope = self._credentials.get_envelope(account_id)
        if envelope is None: raise ValueError("Calendar credentials are unavailable.")
        value = json.loads(self._envelopes.open(account_id, envelope))
        if not isinstance(value, dict): raise ValueError("Calendar credentials are invalid.")
        return value

    def _caldav_credentials(self, account: CalendarAccount) -> CaldavCalendarCredentials:
        if account.configuration.provider_type != "caldav": raise PermissionError("This calendar is read-only.")
        value = self._credential_value(account.configuration.account_id)
        return CaldavCalendarCredentials(str(value["username"]), str(value["password"]), str(value["calendar_url"]))

    def _required_account(self, account_id: str) -> CalendarAccount:
        account = self._repository.get_account(account_id)
        if account is None: raise ValueError("Calendar connection was not found.")
        return account

    @staticmethod
    def _event_view(event: CalendarEvent) -> dict[str, object]:
        return {"eventId": event.event_id, "calendarAccountId": event.account_id, "title": event.title, "startsAt": event.starts_at, "endsAt": event.ends_at, "timezone": event.timezone, "allDay": event.all_day, "location": event.location, "calendar": event.calendar_name, "organizer": event.organizer, "description": event.description, "editable": event.editable}


def _required(value: dict[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip(): raise ValueError(f"{key} is required.")
    return item.strip()


def _optional(value: dict[str, object], key: str) -> str | None:
    item = value.get(key)
    return item.strip() if isinstance(item, str) and item.strip() else None


def _date_time(value: dict[str, object], key: str) -> datetime:
    parsed = datetime.fromisoformat(_required(value, key).replace("Z", "+00:00"))
    if parsed.tzinfo is None: raise ValueError(f"{key} must include a timezone.")
    return parsed


def _optional_date_time(value: dict[str, object], key: str) -> datetime | None:
    return _date_time(value, key) if _optional(value, key) else None


def _limit(arguments: dict[str, object]) -> int:
    value = arguments.get("limit", 25)
    return max(1, min(value, 50)) if isinstance(value, int) and not isinstance(value, bool) else 25
