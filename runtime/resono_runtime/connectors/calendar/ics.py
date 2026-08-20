from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from email.utils import parseaddr
from typing import Iterable

import httpx

from resono_runtime.security.outbound import assert_redirect_safe, validate_public_url


@dataclass(slots=True, frozen=True)
class IcsCalendarCredentials:
    feed_url: str


@dataclass(slots=True, frozen=True)
class IcsCalendarEvent:
    provider_event_id: str
    title: str
    starts_at: datetime
    ends_at: datetime | None
    all_day: bool
    recurrence_id: str = ""
    status: str = "confirmed"
    description: str | None = None
    location: str | None = None
    organizer: str | None = None
    calendar_label: str | None = None


class IcsCalendarProviderClient:
    def parse(self, body: str) -> list[IcsCalendarEvent]:
        if "BEGIN:VCALENDAR" not in body:
            raise ValueError("The provided file is not valid iCalendar content.")
        return list(self._parse_ics(body))

    def validate_feed(self, *, credentials: IcsCalendarCredentials) -> None:
        response = self._get_public_url(credentials.feed_url)
        response.raise_for_status()
        if "BEGIN:VCALENDAR" not in response.text:
            raise ValueError("The provided feed did not return valid iCalendar content.")

    def fetch_events(
        self,
        *,
        credentials: IcsCalendarCredentials,
        starts_at_from: datetime | None = None,
        starts_at_to: datetime | None = None,
        limit: int = 100,
    ) -> list[IcsCalendarEvent]:
        response = self._get_public_url(credentials.feed_url)
        response.raise_for_status()
        events = self.parse(response.text)
        if starts_at_from is not None:
            events = [event for event in events if event.starts_at >= starts_at_from]
        if starts_at_to is not None:
            events = [event for event in events if event.starts_at <= starts_at_to]
        events.sort(key=lambda item: item.starts_at)
        return events[:limit]

    def _get_public_url(self, url: str) -> httpx.Response:
        current_url = validate_public_url(url, target="feedUrl")
        for _ in range(5):
            response = httpx.get(current_url, timeout=20.0, follow_redirects=False)
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            location = response.headers.get("location")
            if not location:
                return response
            current_url = assert_redirect_safe(current_url, str(httpx.URL(current_url).join(location)), target="feedUrl")
        raise ValueError("The provided feed redirects too many times.")

    def _parse_ics(self, body: str) -> Iterable[IcsCalendarEvent]:
        unfolded_lines = self._unfold_lines(body.splitlines())
        in_event = False
        current: dict[str, str] = {}
        calendar_name: str | None = None
        for raw_line in unfolded_lines:
            line = raw_line.strip()
            if not line:
                continue
            if line == "BEGIN:VEVENT":
                in_event = True
                current = {}
                continue
            if line == "END:VEVENT":
                if current:
                    parsed = self._build_event(current=current, calendar_name=calendar_name)
                    if parsed is not None:
                        yield parsed
                in_event = False
                current = {}
                continue
            if not in_event and line.startswith("X-WR-CALNAME:"):
                calendar_name = self._decode_value(line.partition(":")[2])
                continue
            if not in_event:
                continue
            key, _, value = line.partition(":")
            if not _:
                continue
            current[key] = value

    @staticmethod
    def _unfold_lines(lines: list[str]) -> list[str]:
        unfolded: list[str] = []
        for line in lines:
            if unfolded and line.startswith((" ", "\t")):
                unfolded[-1] += line[1:]
            else:
                unfolded.append(line)
        return unfolded

    def _build_event(self, *, current: dict[str, str], calendar_name: str | None) -> IcsCalendarEvent | None:
        uid = current.get("UID")
        dtstart_key = self._first_matching_key(current, prefix="DTSTART")
        if not uid or dtstart_key is None:
            return None
        dtend_key = self._first_matching_key(current, prefix="DTEND")
        starts_at, all_day = self._parse_datetime(value=current[dtstart_key], key=dtstart_key)
        ends_at = None
        if dtend_key is not None:
            ends_at, _ = self._parse_datetime(value=current[dtend_key], key=dtend_key)
        organizer = self._normalize_organizer(current.get(self._first_matching_key(current, prefix="ORGANIZER")))
        return IcsCalendarEvent(
            provider_event_id=uid,
            title=self._decode_value(current.get("SUMMARY", "Untitled event")),
            starts_at=starts_at,
            ends_at=ends_at,
            all_day=all_day,
            recurrence_id=self._optional_decoded(current.get(self._first_matching_key(current, prefix="RECURRENCE-ID"))) or "",
            status=(current.get("STATUS", "CONFIRMED").strip().casefold() if current.get("STATUS", "CONFIRMED").strip().casefold() in {"tentative", "confirmed", "cancelled"} else "confirmed"),
            description=self._optional_decoded(current.get("DESCRIPTION")),
            location=self._optional_decoded(current.get("LOCATION")),
            organizer=organizer,
            calendar_label=calendar_name,
        )

    @staticmethod
    def _first_matching_key(values: dict[str, str], *, prefix: str) -> str | None:
        for key in values:
            if key.startswith(prefix):
                return key
        return None

    def _parse_datetime(self, *, value: str, key: str) -> tuple[datetime, bool]:
        decoded = self._decode_value(value)
        if "VALUE=DATE" in key:
            parsed_date = datetime.strptime(decoded, "%Y%m%d").date()
            return datetime.combine(parsed_date, datetime.min.time(), tzinfo=UTC), True
        if decoded.endswith("Z"):
            return datetime.strptime(decoded, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC), False
        parsed = datetime.strptime(decoded, "%Y%m%dT%H%M%S")
        return parsed.replace(tzinfo=UTC), False

    @staticmethod
    def _normalize_organizer(value: str | None) -> str | None:
        if not value:
            return None
        _, email_address = parseaddr(value.replace("MAILTO:", "mailto:"))
        return email_address or value

    @staticmethod
    def _decode_value(value: str) -> str:
        return (
            value.replace("\\n", "\n")
            .replace("\\,", ",")
            .replace("\\;", ";")
            .replace("\\\\", "\\")
            .strip()
        )

    def _optional_decoded(self, value: str | None) -> str | None:
        if not value:
            return None
        decoded = self._decode_value(value)
        return decoded or None
