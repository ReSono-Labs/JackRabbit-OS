package com.resonolabs.feature.voice;

import static org.junit.Assert.*;

import java.util.ArrayList;
import java.util.List;
import org.json.JSONObject;
import org.junit.Test;

public class RealtimeInputCoordinatorTest {
    @Test public void silentCommittedItemRemainsIdentifiableForLateTranscription() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.event("input_audio_buffer.committed", "silence");
        assertTrue(f.input.isSilentItem("silence"));
        assertFalse(f.input.isSilentItem("unknown-item"));
        f.event("input_audio_buffer.committed", "silence");
        assertTrue(f.input.isSilentItem("silence"));
    }

    @Test public void voicedItemsRemainEligibleForTranscriptionEvenAfterCancellation() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "voice-a");
        f.input.endInput();
        f.event("input_audio_buffer.committed", "voice-a");
        assertFalse(f.input.isSilentItem("voice-a"));
        f.input.beginInput();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "voice-b");
        f.input.endInput();
        f.input.cancelPendingTurn();
        f.event("input_audio_buffer.committed", "voice-b");
        assertFalse(f.input.isSilentItem("voice-b"));
    }

    @Test public void closeAndResetDiscardPreviousSilentItemIdentities() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.event("input_audio_buffer.committed", "silence-a");
        f.input.close();
        assertFalse(f.input.isSilentItem("silence-a"));
        f.input.reset();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.event("input_audio_buffer.committed", "silence-b");
        assertTrue(f.input.isSilentItem("silence-b"));
        f.input.reset();
        assertFalse(f.input.isSilentItem("silence-b"));
    }

    @Test public void firstOfTwoManualAcknowledgementsKeepsCommitPending() throws Exception {
        Fixture f = new Fixture();
        assertFalse(f.input.hasPendingCommit());
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.input.beginInput();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        assertTrue(f.input.hasPendingCommit());
        f.event("input_audio_buffer.speech_started", "input-a");
        f.event("input_audio_buffer.committed", "input-a");
        assertTrue(f.input.hasPendingCommit());
        f.event("input_audio_buffer.speech_started", "input-b");
        f.event("input_audio_buffer.committed", "input-b");
        assertFalse(f.input.hasPendingCommit());
    }

    @Test public void finalExpectedEmptyErrorSettlesOnlyItsPendingManualCommit() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.input.beginInput();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.event("input_audio_buffer.speech_started", "input-a");
        f.event("input_audio_buffer.committed", "input-a");
        assertTrue(f.input.hasPendingCommit());
        assertTrue(f.input.onEvent(error(f.sent.get(1).getString("event_id"),
                "input_audio_buffer_commit_empty")));
        assertFalse(f.input.hasPendingCommit());
    }

    @Test public void cancelledInputStillWaitsForItsActualCommitAcknowledgement() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-a");
        f.input.endInput();
        f.input.cancelPendingTurn();
        assertTrue(f.input.hasPendingCommit());
        f.event("input_audio_buffer.committed", "input-a");
        assertFalse(f.input.hasPendingCommit());
        assertTrue(f.committed.isEmpty());
    }

    @Test public void releaseCommitsAppendedAudioBeforeDelayedVadArrives() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.input.endInput();
        assertEquals(1, f.sent.size());
        assertEquals("input_audio_buffer.commit", f.sent.get(0).getString("type"));
        assertTrue(f.committed.isEmpty());
        f.event("input_audio_buffer.speech_started", "input-1");
        assertTrue(f.input.isSpeaking());
        f.event("input_audio_buffer.committed", "input-1");
        f.event("input_audio_buffer.committed", "input-1");
        assertEquals(List.of("input-1:true"), f.committed);
        assertFalse(f.input.isSpeaking());
    }

    @Test public void vadAutoCommitPreventsRedundantReleaseCommit() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-1");
        f.event("input_audio_buffer.speech_stopped", "input-1");
        f.event("input_audio_buffer.committed", "input-1");
        f.input.endInput();
        assertTrue(f.sent.isEmpty());
        assertEquals(List.of("input-1:true"), f.committed);
        assertEquals(1, f.starts);
        assertEquals(1, f.stops);
    }

    @Test public void autoManualRaceConsumesOnlyCorrelatedEmptyBufferError() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-1");
        f.input.endInput();
        String commitId = f.sent.get(0).getString("event_id");
        f.event("input_audio_buffer.speech_stopped", "input-1");
        f.event("input_audio_buffer.committed", "input-1");
        assertFalse(f.input.onEvent(error("unrelated", "input_audio_buffer_commit_empty")));
        assertFalse(f.input.onEvent(error(commitId, "invalid_request_error")));
        assertTrue(f.input.onEvent(error(commitId, "input_audio_buffer_commit_empty")));
        assertFalse(f.input.onEvent(error(commitId, "input_audio_buffer_commit_empty")));
        assertEquals(List.of("input-1:true"), f.committed);
        assertTrue(f.failures.isEmpty());
    }

    @Test public void emptyErrorCannotHideLostKnownSpeechWithoutCommitAcknowledgement() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-1");
        f.input.endInput();
        assertFalse(f.input.onEvent(error(f.sent.get(0).getString("event_id"),
                "input_audio_buffer_commit_empty")));
    }

    @Test public void silenceCommitDeletesItemAndNeverRequestsAnAnswer() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.event("input_audio_buffer.committed", "silence");
        assertEquals(List.of("silence:false"), f.committed);
        assertEquals("conversation.item.delete", f.sent.get(1).getString("type"));
        assertEquals("silence", f.sent.get(1).getString("item_id"));
        f.event("input_audio_buffer.committed", "silence");
        assertEquals(2, f.sent.size());
    }

    @Test public void noAppendedAudioProducesNoCommit() {
        Fixture f = new Fixture();
        f.input.beginInput();
        f.input.onAudioAppended(0);
        f.input.endInput();
        assertTrue(f.sent.isEmpty());
        assertTrue(f.committed.isEmpty());
    }

    @Test public void cancellingInputSuppressesLateCommitAfterNewCaptureBegins() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.input.cancelPendingTurn();
        f.input.beginInput();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "old-input");
        f.event("input_audio_buffer.committed", "old-input");
        assertTrue(f.committed.isEmpty());
        f.event("input_audio_buffer.speech_started", "new-input");
        f.input.endInput();
        f.event("input_audio_buffer.committed", "new-input");
        assertEquals(List.of("new-input:true"), f.committed);
    }

    @Test public void continuedCaptureDoesNotReopenCancelledTurnWithoutBeginInput() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.input.cancelPendingTurn();
        f.input.endInput();
        f.event("input_audio_buffer.speech_started", "cancelled-input");
        f.event("input_audio_buffer.committed", "cancelled-input");
        assertTrue(f.committed.isEmpty());
        assertTrue(f.sent.stream().noneMatch(e -> "conversation.item.delete".equals(e.optString("type"))));
    }

    @Test public void promotingContinuousToHeldInputKeepsExistingVadSegment() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "continuous-input");
        f.input.beginInput();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.event("input_audio_buffer.committed", "continuous-input");
        assertEquals(List.of("continuous-input:true"), f.committed);
        assertEquals(1, f.sent.size());
    }

    @Test public void automaticCommitDoesNotDiscardAudioAppendedAfterSpeechStop() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-1");
        f.event("input_audio_buffer.speech_stopped", "input-1");
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.committed", "input-1");
        f.input.endInput();
        assertEquals(1, f.sent.size());
        f.event("input_audio_buffer.speech_started", "input-2");
        f.event("input_audio_buffer.committed", "input-2");
        assertEquals(List.of("input-1:true", "input-2:true"), f.committed);
    }

    @Test public void manualResidualSilenceAfterAutoCommitDoesNotProduceSecondAnswer() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-1");
        f.event("input_audio_buffer.speech_stopped", "input-1");
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.event("input_audio_buffer.committed", "input-1");
        f.event("input_audio_buffer.committed", "residual-silence");
        assertEquals(List.of("input-1:true", "residual-silence:false"), f.committed);
        assertEquals("conversation.item.delete", f.sent.get(1).getString("type"));
    }

    @Test public void autoAcknowledgementDoesNotHideTheRemainingManualSpeechSegment() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-a");
        f.event("input_audio_buffer.speech_stopped", "input-a");
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.event("input_audio_buffer.committed", "input-a");
        f.event("input_audio_buffer.speech_started", "provisional-b");
        f.event("input_audio_buffer.committed", "manual-b");
        assertEquals(List.of("input-a:true", "manual-b:true"), f.committed);
        assertEquals(1, f.sent.size());
        assertFalse(f.input.isSpeaking());
        assertFalse(f.input.onEvent(error(f.sent.get(0).getString("event_id"),
                "input_audio_buffer_commit_empty")));
    }

    @Test public void secondSpeechSegmentWithStableIdAlsoCompletesTheManualCommand() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-a");
        f.event("input_audio_buffer.speech_stopped", "input-a");
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.event("input_audio_buffer.committed", "input-a");
        f.event("input_audio_buffer.speech_started", "input-b");
        f.event("input_audio_buffer.committed", "input-b");
        assertEquals(List.of("input-a:true", "input-b:true"), f.committed);
        assertFalse(f.input.onEvent(error(f.sent.get(0).getString("event_id"),
                "input_audio_buffer_commit_empty")));
    }

    @Test public void earlierAutoAcknowledgementCannotHideUncommittedLaterSpeech() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-a");
        f.event("input_audio_buffer.speech_stopped", "input-a");
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.event("input_audio_buffer.committed", "input-a");
        f.event("input_audio_buffer.speech_started", "input-b");
        assertFalse(f.input.onEvent(error(f.sent.get(0).getString("event_id"),
                "input_audio_buffer_commit_empty")));
        assertTrue(f.input.isSpeaking());
    }

    @Test public void manualRemainderKeepsCancelledOwnerAfterNextCaptureBegins() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-a");
        f.event("input_audio_buffer.speech_stopped", "input-a");
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.input.cancelPendingTurn();
        f.input.beginInput();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.committed", "input-a");
        f.event("input_audio_buffer.speech_started", "provisional-b");
        f.event("input_audio_buffer.committed", "manual-b");
        assertTrue(f.committed.isEmpty());
        assertFalse(f.input.isSpeaking());
        assertEquals(1, f.sent.size());
    }

    @Test public void closeIgnoresLateEventsAndResetDoesNotReuseCommitIds() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        String oldId = f.sent.get(0).getString("event_id");
        f.input.close();
        f.event("input_audio_buffer.speech_started", "old-input");
        f.event("input_audio_buffer.committed", "old-input");
        f.input.endInput();
        assertTrue(f.committed.isEmpty());
        f.input.reset();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        assertNotEquals(oldId, f.sent.get(1).getString("event_id"));
        assertFalse(f.input.onEvent(error(oldId, "input_audio_buffer_commit_empty")));
    }

    @Test public void failedCommitSendReportsFailureWithoutInventingConfirmation() {
        Fixture f = new Fixture();
        f.sendSucceeds = false;
        f.input.onAudioAppended(9600);
        f.input.endInput();
        assertEquals(1, f.failures.size());
        assertTrue(f.committed.isEmpty());
    }

    @Test public void failedSilentDeletionDoesNotAcknowledgeInput() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.sendSucceeds = false;
        f.event("input_audio_buffer.committed", "silence");
        assertEquals(1, f.failures.size());
        assertTrue(f.committed.isEmpty());
    }

    @Test public void failedSilentDeletionCannotNotifyCommittedAfterFailureClosesSession() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.sendSucceeds = false;
        f.closeOnFailure = true;
        f.event("input_audio_buffer.committed", "silence");
        assertEquals(1, f.failures.size());
        assertTrue(f.committed.isEmpty());
    }

    @Test public void closingFromSpeechStoppedPreventsSubsequentCommitNotification() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-1");
        f.input.endInput();
        f.closeOnSpeechStopped = true;
        f.event("input_audio_buffer.committed", "input-1");
        assertEquals(1, f.stops);
        assertTrue(f.committed.isEmpty());
    }

    @Test public void manualCommitMayReplaceTheVadProvisionalItemId() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "vad-provisional");
        f.input.endInput();
        f.event("input_audio_buffer.committed", "manual-item");
        assertEquals(List.of("manual-item:true"), f.committed);
        assertEquals(1, f.sent.size());
        assertFalse(f.input.isSpeaking());
        f.event("input_audio_buffer.speech_stopped", "vad-provisional");
        f.event("input_audio_buffer.committed", "manual-item");
        assertEquals(1, f.committed.size());
    }

    @Test public void delayedVadStopUsesServerAudioBoundaryInsteadOfLatestAppend() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-1");
        f.input.onAudioAppended(9600);
        f.input.onEvent(new JSONObject().put("type", "input_audio_buffer.speech_stopped")
                .put("item_id", "input-1").put("audio_end_ms", 200));
        f.event("input_audio_buffer.committed", "input-1");
        f.input.endInput();
        assertEquals(1, f.sent.size());
        assertEquals("input_audio_buffer.commit", f.sent.get(0).getString("type"));
    }

    @Test public void completedManualCommitDoesNotStealLaterSilentInputOwnership() throws Exception {
        Fixture f = new Fixture();
        f.input.onAudioAppended(9600);
        f.event("input_audio_buffer.speech_started", "input-1");
        f.input.endInput();
        f.event("input_audio_buffer.committed", "input-1");
        f.input.cancelPendingTurn();
        f.input.beginInput();
        f.input.onAudioAppended(9600);
        f.input.endInput();
        f.event("input_audio_buffer.committed", "silence");
        assertEquals(List.of("input-1:true", "silence:false"), f.committed);
    }

    private static JSONObject error(String eventId, String code) throws Exception {
        return new JSONObject().put("type", "error").put("error", new JSONObject()
                .put("event_id", eventId).put("code", code).put("message", "Rejected commit"));
    }

    private static final class Fixture implements RealtimeInputCoordinator.Listener {
        final List<JSONObject> sent = new ArrayList<>();
        final List<String> committed = new ArrayList<>();
        final List<String> failures = new ArrayList<>();
        boolean sendSucceeds = true;
        boolean closeOnFailure;
        boolean closeOnSpeechStopped;
        int starts;
        int stops;
        final RealtimeInputCoordinator input = new RealtimeInputCoordinator(event -> {
            sent.add(event);
            return sendSucceeds;
        }, this);
        Fixture() { input.reset(); }
        void event(String type, String itemId) throws Exception {
            input.onEvent(new JSONObject().put("type", type).put("item_id", itemId));
        }
        @Override public void onCommitted(String itemId, boolean voiced) { committed.add(itemId + ":" + voiced); }
        @Override public void onSpeechStarted() { starts++; }
        @Override public void onSpeechStopped() {
            stops++;
            if (closeOnSpeechStopped) input.close();
        }
        @Override public void onFailure(String reason) {
            failures.add(reason);
            if (closeOnFailure) input.close();
        }
    }
}
