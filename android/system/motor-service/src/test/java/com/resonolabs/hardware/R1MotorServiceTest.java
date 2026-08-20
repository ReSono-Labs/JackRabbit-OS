package com.resonolabs.hardware;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class R1MotorServiceTest {
    @Test public void namedPositionsMatchPhysicallyObservedProductStates() {
        assertEquals(180, R1MotorService.rawPositionFor(R1MotorService.POSITION_OUTWARD));
        assertEquals(0, R1MotorService.rawPositionFor(R1MotorService.POSITION_INWARD));
        assertEquals(180, R1MotorService.rawPositionFor(R1MotorService.POSITION_HOME));
        assertEquals(-1, R1MotorService.rawPositionFor(99));
    }

    @Test public void exposedDirectionChangesRequireClosedWaypoint() {
        assertTrue(R1MotorService.requiresPrivacyWaypoint("180", 0));
        assertTrue(R1MotorService.requiresPrivacyWaypoint("0", 180));
        assertFalse(R1MotorService.requiresPrivacyWaypoint("90", 0));
        assertFalse(R1MotorService.requiresPrivacyWaypoint("90", 180));
    }

    @Test public void reportedPositionRequiresExactConfirmedValue() {
        assertTrue(R1MotorService.reportedPositionMatches("180\n", 180));
        assertFalse(R1MotorService.reportedPositionMatches("90", 180));
        assertFalse(R1MotorService.reportedPositionMatches(null, 180));
    }
}
