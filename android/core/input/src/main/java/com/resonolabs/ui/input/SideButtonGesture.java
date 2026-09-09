package com.resonolabs.ui.input;

/** Deterministic side-button gestures using caller-supplied monotonic time. */
public final class SideButtonGesture {
    public static final long HOLD_MILLIS = 200L;

    public enum Event { NONE, DOWN, HOLD, TAP, RELEASE, CANCEL }

    private boolean pressed;
    private boolean held;
    private long pressedAtMillis;

    public Event down(long nowMillis) {
        if (pressed) return Event.NONE;
        pressed = true;
        held = false;
        pressedAtMillis = nowMillis;
        return Event.DOWN;
    }

    public Event advance(long nowMillis) {
        if (!pressed || held || nowMillis - pressedAtMillis < HOLD_MILLIS) {
            return Event.NONE;
        }
        held = true;
        return Event.HOLD;
    }

    public Event up(long nowMillis, boolean cancelled) {
        if (!pressed) return Event.NONE;
        // Key-up can arrive before the scheduled HOLD callback is delivered.
        boolean wasHeld = held || nowMillis - pressedAtMillis >= HOLD_MILLIS;
        reset();
        if (cancelled) return Event.CANCEL;
        return wasHeld ? Event.RELEASE : Event.TAP;
    }

    public boolean isDown() {
        return pressed;
    }

    public void reset() {
        pressed = false;
        held = false;
        pressedAtMillis = 0L;
    }
}
