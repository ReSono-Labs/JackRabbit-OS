package com.resonolabs.feature.voice;

import static org.junit.Assert.*;

import java.util.ArrayList;
import java.util.List;
import org.json.JSONObject;
import org.junit.Test;

public final class RealtimeCancellationCoordinatorTest {
    @Test public void cancelTargetsKnownResponseAndCorrelatesItsBenignRace() throws Exception {
        Fixture f = new Fixture();
        f.coordinator.cancel("response-1");
        JSONObject request = f.sent.get(0);
        assertEquals("response.cancel", request.getString("type"));
        assertEquals("response-1", request.getString("response_id"));
        assertFalse(request.getString("event_id").isEmpty());
        JSONObject error = error(request.getString("event_id"), "response_cancel_not_active");
        assertTrue(f.coordinator.onError(error));
        assertFalse(f.coordinator.onError(error));
        assertEquals(0, f.failures);
    }

    @Test public void unknownResponseCanBeCancelledBeforeCreatedAcknowledgement() throws Exception {
        Fixture f = new Fixture();
        f.coordinator.cancel("");
        f.coordinator.cancel(null);
        assertFalse(f.sent.get(0).has("response_id"));
        assertFalse(f.sent.get(1).has("response_id"));
        assertNotEquals(f.sent.get(0).getString("event_id"), f.sent.get(1).getString("event_id"));
    }

    @Test public void unrelatedErrorsAreNotHiddenEvenWhenTheirCodeOrIdMatches() throws Exception {
        Fixture f = new Fixture();
        f.coordinator.cancel("response-1");
        String eventId = f.sent.get(0).getString("event_id");
        assertFalse(f.coordinator.onError(error("another-command", "response_cancel_not_active")));
        assertFalse(f.coordinator.onError(error(eventId, "invalid_request_error")));
        assertFalse(f.coordinator.onError(new JSONObject().put("code", "response_cancel_not_active")));
        assertFalse(f.coordinator.onError(null));
        assertTrue(f.coordinator.onError(error(eventId, "response_cancel_not_active")));
    }

    @Test public void eachOutstandingCancellationHasItsOwnErrorIdentity() throws Exception {
        Fixture f = new Fixture();
        f.coordinator.cancel("response-1");
        f.coordinator.cancel("response-2");
        assertTrue(f.coordinator.onError(error(f.sent.get(1).getString("event_id"), "response_cancel_not_active")));
        assertTrue(f.coordinator.onError(error(f.sent.get(0).getString("event_id"), "response_cancel_not_active")));
    }

    @Test public void resetAndCloseRejectOldCallbacksWithoutReusingClientIds() throws Exception {
        Fixture f = new Fixture();
        f.coordinator.cancel("response-1");
        String oldId = f.sent.get(0).getString("event_id");
        f.coordinator.close();
        f.coordinator.cancel("response-2");
        assertEquals(1, f.sent.size());
        assertFalse(f.coordinator.onError(error(oldId, "response_cancel_not_active")));
        f.coordinator.reset();
        f.coordinator.cancel("response-3");
        assertNotEquals(oldId, f.sent.get(1).getString("event_id"));
        assertFalse(f.coordinator.onError(error(oldId, "response_cancel_not_active")));
    }

    @Test public void unsentCancellationReportsFailureAndCannotConsumeProviderError() throws Exception {
        Fixture f = new Fixture();
        f.sendSucceeds = false;
        f.coordinator.cancel("response-1");
        assertEquals(1, f.failures);
        assertFalse(f.coordinator.onError(error(f.sent.get(0).getString("event_id"), "response_cancel_not_active")));
    }

    private static JSONObject error(String eventId, String code) throws Exception {
        return new JSONObject().put("event_id", eventId).put("code", code);
    }

    private static final class Fixture {
        final List<JSONObject> sent = new ArrayList<>();
        int failures;
        boolean sendSucceeds = true;
        final RealtimeCancellationCoordinator coordinator = new RealtimeCancellationCoordinator(event -> {
            sent.add(event);
            return sendSucceeds;
        }, () -> failures++);
        Fixture() { coordinator.reset(); }
    }
}
