package com.resonolabs.feature.voice;

import java.util.ArrayDeque;

/** Serializes Realtime tool execution so completion callbacks cannot race. */
final class RealtimeToolCallQueue {
    interface Completion {
        void complete();
    }

    interface Invocation {
        void execute(Completion completion);
    }

    private final ArrayDeque<Invocation> pending = new ArrayDeque<>();
    private boolean running;
    private boolean closed = true;
    private long generation;

    void reset() {
        generation++;
        pending.clear();
        running = false;
        closed = false;
    }

    void close() {
        generation++;
        closed = true;
        pending.clear();
        running = false;
    }

    void enqueue(Invocation invocation) {
        if (closed || invocation == null) return;
        pending.addLast(invocation);
        startNext();
    }

    private void startNext() {
        if (closed || running) return;
        Invocation invocation = pending.pollFirst();
        if (invocation == null) return;
        running = true;
        final long invocationGeneration = generation;
        final boolean[] completed = {false};
        try {
            invocation.execute(() -> {
                if (completed[0]) return;
                completed[0] = true;
                if (invocationGeneration != generation) return;
                running = false;
                startNext();
            });
        } catch (Exception ignored) {
            if (completed[0] || invocationGeneration != generation) return;
            completed[0] = true;
            running = false;
            startNext();
        }
    }
}
