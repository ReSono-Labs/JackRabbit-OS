package com.resonolabs.feature.voice;

import static org.junit.Assert.*;

import java.util.ArrayList;
import java.util.List;
import org.json.JSONObject;
import org.junit.Test;

public class RealtimeResponseCoordinatorTest {
    @Test public void committedInputStartsOneResponseAndToolsContinueItsRound() {
        Fixture f = new Fixture();
        f.coordinator.requestForInput("input-1");
        long round = f.coordinator.currentRound();
        f.coordinator.onResponseCreated("response-1");
        f.coordinator.requestForInput("input-1");
        f.coordinator.onResponseDone("response-1");
        assertEquals(1, f.sent.size());
        f.coordinator.requestContinuation(round);
        assertEquals(2, f.sent.size());
        assertEquals(round, f.coordinator.currentRound());
        assertEquals(Long.toString(round), f.sent.get(1).optJSONObject("response")
                .optJSONObject("metadata").optString("resono_round"));
    }

    @Test public void cancelledRoundDropsHeldRequestAndLateToolContinuation() {
        Fixture f = new Fixture();
        f.coordinator.setHeld(true);
        f.coordinator.requestForInput("input-1");
        long cancelled = f.coordinator.currentRound();
        f.coordinator.cancelCurrentRound();
        f.coordinator.setHeld(false);
        f.coordinator.requestContinuation(cancelled);
        f.coordinator.requestDefault();
        assertTrue(f.sent.isEmpty());
        assertFalse(f.coordinator.acceptsRound(cancelled));
        f.coordinator.requestForInput("input-2");
        assertEquals(1, f.sent.size());
        assertTrue(f.coordinator.acceptsRound(f.coordinator.currentRound()));
    }

    @Test public void oldDoneCannotUnlockNewInFlightResponse() {
        Fixture f = new Fixture();
        f.coordinator.requestForInput("input-1");
        f.coordinator.onResponseCreated("response-1");
        f.coordinator.cancelCurrentRound();
        assertTrue(f.coordinator.isResponseCancelled("response-1"));
        f.coordinator.requestForInput("input-2");
        assertEquals(1, f.sent.size());
        f.coordinator.onResponseDone("response-1");
        assertEquals(2, f.sent.size());
        f.coordinator.onResponseCreated("response-2");
        f.coordinator.requestContinuation(f.coordinator.currentRound());
        f.coordinator.onResponseDone("response-1");
        assertTrue(f.coordinator.isInFlight());
        assertEquals(2, f.sent.size());
        f.coordinator.onResponseDone("response-2");
        assertEquals(3, f.sent.size());
    }

    @Test public void gestureHoldDefersOnlyNewRequests() {
        Fixture f = new Fixture();
        f.coordinator.requestForInput("input-1");
        f.coordinator.onResponseCreated("response-1");
        f.coordinator.setHeld(true);
        f.coordinator.requestContinuation(f.coordinator.currentRound());
        f.coordinator.onResponseDone("response-1");
        assertEquals(1, f.sent.size());
        f.coordinator.setHeld(false);
        assertEquals(2, f.sent.size());
    }

    @Test public void lateCreatedRetainsCancelledIdentityUntilTerminalEvent() {
        Fixture f = new Fixture();
        f.coordinator.requestForInput("input-1");
        f.coordinator.cancelCurrentRound();
        f.coordinator.requestForInput("input-2");
        f.coordinator.onResponseCreated("late-response-1");
        assertTrue(f.coordinator.isResponseCancelled("late-response-1"));
        f.coordinator.onResponseDone("late-response-1");
        assertEquals(2, f.sent.size());
        f.coordinator.onResponseCreated("response-2");
        assertFalse(f.coordinator.isResponseCancelled("response-2"));
    }

    @Test public void staleCreatedAndDoneDoNotReleaseAnUnacknowledgedNewRequest() {
        Fixture f = new Fixture();
        f.coordinator.requestDefault();
        f.coordinator.onResponseCreated("response-1");
        f.coordinator.onResponseDone("response-1");
        f.coordinator.requestForInput("input-2");
        f.coordinator.onResponseCreated("response-1");
        f.coordinator.onResponseDone("response-1");
        f.coordinator.requestContinuation(f.coordinator.currentRound());
        assertEquals(2, f.sent.size());
        assertTrue(f.coordinator.isInFlight());
    }

    @Test public void legacyRequestPreservesResponseAndMetadataWithoutMutatingCaller() throws Exception {
        Fixture f = new Fixture();
        JSONObject original = new JSONObject("{\"type\":\"response.create\",\"response\":{"
                + "\"instructions\":\"describe the image\",\"metadata\":{\"origin\":\"camera\"}}}");
        f.coordinator.request(original);
        JSONObject response = f.sent.get(0).getJSONObject("response");
        assertEquals("describe the image", response.getString("instructions"));
        assertEquals("camera", response.getJSONObject("metadata").getString("origin"));
        assertFalse(original.getJSONObject("response").getJSONObject("metadata").has("resono_round"));
        f.coordinator.onResponseCreated();
        f.coordinator.onResponseDone();
        assertFalse(f.coordinator.isInFlight());
    }

    @Test public void resetInvalidatesPreviousRoundAndCloseDiscardsRetries() {
        Fixture f = new Fixture();
        long oldRound = f.coordinator.currentRound();
        f.coordinator.reset();
        assertFalse(f.coordinator.acceptsRound(oldRound));
        f.sendSucceeds = false;
        f.coordinator.requestDefault();
        assertEquals(1, f.failures);
        assertNotNull(f.scheduled);
        Runnable retry = f.scheduled;
        f.coordinator.close();
        f.sendSucceeds = true;
        retry.run();
        assertEquals(1, f.sent.size());
    }

    private static final class Fixture implements RealtimeResponseCoordinator.Scheduler {
        final List<JSONObject> sent = new ArrayList<>();
        Runnable scheduled;
        int failures;
        boolean sendSucceeds = true;
        final RealtimeResponseCoordinator coordinator = new RealtimeResponseCoordinator(event -> {
            sent.add(event);
            return sendSucceeds;
        }, this, () -> failures++);
        Fixture() { coordinator.reset(); }
        @Override public void schedule(Runnable action, long delayMillis) { scheduled = action; }
        @Override public void cancel(Runnable action) { if (scheduled == action) scheduled = null; }
    }
}
