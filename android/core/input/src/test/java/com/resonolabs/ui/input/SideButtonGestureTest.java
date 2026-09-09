package com.resonolabs.ui.input;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class SideButtonGestureTest {
    @Test public void releaseBeforeThresholdIsOneTap() {
        SideButtonGesture gesture = new SideButtonGesture();
        assertEquals(SideButtonGesture.Event.DOWN, gesture.down(1_000L));
        assertTrue(gesture.isDown());
        assertEquals(SideButtonGesture.Event.NONE, gesture.advance(1_199L));
        assertEquals(SideButtonGesture.Event.TAP, gesture.up(1_199L, false));
        assertFalse(gesture.isDown());
        assertEquals(SideButtonGesture.Event.NONE, gesture.up(1_200L, false));
        assertEquals(SideButtonGesture.Event.NONE, gesture.advance(1_400L));
    }

    @Test public void releaseAtThresholdDoesNotRequireTimerDelivery() {
        SideButtonGesture gesture = new SideButtonGesture();
        gesture.down(1_000L);
        assertEquals(SideButtonGesture.Event.RELEASE, gesture.up(1_200L, false));
        assertFalse(gesture.isDown());
        assertEquals(SideButtonGesture.Event.NONE, gesture.up(1_201L, false));
    }

    @Test public void holdIsEmittedOnceAtThreshold() {
        SideButtonGesture gesture = new SideButtonGesture();
        gesture.down(1_000L);
        assertEquals(SideButtonGesture.Event.NONE, gesture.advance(1_199L));
        assertEquals(SideButtonGesture.Event.HOLD, gesture.advance(1_200L));
        assertEquals(SideButtonGesture.Event.NONE, gesture.advance(1_400L));
        assertEquals(SideButtonGesture.Event.RELEASE, gesture.up(1_500L, false));
        assertEquals(SideButtonGesture.Event.NONE, gesture.advance(1_700L));
    }

    @Test public void repeatedDownDoesNotRestartOrReemitHold() {
        SideButtonGesture gesture = new SideButtonGesture();
        gesture.down(1_000L);
        assertEquals(SideButtonGesture.Event.NONE, gesture.down(1_150L));
        assertEquals(SideButtonGesture.Event.HOLD, gesture.advance(1_200L));
        assertEquals(SideButtonGesture.Event.NONE, gesture.down(1_300L));
        assertEquals(SideButtonGesture.Event.NONE, gesture.advance(1_500L));
        assertEquals(SideButtonGesture.Event.RELEASE, gesture.up(1_501L, false));
    }

    @Test public void cancelledReleaseOverridesElapsedHoldThreshold() {
        SideButtonGesture gesture = new SideButtonGesture();
        gesture.down(1_000L);
        assertEquals(SideButtonGesture.Event.CANCEL, gesture.up(1_500L, true));
        assertFalse(gesture.isDown());
        assertEquals(SideButtonGesture.Event.NONE, gesture.up(1_501L, true));
    }

    @Test public void cancelledReleaseAfterHoldClearsThePress() {
        SideButtonGesture gesture = new SideButtonGesture();
        gesture.down(1_000L);
        gesture.advance(1_200L);
        assertEquals(SideButtonGesture.Event.CANCEL, gesture.up(1_300L, true));
        assertFalse(gesture.isDown());
        assertEquals(SideButtonGesture.Event.DOWN, gesture.down(1_400L));
        assertEquals(SideButtonGesture.Event.TAP, gesture.up(1_401L, false));
    }

    @Test public void resetDiscardsHeldPressAndItsLateEvents() {
        SideButtonGesture gesture = new SideButtonGesture();
        gesture.down(1_000L);
        gesture.advance(1_200L);
        gesture.reset();
        assertFalse(gesture.isDown());
        assertEquals(SideButtonGesture.Event.NONE, gesture.advance(1_300L));
        assertEquals(SideButtonGesture.Event.NONE, gesture.up(1_400L, false));
        assertEquals(SideButtonGesture.Event.DOWN, gesture.down(1_500L));
        assertEquals(SideButtonGesture.Event.TAP, gesture.up(1_699L, false));
    }
}
