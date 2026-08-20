from __future__ import annotations

from dataclasses import dataclass


CALENDAR_PACKAGE_VERSION = 1


@dataclass(frozen=True, slots=True)
class CalendarToolContract:
    name: str
    description: str
    effect_class: str
    input_schema: dict[str, object]


def contracts() -> tuple[CalendarToolContract, ...]:
    account = {"calendarAccountId": {"type": "string"}}
    event = {**account, "eventId": {"type": "string"}}
    return (
        CalendarToolContract(
            "calendar_list_upcoming",
            "List upcoming events from the local synchronized Calendar service.",
            "read",
            _schema({"limit": {"type": "integer", "minimum": 1, "maximum": 50}}),
        ),
        CalendarToolContract(
            "calendar_search",
            "Search upcoming events in the local synchronized Calendar service.",
            "read",
            _schema({"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 50}}, ("query",)),
        ),
        CalendarToolContract(
            "calendar_read_event",
            "Read one synchronized Calendar event by its stable event ID.",
            "read",
            _schema({"eventId": {"type": "string"}}, ("eventId",)),
        ),
        CalendarToolContract(
            "calendar_create_event",
            "Prepare an event for a selected calendar. The calendar may be read-only. Review the exact event with the user before confirmation.",
            "external_write",
            _schema({**account, **_event_fields()}, ("calendarAccountId", "title", "startsAt")),
        ),
        CalendarToolContract(
            "calendar_update_event",
            "Prepare changes to an existing event. The calendar or event may be read-only. Review the exact changes with the user before confirmation.",
            "external_write",
            _schema({**event, **_event_fields()}, ("calendarAccountId", "eventId")),
        ),
        CalendarToolContract(
            "calendar_delete_event",
            "Prepare deletion of an existing event. The calendar or event may be read-only. Deletion requires explicit user confirmation.",
            "external_write",
            _schema(event, ("calendarAccountId", "eventId")),
        ),
        CalendarToolContract(
            "calendar_confirm_action",
            "Execute one unchanged reviewed Calendar action only after the user explicitly approves it within ten minutes.",
            "external_write",
            _schema({"actionId": {"type": "string"}, "contentHash": {"type": "string"}}, ("actionId", "contentHash")),
        ),
    )


def _event_fields() -> dict[str, object]:
    return {
        "title": {"type": "string"}, "startsAt": {"type": "string"},
        "endsAt": {"type": "string"}, "timezone": {"type": "string"},
        "allDay": {"type": "boolean"}, "location": {"type": "string"},
        "description": {"type": "string"},
    }


def _schema(
    properties: dict[str, object],
    required: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "type": "object", "properties": properties,
        "required": list(required), "additionalProperties": False,
    }
