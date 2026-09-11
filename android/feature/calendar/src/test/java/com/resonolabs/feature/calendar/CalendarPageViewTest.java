package com.resonolabs.feature.calendar;

import java.util.Locale;
import java.util.TimeZone;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import static org.junit.Assert.assertEquals;

public final class CalendarPageViewTest {
    private Locale originalLocale;
    private TimeZone originalTimezone;

    @Before public void setLocale() {
        originalLocale = Locale.getDefault();
        originalTimezone = TimeZone.getDefault();
        Locale.setDefault(Locale.US);
    }

    @After public void restoreLocale() {
        Locale.setDefault(originalLocale);
        TimeZone.setDefault(originalTimezone);
    }

    @Test public void timedEventsUseTheDeviceTimezoneIncludingDaylightSaving() {
        TimeZone.setDefault(TimeZone.getTimeZone("Europe/London"));
        assertEquals("Fri, Sep 11 · 9:00 AM", CalendarPageView.friendly("2026-09-11T08:00:00+00:00", false));
        assertEquals("Fri, Dec 11 · 9:00 AM", CalendarPageView.friendly("2026-12-11T09:00:00+00:00", false));
        assertEquals("Sat, Sep 12 · 12:30 AM", CalendarPageView.friendly("2026-09-11T23:30:00+00:00", false));
        TimeZone.setDefault(TimeZone.getTimeZone("America/New_York"));
        assertEquals("Fri, Sep 11 · 4:00 AM", CalendarPageView.friendly("2026-09-11T08:00:00+00:00", false));
    }

    @Test public void utcDisplayRemainsUnchanged() {
        TimeZone.setDefault(TimeZone.getTimeZone("UTC"));
        assertEquals("Fri, Sep 11 · 8:00 AM", CalendarPageView.friendly("2026-09-11T08:00:00+00:00", false));
    }

    @Test public void allDayDatesDoNotShiftToThePreviousDay() {
        TimeZone.setDefault(TimeZone.getTimeZone("America/New_York"));
        assertEquals("Fri, Sep 11 · 12:00 AM", CalendarPageView.friendly("2026-09-11T00:00:00+00:00", true));
    }

    @Test public void emptyAndUnparseableValuesRemainUnchanged() {
        assertEquals("", CalendarPageView.friendly(null, false));
        assertEquals("", CalendarPageView.friendly("", false));
        assertEquals("unavailable", CalendarPageView.friendly("unavailable", false));
    }
}
