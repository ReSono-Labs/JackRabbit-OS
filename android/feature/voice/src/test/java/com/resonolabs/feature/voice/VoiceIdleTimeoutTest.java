package com.resonolabs.feature.voice;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class VoiceIdleTimeoutTest {
    @Test public void connectionStartsTenMinutesAndIdlePollingCannotPostponeIt() {
        VoiceIdleTimeout timeout = new VoiceIdleTimeout();
        timeout.connected(1_000L);
        timeout.update(300_000L, false);
        timeout.update(600_999L, false);
        assertFalse(timeout.expired(600_999L));
        assertTrue(timeout.expired(601_000L));
        timeout.update(700_000L, false);
        assertTrue(timeout.expired(700_000L));
    }

    @Test public void busyRoundSuspendsTimeoutUntilItBecomesIdle() {
        VoiceIdleTimeout timeout = new VoiceIdleTimeout();
        timeout.connected(1_000L);
        timeout.update(2_000L, true);
        timeout.update(700_000L, true);
        assertFalse(timeout.expired(700_000L));
        timeout.update(700_001L, false);
        assertFalse(timeout.expired(1_300_000L));
        assertTrue(timeout.expired(1_300_001L));
    }

    @Test public void newBusyRoundReplacesPreviousIdleDeadline() {
        VoiceIdleTimeout timeout = new VoiceIdleTimeout();
        timeout.connected(0L);
        timeout.update(100L, true);
        timeout.update(200L, false);
        timeout.update(600_199L, true);
        assertFalse(timeout.expired(900_000L));
        timeout.update(900_001L, false);
        timeout.update(1_000_000L, false);
        assertFalse(timeout.expired(1_500_000L));
        assertTrue(timeout.expired(1_500_001L));
    }

    @Test public void resetDisarmsTimeoutUntilTheNextConnection() {
        VoiceIdleTimeout timeout = new VoiceIdleTimeout();
        assertFalse(timeout.expired(600_000L));
        timeout.connected(600_001L);
        assertTrue(timeout.expired(1_200_001L));
        timeout.reset();
        timeout.update(1_200_002L, true);
        timeout.update(1_200_003L, false);
        assertFalse(timeout.expired(1_800_003L));
        timeout.connected(1_800_004L);
        assertFalse(timeout.expired(2_400_003L));
        assertTrue(timeout.expired(2_400_004L));
    }

    @Test public void newConnectionClearsPreviousBusyState() {
        VoiceIdleTimeout timeout = new VoiceIdleTimeout();
        timeout.connected(0L);
        timeout.update(1L, true);
        timeout.connected(1_000L);
        assertFalse(timeout.expired(600_999L));
        assertTrue(timeout.expired(601_000L));
    }
}
