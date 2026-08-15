package com.resonolabs.ui.power;

import org.junit.Test;
import static org.junit.Assert.assertEquals;

public final class DisplayPolicyTest {
    @Test public void homeUsesTwoMinuteIdleTimeout() {
        assertEquals(-1L, DisplayPolicy.IDLE_TIMEOUT_MS);
    }
}
