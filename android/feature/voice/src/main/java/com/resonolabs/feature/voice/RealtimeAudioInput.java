package com.resonolabs.feature.voice;

import java.util.ArrayDeque;

/**
 * Owns unsent 24 kHz mono PCM16 on the capture thread and the session thread.
 * Gesture times and capture timestamps must use the System.nanoTime() clock domain.
 * A failed queue stops draining until its owner reports the failure and resets it.
 */
final class RealtimeAudioInput {
    static final int MAX_BUFFERED_BYTES = 1_440_000;
    enum OfferResult { ACCEPTED, IGNORED, OVERFLOW }

    static final class Entry {
        private final byte[] pcm;
        private final long captureTimeNanos;

        private Entry(byte[] pcm, long captureTimeNanos) {
            this.pcm = pcm == null ? null : pcm.clone();
            this.captureTimeNanos = captureTimeNanos;
        }

        boolean isEnd() { return pcm == null; }
        byte[] pcm() { return pcm == null ? null : pcm.clone(); }
        long captureTimeNanos() { return captureTimeNanos; }
    }

    private enum Gate { CLOSED, CANDIDATE, STREAM }

    private final ArrayDeque<Entry> ready = new ArrayDeque<>();
    private final ArrayDeque<Entry> candidate = new ArrayDeque<>();
    private Gate gate = Gate.CLOSED;
    private long openedAtNanos;
    private long candidateAtNanos;
    private boolean previousStream;
    private boolean streamHasAudio;
    private boolean failed;
    private int queuedBytes;

    /** Opens a separate candidate without losing already authorized stream audio. */
    synchronized void beginCandidate(long nowNanos) {
        if (failed || gate == Gate.CANDIDATE) return;
        previousStream = gate == Gate.STREAM;
        if (!previousStream) openedAtNanos = nowNanos;
        candidateAtNanos = nowNanos;
        gate = Gate.CANDIDATE;
    }

    synchronized void confirmCandidate() {
        if (failed || gate != Gate.CANDIDATE) return;
        if (!candidate.isEmpty()) streamHasAudio = true;
        ready.addAll(candidate);
        candidate.clear();
        gate = Gate.STREAM;
        previousStream = false;
    }

    /** Closes admission immediately; END stays behind every earlier confirmed frame. */
    synchronized void release(boolean submit, long nowNanos) {
        if (failed || gate == Gate.CLOSED) return;
        if (submit) confirmCandidate();
        for (Entry entry : candidate) queuedBytes -= entry.pcm.length;
        candidate.clear();
        gate = Gate.CLOSED;
        previousStream = false;
        if (streamHasAudio) ready.addLast(new Entry(null, nowNanos));
        streamHasAudio = false;
    }

    synchronized void setContinuous(boolean enabled, long nowNanos) {
        if (failed) return;
        if (!enabled) {
            release(true, nowNanos);
            return;
        }
        if (gate == Gate.CANDIDATE) confirmCandidate();
        if (gate == Gate.CLOSED) openedAtNanos = nowNanos;
        gate = Gate.STREAM;
    }

    synchronized void reset() {
        ready.clear();
        candidate.clear();
        gate = Gate.CLOSED;
        previousStream = false;
        streamHasAudio = false;
        queuedBytes = 0;
        failed = false;
    }

    /**
     * Backlog is the raw DataChannel bufferedAmount, counted conservatively as PCM
     * bytes even though it includes base64/JSON overhead. Never overwrites old audio.
     */
    synchronized OfferResult offer(byte[] pcm, long captureTimeNanos,
                                   long dataChannelBufferedBytes) {
        if (failed || gate == Gate.CLOSED || captureTimeNanos < openedAtNanos) {
            return OfferResult.IGNORED;
        }
        if (pcm == null || pcm.length == 0) return OfferResult.IGNORED;
        if ((pcm.length & 1) != 0) throw new IllegalArgumentException("PCM16 requires complete samples");
        long remaining = MAX_BUFFERED_BYTES - (long) queuedBytes - pcm.length;
        if (remaining < 0 || Math.max(0L, dataChannelBufferedBytes) > remaining) {
            gate = Gate.CLOSED;
            failed = true;
            return OfferResult.OVERFLOW;
        }
        Entry entry = new Entry(pcm, captureTimeNanos);
        if (gate == Gate.CANDIDATE
                && !(previousStream && captureTimeNanos < candidateAtNanos)) {
            candidate.addLast(entry);
        } else {
            ready.addLast(entry);
            streamHasAudio = true;
        }
        queuedBytes += pcm.length;
        return OfferResult.ACCEPTED;
    }

    synchronized Entry peek() { return failed ? null : ready.peekFirst(); }

    /** Call only after the peeked append/END was handled successfully by the session. */
    synchronized Entry poll() {
        if (failed) return null;
        Entry entry = ready.pollFirst();
        if (entry != null && !entry.isEnd()) queuedBytes -= entry.pcm.length;
        return entry;
    }

    synchronized boolean hasPending() { return !ready.isEmpty() || !candidate.isEmpty(); }
    synchronized boolean failed() { return failed; }
    synchronized int queuedBytes() { return queuedBytes; }
}
