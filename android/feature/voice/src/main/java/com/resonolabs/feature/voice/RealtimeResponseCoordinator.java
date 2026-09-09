package com.resonolabs.feature.voice;

import org.json.JSONObject;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

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
    private final Set<String> requestedInputIds = new HashSet<>();
    private final Set<Long> cancelledRounds = new HashSet<>();
    private final Map<String, Long> responseRounds = new HashMap<>();
    private final Set<String> completedResponseIds = new HashSet<>();
    private JSONObject pendingResponseCreate;
    private boolean providerResponseInFlight;
    private String activeResponseId;
    private long activeResponseRound;
    private long round;
    private boolean held;
    private boolean closed = true;

    RealtimeResponseCoordinator(Sender sender, Scheduler scheduler, Runnable onSendFailure) {
        this.sender = sender;
        this.scheduler = scheduler;
        this.onSendFailure = onSendFailure;
    }

    void reset() {
        close();
        requestedInputIds.clear();
        cancelledRounds.clear();
        responseRounds.clear();
        completedResponseIds.clear();
        closed = false;
        round++;
    }

    void close() {
        closed = true;
        scheduler.cancel(retry);
        pendingResponseCreate = null;
        providerResponseInFlight = false;
        activeResponseId = null;
        held = false;
    }

    long beginRound() {
        if (closed) return round;
        scheduler.cancel(retry);
        pendingResponseCreate = null;
        return ++round;
    }

    long currentRound() { return round; }

    boolean acceptsRound(long token) {
        return !closed && token == round && !cancelledRounds.contains(token);
    }

    boolean isInFlight() { return !closed && providerResponseInFlight; }

    boolean isResponseCancelled(String responseId) {
        Long responseRound = responseRounds.get(responseId);
        return responseRound != null && cancelledRounds.contains(responseRound);
    }

    void cancelCurrentRound() {
        if (closed) return;
        cancelledRounds.add(round);
        scheduler.cancel(retry);
        pendingResponseCreate = null;
        // Keep the provider's active slot until its terminal event arrives.
    }

    void setHeld(boolean value) {
        if (closed) return;
        held = value;
        if (!held) sendPendingIfIdle();
    }

    void requestForInput(String itemId) {
        if (closed || itemId == null || itemId.isEmpty() || !requestedInputIds.add(itemId)) return;
        beginRound();
        requestDefault();
    }

    void requestContinuation(long token) {
        if (acceptsRound(token)) requestDefault();
    }

    void onResponseCreated() {
        onResponseCreated(null);
    }

    void onResponseCreated(String responseId) {
        if (closed || completedResponseIds.contains(responseId)) return;
        if (responseId != null && responseRounds.containsKey(responseId)
                && !responseId.equals(activeResponseId)) return;
        if (activeResponseId != null && !activeResponseId.equals(responseId)) return;
        if (!providerResponseInFlight) activeResponseRound = round;
        providerResponseInFlight = true;
        activeResponseId = responseId;
        if (responseId != null) responseRounds.put(responseId, activeResponseRound);
    }

    void onResponseDone() {
        onResponseDone(activeResponseId);
    }

    void onResponseDone(String responseId) {
        if (closed || !providerResponseInFlight || completedResponseIds.contains(responseId)) return;
        if (activeResponseId != null && !activeResponseId.equals(responseId)) return;
        if (responseId != null && responseRounds.containsKey(responseId)
                && responseRounds.get(responseId) != activeResponseRound) return;
        if (responseId != null) {
            completedResponseIds.add(responseId);
            responseRounds.put(responseId, activeResponseRound);
        }
        providerResponseInFlight = false;
        activeResponseId = null;
        scheduler.cancel(retry);
        sendPendingIfIdle();
    }

    void onActiveResponseRejection() {
        if (!closed && !providerResponseInFlight) {
            providerResponseInFlight = true;
            activeResponseRound = round;
        }
    }

    void request(JSONObject responseCreateEvent) {
        if (!acceptsRound(round) || responseCreateEvent == null
                || !"response.create".equals(responseCreateEvent.optString("type"))) return;
        try {
            JSONObject event = new JSONObject(responseCreateEvent.toString());
            JSONObject response = event.optJSONObject("response");
            if (response == null) response = new JSONObject();
            JSONObject metadata = response.optJSONObject("metadata");
            if (metadata == null) metadata = new JSONObject();
            metadata.put("resono_round", Long.toString(round));
            response.put("metadata", metadata);
            event.put("response", response);
            pendingResponseCreate = event;
        } catch (Exception ignored) {
            onSendFailure.run();
            return;
        }
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
        if (!acceptsRound(round) || held || pendingResponseCreate == null
                || providerResponseInFlight) return false;
        JSONObject event = pendingResponseCreate;
        pendingResponseCreate = null;
        providerResponseInFlight = true;
        activeResponseRound = round;
        activeResponseId = null;
        if (sender.send(event)) return true;
        providerResponseInFlight = false;
        pendingResponseCreate = event;
        onSendFailure.run();
        return false;
    }
}
