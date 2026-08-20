from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
import uuid
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import httpx

from resono_runtime.security.outbound import assert_redirect_safe, validate_public_url
from resono_runtime.connectors.calendar.ics import IcsCalendarEvent, IcsCalendarProviderClient


ICLOUD_CALDAV_ROOT_URL = "https://caldav.icloud.com"
ICLOUD_CALDAV_PRINCIPAL_URL = "https://caldav.icloud.com/principal/"
_CALDAV_EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,254}$")


@dataclass(slots=True, frozen=True)
class CaldavCalendarCredentials:
    username: str
    password: str
    calendar_url: str | None = None


@dataclass(slots=True, frozen=True)
class CaldavDiscoveredCalendar:
    calendar_url: str
    display_name: str | None


@dataclass(slots=True, frozen=True)
class CaldavCalendarCreateRequest:
    title: str
    starts_at: datetime
    ends_at: datetime | None
    all_day: bool
    description: str | None = None
    location: str | None = None


class CaldavCalendarProviderClient:
    _NS_DAV = "DAV:"
    _NS_CALDAV = "urn:ietf:params:xml:ns:caldav"

    def __init__(self) -> None:
        self._ics = IcsCalendarProviderClient()

    def discover_calendars(self, *, credentials: CaldavCalendarCredentials) -> list[CaldavDiscoveredCalendar]:
        if credentials.calendar_url:
            return [CaldavDiscoveredCalendar(calendar_url=credentials.calendar_url, display_name=None)]

        principal_url = self._discover_principal_url(credentials=credentials)
        calendar_home_url = self._discover_calendar_home_url(credentials=credentials, principal_url=principal_url)
        calendars = self._discover_calendar_collection_urls(
            credentials=credentials,
            calendar_home_url=calendar_home_url,
        )
        if not calendars:
            raise ValueError("ReSono Labs could not discover any writable calendars for that Apple/CalDAV account.")
        return calendars

    def validate_calendar(self, *, credentials: CaldavCalendarCredentials) -> None:
        calendars = self.discover_calendars(credentials=credentials)
        for calendar in calendars:
            self._fetch_calendar_bodies(
                credentials=CaldavCalendarCredentials(
                    username=credentials.username,
                    password=credentials.password,
                    calendar_url=calendar.calendar_url,
                ),
                starts_at_from=None,
                starts_at_to=None,
            )
            return
        raise ValueError("The provided CalDAV account did not expose a readable calendar.")

    def discover_capabilities(self, *, credentials: CaldavCalendarCredentials) -> tuple[bool, bool, bool]:
        if not credentials.calendar_url:
            raise ValueError("The linked CalDAV calendar is missing its resolved calendar URL.")
        body = ('<?xml version="1.0" encoding="utf-8"?>'
                '<D:propfind xmlns:D="DAV:"><D:prop><D:current-user-privilege-set/>'
                '</D:prop></D:propfind>')
        response = self._send_request(
            credentials=credentials, method="PROPFIND", url=credentials.calendar_url,
            content=body, headers={"Content-Type": "application/xml; charset=utf-8", "Depth": "0"},
        )
        if response.status_code not in {200, 207}:
            return False, False, False
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            return False, False, False
        privileges = {node.tag for node in root.findall(".//{DAV:}privilege/*")}
        write = "{DAV:}write" in privileges
        return write or "{DAV:}bind" in privileges, write or "{DAV:}write-content" in privileges, write or "{DAV:}unbind" in privileges

    def fetch_events(
        self,
        *,
        credentials: CaldavCalendarCredentials,
        starts_at_from: datetime | None = None,
        starts_at_to: datetime | None = None,
        limit: int = 100,
    ) -> list[IcsCalendarEvent]:
        if not credentials.calendar_url:
            raise ValueError("The linked CalDAV calendar is missing its resolved calendar URL.")
        calendar_bodies = self._fetch_calendar_bodies(
            credentials=credentials,
            starts_at_from=starts_at_from,
            starts_at_to=starts_at_to,
        )
        events: list[IcsCalendarEvent] = []
        for body in calendar_bodies:
            events.extend(list(self._ics._parse_ics(body)))
        if starts_at_from is not None:
            events = [event for event in events if event.starts_at >= starts_at_from]
        if starts_at_to is not None:
            events = [event for event in events if event.starts_at <= starts_at_to]
        events.sort(key=lambda item: item.starts_at)
        return events[:limit]

    def create_event(
        self,
        *,
        credentials: CaldavCalendarCredentials,
        request: CaldavCalendarCreateRequest,
        calendar_label: str | None = None,
        provider_event_id: str | None = None,
    ) -> IcsCalendarEvent:
        if not credentials.calendar_url:
            raise ValueError("The linked CalDAV calendar is missing its resolved calendar URL.")
        uid = provider_event_id or f"{uuid.uuid4()}@resono.calendar"
        if not _CALDAV_EVENT_ID_PATTERN.fullmatch(uid):
            raise ValueError("The calendar event identity is invalid.")
        resource_url = self._resource_url(credentials.calendar_url, uid)
        response = self._send_request(
            credentials=credentials,
            method="PUT",
            url=resource_url,
            content=self._build_event_ics(uid=uid, request=request),
            headers={
                "Content-Type": "text/calendar; charset=utf-8",
                "If-None-Match": "*",
            },
        )
        response.raise_for_status()
        return IcsCalendarEvent(
            provider_event_id=uid,
            title=request.title,
            starts_at=request.starts_at,
            ends_at=request.ends_at,
            all_day=request.all_day,
            description=request.description,
            location=request.location,
            organizer=credentials.username,
            calendar_label=calendar_label,
        )

    def update_event(
        self,
        *,
        credentials: CaldavCalendarCredentials,
        provider_event_id: str,
        request: CaldavCalendarCreateRequest,
        calendar_label: str | None = None,
    ) -> IcsCalendarEvent:
        if not credentials.calendar_url:
            raise ValueError("The linked CalDAV calendar is missing its resolved calendar URL.")
        if not _CALDAV_EVENT_ID_PATTERN.fullmatch(provider_event_id):
            raise ValueError("The calendar event identity is invalid.")
        response = self._send_request(
            credentials=credentials,
            method="PUT",
            url=self._resource_url(credentials.calendar_url, provider_event_id),
            content=self._build_event_ics(uid=provider_event_id, request=request),
            headers={"Content-Type": "text/calendar; charset=utf-8"},
        )
        response.raise_for_status()
        return IcsCalendarEvent(
            provider_event_id=provider_event_id, title=request.title,
            starts_at=request.starts_at, ends_at=request.ends_at, all_day=request.all_day,
            description=request.description, location=request.location,
            organizer=credentials.username, calendar_label=calendar_label,
        )

    def delete_event(self, *, credentials: CaldavCalendarCredentials, provider_event_id: str) -> None:
        if not credentials.calendar_url:
            raise ValueError("The linked CalDAV calendar is missing its resolved calendar URL.")
        if not _CALDAV_EVENT_ID_PATTERN.fullmatch(provider_event_id):
            raise ValueError("The calendar event identity is invalid.")
        response = self._send_request(
            credentials=credentials,
            method="DELETE",
            url=self._resource_url(credentials.calendar_url, provider_event_id),
        )
        if response.status_code not in {200, 202, 204, 404}:
            response.raise_for_status()

    def _discover_principal_url(self, *, credentials: CaldavCalendarCredentials) -> str:
        candidates = [
            ICLOUD_CALDAV_PRINCIPAL_URL,
            f"{ICLOUD_CALDAV_ROOT_URL}/.well-known/caldav",
            f"{ICLOUD_CALDAV_ROOT_URL}/",
        ]
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<D:propfind xmlns:D="DAV:">'
            "<D:prop><D:current-user-principal/></D:prop>"
            "</D:propfind>"
        )
        for candidate in candidates:
            response = self._send_request(
                credentials=credentials,
                method="PROPFIND",
                url=candidate,
                content=body,
                headers={"Content-Type": "application/xml; charset=utf-8", "Depth": "0"},
            )
            if response.status_code not in {200, 207}:
                continue
            principal_href = self._extract_first_href(response.text, f"{{{self._NS_DAV}}}current-user-principal")
            if principal_href:
                return self._absolute_url(str(response.url), principal_href)
            if candidate == ICLOUD_CALDAV_PRINCIPAL_URL:
                return candidate
        raise ValueError("ReSono Labs could not discover the principal URL for that Apple/CalDAV account.")

    def _discover_calendar_home_url(self, *, credentials: CaldavCalendarCredentials, principal_url: str) -> str:
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'
            "<D:prop><C:calendar-home-set/></D:prop>"
            "</D:propfind>"
        )
        response = self._send_request(
            credentials=credentials,
            method="PROPFIND",
            url=principal_url,
            content=body,
            headers={"Content-Type": "application/xml; charset=utf-8", "Depth": "0"},
        )
        response.raise_for_status()
        home_href = self._extract_first_href(response.text, f"{{{self._NS_CALDAV}}}calendar-home-set")
        if not home_href:
            raise ValueError("ReSono Labs could not discover the calendar home for that Apple/CalDAV account.")
        return self._absolute_url(str(response.url), home_href)

    def _discover_calendar_collection_urls(
        self,
        *,
        credentials: CaldavCalendarCredentials,
        calendar_home_url: str,
    ) -> list[CaldavDiscoveredCalendar]:
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'
            "<D:prop><D:displayname/><D:resourcetype/></D:prop>"
            "</D:propfind>"
        )
        response = self._send_request(
            credentials=credentials,
            method="PROPFIND",
            url=calendar_home_url,
            content=body,
            headers={"Content-Type": "application/xml; charset=utf-8", "Depth": "1"},
        )
        response.raise_for_status()
        return self._extract_calendar_collections(payload=response.text, base_url=str(response.url))

    def _fetch_calendar_bodies(
        self,
        *,
        credentials: CaldavCalendarCredentials,
        starts_at_from: datetime | None,
        starts_at_to: datetime | None,
    ) -> list[str]:
        if not credentials.calendar_url:
            raise ValueError("The linked CalDAV calendar is missing its resolved calendar URL.")
        report_body = self._build_report_xml(starts_at_from=starts_at_from, starts_at_to=starts_at_to)
        report_response = self._send_request(
            credentials=credentials,
            method="REPORT",
            url=credentials.calendar_url,
            content=report_body,
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "Depth": "1",
            },
        )
        if report_response.status_code in {200, 207}:
            calendar_bodies = self._extract_calendar_data(report_response.text)
            if calendar_bodies:
                return calendar_bodies

        get_response = self._send_request(
            credentials=credentials,
            method="GET",
            url=credentials.calendar_url,
        )
        get_response.raise_for_status()
        if "BEGIN:VCALENDAR" in get_response.text:
            return [get_response.text]
        return []

    def _send_request(
        self,
        *,
        credentials: CaldavCalendarCredentials,
        method: str,
        url: str,
        content: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        safe_url = validate_public_url(url, target="calendarUrl")
        last_response: httpx.Response | None = None
        last_error: httpx.HTTPError | None = None
        for username_candidate in self._auth_username_candidates(credentials.username):
            try:
                response = httpx.request(
                    method,
                    safe_url,
                    content=content,
                    headers=headers,
                    auth=httpx.BasicAuth(username_candidate, credentials.password),
                    timeout=20.0,
                    follow_redirects=False,
                )
                if response.status_code in {301, 302, 303, 307, 308} and response.headers.get("location"):
                    redirect_url = str(httpx.URL(str(response.url)).join(response.headers["location"]))
                    response = httpx.request(
                        method,
                        assert_redirect_safe(
                            str(response.url),
                            redirect_url,
                            allow_host_change=False,
                            target="calendarUrl",
                        ),
                        content=content,
                        headers=headers,
                        auth=httpx.BasicAuth(username_candidate, credentials.password),
                        timeout=20.0,
                        follow_redirects=False,
                    )
            except httpx.HTTPError as exc:
                last_error = exc
                continue
            if response.status_code != 401:
                return response
            last_response = response
        if last_response is not None:
            return last_response
        if last_error is not None:
            raise last_error
        raise RuntimeError("No CalDAV authentication attempt was made.")

    def _extract_calendar_data(self, payload: str) -> list[str]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return []
        calendar_data_tag = f"{{{self._NS_CALDAV}}}calendar-data"
        output: list[str] = []
        for node in root.iter():
            if node.tag != calendar_data_tag:
                continue
            if isinstance(node.text, str) and "BEGIN:VCALENDAR" in node.text:
                output.append(node.text)
        return output

    def _extract_first_href(self, payload: str, property_tag: str) -> str | None:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return None
        for node in root.iter():
            if node.tag != property_tag:
                continue
            href_node = node.find(f".//{{{self._NS_DAV}}}href")
            if href_node is not None and isinstance(href_node.text, str) and href_node.text.strip():
                return href_node.text.strip()
        return None

    def _extract_calendar_collections(self, *, payload: str, base_url: str) -> list[CaldavDiscoveredCalendar]:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            return []
        calendars: list[CaldavDiscoveredCalendar] = []
        response_tag = f"{{{self._NS_DAV}}}response"
        href_tag = f"{{{self._NS_DAV}}}href"
        displayname_tag = f"{{{self._NS_DAV}}}displayname"
        resourcetype_tag = f"{{{self._NS_DAV}}}resourcetype"
        calendar_tag = f"{{{self._NS_CALDAV}}}calendar"
        for response in root.findall(f".//{response_tag}"):
            href_node = response.find(href_tag)
            if href_node is None or not isinstance(href_node.text, str) or not href_node.text.strip():
                continue
            resource_type = response.find(f".//{resourcetype_tag}")
            if resource_type is None or resource_type.find(calendar_tag) is None:
                continue
            display_name_node = response.find(f".//{displayname_tag}")
            display_name = display_name_node.text.strip() if display_name_node is not None and isinstance(display_name_node.text, str) and display_name_node.text.strip() else None
            calendars.append(
                CaldavDiscoveredCalendar(
                    calendar_url=self._absolute_url(base_url, href_node.text.strip()),
                    display_name=display_name,
                )
            )
        return calendars

    def _build_report_xml(
        self,
        *,
        starts_at_from: datetime | None,
        starts_at_to: datetime | None,
    ) -> str:
        time_range = ""
        if starts_at_from is not None or starts_at_to is not None:
            start_value = self._format_utc(starts_at_from or datetime(2000, 1, 1, tzinfo=UTC))
            end_value = self._format_utc(starts_at_to or datetime(2100, 1, 1, tzinfo=UTC))
            time_range = f'<C:time-range start="{start_value}" end="{end_value}"/>'
        return (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'
            "<D:prop><D:getetag/><C:calendar-data/></D:prop>"
            "<C:filter><C:comp-filter name=\"VCALENDAR\"><C:comp-filter name=\"VEVENT\">"
            f"{time_range}"
            "</C:comp-filter></C:comp-filter></C:filter>"
            "</C:calendar-query>"
        )

    def _build_event_ics(self, *, uid: str, request: CaldavCalendarCreateRequest) -> str:
        created_at = self._format_utc(datetime.now(UTC))
        dtstart = self._format_event_datetime(request.starts_at, all_day=request.all_day)
        dtend = None
        if request.ends_at is not None:
            dtend = self._format_event_datetime(request.ends_at, all_day=request.all_day)
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//ReSono Labs//Calendar Runtime//EN",
            "CALSCALE:GREGORIAN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{created_at}",
            f"DTSTART{';VALUE=DATE' if request.all_day else ''}:{dtstart}",
        ]
        if dtend is not None:
            lines.append(f"DTEND{';VALUE=DATE' if request.all_day else ''}:{dtend}")
        lines.append(f"SUMMARY:{self._escape_ics_text(request.title)}")
        if request.description:
            lines.append(f"DESCRIPTION:{self._escape_ics_text(request.description)}")
        if request.location:
            lines.append(f"LOCATION:{self._escape_ics_text(request.location)}")
        lines.extend(["END:VEVENT", "END:VCALENDAR", ""])
        return "\r\n".join(lines)

    @staticmethod
    def _resource_url(calendar_url: str, uid: str) -> str:
        return f"{calendar_url.rstrip('/')}/{uid}.ics"

    @staticmethod
    def _auth_username_candidates(username: str) -> list[str]:
        normalized = username.strip()
        candidates = [normalized]
        if "@" in normalized:
            local_part, _, domain = normalized.partition("@")
            if local_part and domain.lower() in {"icloud.com", "me.com", "mac.com"}:
                candidates.append(local_part)
        deduped: list[str] = []
        for candidate in candidates:
            if candidate and candidate not in deduped:
                deduped.append(candidate)
        return deduped

    @staticmethod
    def _absolute_url(base_url: str, href: str) -> str:
        return urljoin(base_url, href)

    @staticmethod
    def _format_utc(value: datetime) -> str:
        return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")

    @staticmethod
    def _format_event_datetime(value: datetime, *, all_day: bool) -> str:
        if all_day:
            return value.astimezone(UTC).strftime("%Y%m%d")
        return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")

    @staticmethod
    def _escape_ics_text(value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace(",", "\\,")
            .replace(";", "\\;")
        )
