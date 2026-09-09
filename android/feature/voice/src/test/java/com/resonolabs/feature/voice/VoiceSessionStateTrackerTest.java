package com.resonolabs.feature.voice;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class VoiceSessionStateTrackerTest {
    @Test public void responseCompletesBackToLive() {
        VoiceSessionStateTracker tracker = new VoiceSessionStateTracker();
        tracker.connecting();
        tracker.live();
        tracker.onRealtimeEvent("input_audio_buffer.speech_stopped");
        assertEquals(VoiceSessionStateTracker.State.RESPONDING, tracker.state());
        tracker.onRealtimeEvent("response.created");
        tracker.onRealtimeEvent("response.output_audio_transcript.done");
        assertEquals(VoiceSessionStateTracker.State.RESPONDING, tracker.state());
        tracker.onRealtimeEvent("response.done");
        assertEquals(VoiceSessionStateTracker.State.LIVE, tracker.state());
    }

    @Test public void toolAndFollowUpRemainRespondingUntilFollowUpDone() {
        VoiceSessionStateTracker tracker = new VoiceSessionStateTracker();
        tracker.live();
        tracker.onRealtimeEvent("response.function_call_arguments.done");
        tracker.onRealtimeEvent("response.done");
        assertEquals(VoiceSessionStateTracker.State.RESPONDING, tracker.state());
        tracker.toolOutputSent();
        tracker.onRealtimeEvent("response.done");
        assertEquals(VoiceSessionStateTracker.State.RESPONDING, tracker.state());
        tracker.onRealtimeEvent("response.created");
        tracker.onRealtimeEvent("response.done");
        assertEquals(VoiceSessionStateTracker.State.LIVE, tracker.state());
    }

    @Test public void resetClearsToolState() {
        VoiceSessionStateTracker tracker = new VoiceSessionStateTracker();
        tracker.onRealtimeEvent("response.function_call_arguments.done");
        tracker.error();
        tracker.connecting();
        tracker.live();
        tracker.onRealtimeEvent("response.done");
        assertEquals(VoiceSessionStateTracker.State.LIVE, tracker.state());
    }

    @Test public void cancelledPendingToolsDoNotKeepTheNextRoundResponding() {
        VoiceSessionStateTracker tracker = new VoiceSessionStateTracker();
        tracker.live();
        tracker.onRealtimeEvent("response.function_call_arguments.done");
        tracker.onRealtimeEvent("response.function_call_arguments.done");
        tracker.onRealtimeEvent("response.done");
        tracker.cancelRound();
        assertEquals(VoiceSessionStateTracker.State.LIVE, tracker.state());
        tracker.onRealtimeEvent("response.created");
        tracker.onRealtimeEvent("response.done");
        assertEquals(VoiceSessionStateTracker.State.LIVE, tracker.state());
    }

    @Test public void cancellationDropsAQueuedToolFollowUp() {
        VoiceSessionStateTracker tracker = new VoiceSessionStateTracker();
        tracker.live();
        tracker.onRealtimeEvent("response.function_call_arguments.done");
        tracker.toolOutputSent();
        tracker.cancelRound();
        tracker.onRealtimeEvent("response.done");
        assertEquals(VoiceSessionStateTracker.State.LIVE, tracker.state());
    }

    @Test public void cancellingBeforeReadyDoesNotInventALiveConnection() {
        VoiceSessionStateTracker tracker = new VoiceSessionStateTracker();
        tracker.cancelRound();
        assertEquals(VoiceSessionStateTracker.State.IDLE, tracker.state());
        tracker.connecting();
        tracker.cancelRound();
        assertEquals(VoiceSessionStateTracker.State.CONNECTING, tracker.state());
        tracker.error();
        tracker.cancelRound();
        assertEquals(VoiceSessionStateTracker.State.ERROR, tracker.state());
    }

    @Test public void previousPlaybackCanFinishAfterATextOnlyContinuationStarts() {
        VoiceSessionStateTracker tracker = new VoiceSessionStateTracker();
        tracker.live();
        tracker.onRealtimeEvent("response.created");
        tracker.playbackStarted("response-a");
        tracker.onRealtimeEvent("response.done");
        assertTrue(tracker.isPlaying());
        tracker.onRealtimeEvent("response.created");
        tracker.playbackStopped("response-a");
        assertFalse(tracker.isPlaying());
        assertEquals(VoiceSessionStateTracker.State.RESPONDING, tracker.state());
        tracker.onRealtimeEvent("response.done");
        assertEquals(VoiceSessionStateTracker.State.LIVE, tracker.state());
    }

    @Test public void overlappingOutputStopsOnlyAfterEveryResponseDrains() {
        VoiceSessionStateTracker tracker = new VoiceSessionStateTracker();
        tracker.playbackStarted("response-a");
        tracker.playbackStarted("response-b");
        tracker.playbackStopped("response-a");
        assertTrue(tracker.isPlaying());
        tracker.playbackStopped("response-b");
        assertFalse(tracker.isPlaying());
    }

    @Test public void unknownAndDuplicateOutputEventsCannotStopCurrentPlayback() {
        VoiceSessionStateTracker tracker = new VoiceSessionStateTracker();
        tracker.playbackStarted("response-a");
        tracker.playbackStarted("response-a");
        tracker.playbackStopped("unknown-response");
        assertTrue(tracker.isPlaying());
        tracker.playbackStopped("response-a");
        assertFalse(tracker.isPlaying());
        tracker.playbackStarted("response-b");
        tracker.playbackStopped("response-a");
        assertTrue(tracker.isPlaying());
    }

    @Test public void resettingToolRoundKeepsPlaybackUntilItIsExplicitlyCleared() {
        VoiceSessionStateTracker tracker = new VoiceSessionStateTracker();
        tracker.onRealtimeEvent("response.created");
        tracker.playbackStarted("response-a");
        tracker.cancelRound();
        assertTrue(tracker.isPlaying());
        tracker.clearPlayback();
        assertFalse(tracker.isPlaying());
        tracker.playbackStarted("");
        tracker.playbackStarted(null);
        assertFalse(tracker.isPlaying());
    }

    @Test public void connectionLifecycleDropsPreviousPlaybackIdentities() {
        VoiceSessionStateTracker tracker = new VoiceSessionStateTracker();
        tracker.playbackStarted("response-a");
        tracker.idle();
        assertFalse(tracker.isPlaying());
        tracker.playbackStarted("response-b");
        tracker.error();
        assertFalse(tracker.isPlaying());
        tracker.playbackStarted("response-c");
        tracker.connecting();
        assertFalse(tracker.isPlaying());
    }
}
