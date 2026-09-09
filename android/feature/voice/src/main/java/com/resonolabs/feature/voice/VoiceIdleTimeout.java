package com.resonolabs.feature.voice;

/** Idle deadline using caller-supplied monotonic time and settled-round state. */
final class VoiceIdleTimeout {
    static final long TIMEOUT_MILLIS = 600_000L;

    private boolean connected;
    private boolean busy;
    private long idleSinceMillis;

    void connected(long nowMillis) {
        connected = true;
        busy = false;
        idleSinceMillis = nowMillis;
    }

    void update(long nowMillis, boolean busy) {
        if (!connected) return;
        if (this.busy && !busy) idleSinceMillis = nowMillis;
        this.busy = busy;
    }

    void reset() {
        connected = false;
        busy = false;
        idleSinceMillis = 0L;
    }

    boolean expired(long nowMillis) {
        return connected && !busy && nowMillis - idleSinceMillis >= TIMEOUT_MILLIS;
    }
}
