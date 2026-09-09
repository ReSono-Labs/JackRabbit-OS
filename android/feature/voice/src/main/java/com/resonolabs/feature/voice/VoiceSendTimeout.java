package com.resonolabs.feature.voice;

/** Tracks stalled audio and DataChannel delivery using caller-supplied monotonic time. */
final class VoiceSendTimeout {
    private static final long TIMEOUT_MILLIS = 30_000L;

    private boolean pending;
    private long lastProgressMillis;
    private long previousBufferedBytes;

    void reset(long nowMillis) {
        pending = false;
        lastProgressMillis = nowMillis;
        previousBufferedBytes = 0L;
    }

    /** Called after a successful PCM append or an acknowledged input commit. */
    void audioProgress(long nowMillis) {
        pending = true;
        lastProgressMillis = nowMillis;
    }

    boolean expired(long nowMillis, boolean audioPending, long dataChannelBufferedBytes) {
        long bufferedBytes = Math.max(0L, dataChannelBufferedBytes);
        boolean hasPending = audioPending || bufferedBytes > 0L;
        if (hasPending && (!pending
                || (previousBufferedBytes == 0L && bufferedBytes > 0L)
                || bufferedBytes < previousBufferedBytes)) {
            lastProgressMillis = nowMillis;
        }
        previousBufferedBytes = bufferedBytes;
        pending = hasPending;
        return pending && nowMillis - lastProgressMillis >= TIMEOUT_MILLIS;
    }
}
