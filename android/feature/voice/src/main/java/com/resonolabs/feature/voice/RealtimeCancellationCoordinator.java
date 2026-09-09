package com.resonolabs.feature.voice;

import java.util.HashSet;
import java.util.Set;
import org.json.JSONObject;

/** Correlates the harmless race between response.cancel and response.done. */
final class RealtimeCancellationCoordinator {
    interface Sender { boolean send(JSONObject event); }

    private final Sender sender;
    private final Runnable onFailure;
    private final Set<String> pendingEventIds = new HashSet<>();
    private long eventSequence;
    private boolean closed = true;

    RealtimeCancellationCoordinator(Sender sender, Runnable onFailure) {
        this.sender = sender;
        this.onFailure = onFailure;
    }

    void reset() {
        pendingEventIds.clear();
        closed = false;
    }

    void close() {
        closed = true;
        pendingEventIds.clear();
    }

    void cancel(String responseId) {
        if (closed) return;
        String eventId = "resono-response-cancel-" + (++eventSequence);
        boolean sent = false;
        try {
            JSONObject event = new JSONObject().put("type", "response.cancel").put("event_id", eventId);
            if (responseId != null && !responseId.isEmpty()) event.put("response_id", responseId);
            pendingEventIds.add(eventId);
            sent = sender.send(event);
        } catch (Exception ignored) {
            // A malformed or unsent request cannot own a subsequent provider error.
        }
        if (!sent) {
            pendingEventIds.remove(eventId);
            onFailure.run();
        }
    }

    boolean onError(JSONObject error) {
        return !closed && error != null
                && "response_cancel_not_active".equals(error.optString("code"))
                && pendingEventIds.remove(error.optString("event_id"));
    }
}
