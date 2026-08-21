package com.resonolabs.feature.voice;

import org.json.JSONObject;

/** Single owner for every client-originated Realtime response.create event. */
final class RealtimeResponseCoordinator {
    interface Sender {
        boolean send(JSONObject event);
    }

    interface Scheduler {
        void schedule(Runnable runnable, long delayMillis);
        void cancel(Runnable runnable);
    }

    private static final long RETRY_DELAY_MILLIS = 150L;

    private final Sender sender;
    private final Scheduler scheduler;
    private final Runnable onSendFailure;
    private final Runnable retry = this::sendPendingIfIdle;
    private JSONObject pendingResponseCreate;
    private boolean providerResponseInFlight;
    private boolean closed = true;

    RealtimeResponseCoordinator(Sender sender, Scheduler scheduler, Runnable onSendFailure) {
        this.sender = sender;
        this.scheduler = scheduler;
        this.onSendFailure = onSendFailure;
    }

    void reset() {
        scheduler.cancel(retry);
        pendingResponseCreate = null;
        providerResponseInFlight = false;
        closed = false;
    }

    void close() {
        closed = true;
        scheduler.cancel(retry);
        pendingResponseCreate = null;
        providerResponseInFlight = false;
    }

    void onResponseCreated() {
        if (!closed) providerResponseInFlight = true;
    }

    void onResponseDone() {
        if (closed) return;
        providerResponseInFlight = false;
        scheduler.cancel(retry);
        sendPendingIfIdle();
    }

    void onActiveResponseRejection() {
        if (!closed) providerResponseInFlight = true;
    }

    void request(JSONObject responseCreateEvent) {
        if (closed || responseCreateEvent == null
                || !"response.create".equals(responseCreateEvent.optString("type"))) return;
        pendingResponseCreate = responseCreateEvent;
        if (sendPendingIfIdle()) {
            scheduler.cancel(retry);
            return;
        }
        scheduler.cancel(retry);
        scheduler.schedule(retry, RETRY_DELAY_MILLIS);
    }

    void requestDefault() {
        try {
            request(new JSONObject().put("type", "response.create"));
        } catch (Exception ignored) {
            onSendFailure.run();
        }
    }

    private boolean sendPendingIfIdle() {
        if (closed || pendingResponseCreate == null || providerResponseInFlight) return false;
        JSONObject event = pendingResponseCreate;
        pendingResponseCreate = null;
        providerResponseInFlight = true;
        if (sender.send(event)) return true;
        providerResponseInFlight = false;
        pendingResponseCreate = event;
        onSendFailure.run();
        return false;
    }
}
