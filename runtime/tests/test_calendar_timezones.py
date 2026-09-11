from datetime import UTC
import unittest

from resono_runtime.connectors.calendar.ics import IcsCalendarProviderClient


def parse_event(start, end=None):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "BEGIN:VEVENT", "UID:timezone-test", start]
    if end:
        lines.append(end)
    lines.extend(["END:VEVENT", "END:VCALENDAR"])
    return IcsCalendarProviderClient().parse("\r\n".join(lines))[0]


class CalendarTimezoneTest(unittest.TestCase):
    def test_named_timezones_apply_to_start_and_end(self):
        for zone, date, expected_start, expected_end in (
            ("Europe/London", "20260911", "2026-09-11T08:00:00+00:00", "2026-09-11T09:00:00+00:00"),
            ("Europe/London", "20261211", "2026-12-11T09:00:00+00:00", "2026-12-11T10:00:00+00:00"),
            ('"America/New_York"', "20260911", "2026-09-11T13:00:00+00:00", "2026-09-11T14:00:00+00:00"),
        ):
            with self.subTest(zone=zone, date=date):
                event = parse_event(f"DTSTART;TZID={zone}:{date}T090000",
                                    f"DTEND;TZID={zone}:{date}T100000")
                self.assertEqual(event.starts_at.astimezone(UTC).isoformat(), expected_start)
                self.assertEqual(event.ends_at.astimezone(UTC).isoformat(), expected_end)

    def test_explicit_date_time_is_not_an_all_day_date(self):
        event = parse_event("DTSTART;VALUE=DATE-TIME;TZID=Europe/London:20260911T090000")
        self.assertEqual(event.starts_at.astimezone(UTC).isoformat(), "2026-09-11T08:00:00+00:00")
        self.assertFalse(event.all_day)

    def test_utc_all_day_and_existing_floating_time_behavior_are_preserved(self):
        for start, expected, all_day in (
            ("DTSTART:20260911T080000Z", "2026-09-11T08:00:00+00:00", False),
            ("DTSTART;VALUE=DATE:20260911", "2026-09-11T00:00:00+00:00", True),
            ("DTSTART:20260911T090000", "2026-09-11T09:00:00+00:00", False),
        ):
            with self.subTest(start=start):
                event = parse_event(start)
                self.assertEqual(event.starts_at.isoformat(), expected)
                self.assertEqual(event.all_day, all_day)

    def test_unknown_timezone_is_not_silently_treated_as_utc(self):
        with self.assertRaisesRegex(ValueError, "Unsupported calendar time zone"):
            parse_event("DTSTART;TZID=Unknown/Zone:20260911T090000")
