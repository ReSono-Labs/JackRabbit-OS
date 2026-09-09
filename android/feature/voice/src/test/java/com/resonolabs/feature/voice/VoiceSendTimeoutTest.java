package com.resonolabs.feature.voice;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class VoiceSendTimeoutTest {
    @Test public void stalledLocalAudioExpiresAtThirtySecondsDespitePolling() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(1_000L);
        assertFalse(timeout.expired(1_000L, true, 0L));
        assertFalse(timeout.expired(20_000L, true, 0L));
        assertFalse(timeout.expired(30_999L, true, 0L));
        assertTrue(timeout.expired(31_000L, true, 0L));
    }

    @Test public void appendBeforeFirstPollStartsTheProgressDeadline() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(0L);
        timeout.audioProgress(1_000L);
        assertFalse(timeout.expired(30_999L, true, 0L));
        assertTrue(timeout.expired(31_000L, true, 0L));
    }

    @Test public void commitAcknowledgementRestartsTheDeadlineForRemainingAudio() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(0L);
        assertFalse(timeout.expired(0L, true, 0L));
        timeout.audioProgress(29_000L);
        assertFalse(timeout.expired(30_000L, true, 0L));
        assertFalse(timeout.expired(58_999L, true, 0L));
        assertTrue(timeout.expired(59_000L, true, 0L));
    }

    @Test public void cancelledAudioStillExpiresWhileTheDataChannelIsStalled() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(0L);
        timeout.audioProgress(1_000L);
        assertFalse(timeout.expired(1_000L, true, 16_384L));
        assertFalse(timeout.expired(2_000L, false, 16_384L));
        assertFalse(timeout.expired(30_999L, false, 16_384L));
        assertTrue(timeout.expired(31_000L, false, 16_384L));
    }

    @Test public void decreasingDataChannelBacklogCountsAsProgress() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(0L);
        assertFalse(timeout.expired(0L, false, 16_384L));
        assertFalse(timeout.expired(29_000L, false, 8_192L));
        assertFalse(timeout.expired(58_999L, false, 8_192L));
        assertTrue(timeout.expired(59_000L, false, 8_192L));
    }

    @Test public void growingNonemptyDataChannelDoesNotHideAStalledSend() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(0L);
        assertFalse(timeout.expired(0L, true, 100L));
        assertFalse(timeout.expired(29_000L, true, 200L));
        assertTrue(timeout.expired(30_000L, true, 300L));
    }

    @Test public void firstDataChannelBytesStartAProgressDeadlineDuringLocalBacklog() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(0L);
        assertFalse(timeout.expired(0L, true, 0L));
        assertFalse(timeout.expired(29_000L, true, 100L));
        assertFalse(timeout.expired(58_999L, true, 100L));
        assertTrue(timeout.expired(59_000L, true, 100L));
    }

    @Test public void continuousSuccessfulAppendsKeepSendingAlive() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(0L);
        assertFalse(timeout.expired(0L, true, 100L));
        timeout.audioProgress(29_000L);
        assertFalse(timeout.expired(30_000L, true, 200L));
        timeout.audioProgress(58_000L);
        assertFalse(timeout.expired(59_000L, true, 300L));
        assertFalse(timeout.expired(87_999L, true, 300L));
        assertTrue(timeout.expired(88_000L, true, 300L));
    }

    @Test public void emptyQueuesDisarmUntilNewLocalAudioArrives() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(0L);
        timeout.audioProgress(1_000L);
        assertFalse(timeout.expired(2_000L, false, 0L));
        assertFalse(timeout.expired(600_000L, false, 0L));
        assertFalse(timeout.expired(600_001L, true, 0L));
        assertFalse(timeout.expired(630_000L, true, 0L));
        assertTrue(timeout.expired(630_001L, true, 0L));
    }

    @Test public void controlBytesAfterLongIdleDoNotInheritOldAudioDeadline() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(0L);
        timeout.audioProgress(1_000L);
        assertFalse(timeout.expired(2_000L, false, 0L));
        assertFalse(timeout.expired(600_000L, false, 80L));
        assertFalse(timeout.expired(629_999L, false, 80L));
        assertTrue(timeout.expired(630_000L, false, 80L));
    }

    @Test public void drainedChannelCanStartAnotherDeadlineWhileAudioAwaitsCommit() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(0L);
        assertFalse(timeout.expired(0L, true, 100L));
        assertFalse(timeout.expired(20_000L, true, 0L));
        assertFalse(timeout.expired(40_000L, true, 100L));
        assertFalse(timeout.expired(69_999L, true, 100L));
        assertTrue(timeout.expired(70_000L, true, 100L));
    }

    @Test public void resetClearsThePreviousSessionBacklog() {
        VoiceSendTimeout timeout = new VoiceSendTimeout();
        timeout.reset(0L);
        assertFalse(timeout.expired(0L, true, 100L));
        assertTrue(timeout.expired(30_000L, true, 100L));
        timeout.reset(600_000L);
        assertFalse(timeout.expired(600_000L, false, 0L));
        assertFalse(timeout.expired(700_000L, true, 0L));
        assertFalse(timeout.expired(729_999L, true, 0L));
        assertTrue(timeout.expired(730_000L, true, 0L));
    }
}
