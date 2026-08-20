from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from resono_runtime.domains.calendar.repository import CalendarAccountLimitError, CalendarRepository
from resono_runtime.domains.calendar.service import CalendarService
from resono_runtime.security.pairing import PairingAuthority

if TYPE_CHECKING:
    from .routes import RouteRequest


class CalendarRoutes:
    """Separates content-free management responses from device event content."""

    def __init__(self, repository: CalendarRepository, service: CalendarService) -> None:
        self._repository = repository
        self._service = service

    def handle_get(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if path == "/v1/management/calendar/accounts":
            if not _session(request, pairing, mutation=False): return True
            request.respond_json(200, {"accounts": [_account(item) for item in self._repository.list_accounts()]})
            return True
        if path == "/v1/calendar/upcoming":
            events = self._repository.upcoming_events(datetime.now(UTC).isoformat(), limit=50)
            request.respond_json(200, {"events": [_event(item) for item in events]})
            return True
        if path.startswith("/v1/calendar/events/"):
            item = self._repository.get_event(path.rsplit("/", 1)[-1])
            if item is None: _error(request, 404, "calendar_event_not_found", "Calendar event not found.")
            else: request.respond_json(200, _event(item))
            return True
        return False

    def handle_post(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        base = "/v1/management/calendar/accounts"
        if path != base and not (path.startswith(base + "/") and path.endswith("/sync")):
            return False
        if not _session(request, pairing, mutation=True): return True
        payload = request.request_json(max_bytes=2_000_000)
        if payload is None: return True
        try:
            if path.endswith("/sync"):
                account_id = path.split("/")[-2]
                self._service.sync(account_id)
                item = self._repository.get_account(account_id)
                request.respond_json(200, _account(item) if item is not None else {})
                return True
            kind = _required(payload, "type")
            label = _required(payload, "label")
            if kind == "ics_subscription":
                item = self._service.connect_ics_subscription(label=label, feed_url=_required(payload, "feedUrl"))
            elif kind == "ics_file":
                item = self._service.connect_ics_file(label=label, body=_required(payload, "ics"))
            elif kind == "caldav":
                item = self._service.connect_caldav(label=label, username=_required(payload, "username"), password=_required(payload, "password"), calendar_url=_required(payload, "calendarUrl"))
            else:
                raise ValueError("Calendar connection type is invalid.")
            request.respond_json(201, _account(item))
        except CalendarAccountLimitError as error:
            _error(request, 409, "calendar_account_limit", str(error))
        except (TypeError, ValueError) as error:
            _error(request, 400, "invalid_calendar_account", str(error))
        except Exception:
            _error(request, 502, "calendar_provider_unavailable", "Calendar validation or synchronization failed.")
        return True

    def handle_delete(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if not path.startswith("/v1/management/calendar/accounts/"): return False
        if not _session(request, pairing, mutation=True): return True
        account_id = path.rsplit("/", 1)[-1]
        if not self._repository.remove_account_local(account_id):
            _error(request, 404, "calendar_account_not_found", "Calendar connection not found.")
        else:
            request.respond_json(200, {"calendarAccountId": account_id, "removed": True})
        return True


def _account(item: object) -> dict[str, object]:
    value = item.configuration
    return {"calendarAccountId": value.account_id, "label": value.label, "type": value.provider_type, "endpoint": value.endpoint, "enabled": item.enabled, "credentialPresent": item.credential_present, "syncState": item.last_sync_state, "syncDetail": item.last_sync_detail, "lastSyncAt": item.last_sync_at, "nextSyncAt": item.next_sync_at, "capabilities": {"create": item.capabilities.can_create, "update": item.capabilities.can_update, "delete": item.capabilities.can_delete}}


def _event(item: object) -> dict[str, object]:
    return {"eventId": item.event_id, "calendarAccountId": item.account_id, "title": item.title, "startsAt": item.starts_at, "endsAt": item.ends_at, "timezone": item.timezone, "allDay": item.all_day, "location": item.location, "calendar": item.calendar_name, "organizer": item.organizer, "description": item.description, "editable": item.editable}


def _required(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip(): raise ValueError(f"{key} is required.")
    return value.strip()


def _session(request: "RouteRequest", pairing: PairingAuthority | None, *, mutation: bool) -> bool:
    if pairing is None:
        _error(request, 503, "management_unavailable", "Management pairing is unavailable."); return False
    return request.browser_session(pairing, mutation=mutation) is not None


def _error(request: "RouteRequest", status: int, code: str, message: str) -> None:
    request.respond_json(status, {"error": {"code": code, "message": message}})
