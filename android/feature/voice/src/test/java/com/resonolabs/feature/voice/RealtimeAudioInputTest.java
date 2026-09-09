package com.resonolabs.feature.voice;

import static org.junit.Assert.*;

import org.junit.Test;

public final class RealtimeAudioInputTest {
    private static final byte[] AUDIO = {1, 2, 3, 4};

    @Test public void coldConnectionReleaseKeepsAudioUntilDrainedExactlyOnce() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        assertEquals(RealtimeAudioInput.OfferResult.ACCEPTED, input.offer(AUDIO, 110, 0));
        assertNull(input.peek());
        input.release(true, 300);
        assertArrayEquals(AUDIO, input.poll().pcm());
        assertTrue(input.poll().isEnd());
        assertNull(input.poll());
        input.release(true, 301);
        assertNull(input.poll());
    }

    @Test public void shortCandidateDiscardPreservesOlderContinuousAudioAndEnd() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.setContinuous(true, 10);
        input.offer(AUDIO, 20, 0);
        input.beginCandidate(100);
        input.offer(new byte[] {5, 6}, 90, 0); // Earlier capture delivered after DOWN.
        input.offer(new byte[] {7, 8}, 110, 0);
        input.release(false, 150);
        assertArrayEquals(AUDIO, input.poll().pcm());
        assertArrayEquals(new byte[] {5, 6}, input.poll().pcm());
        assertTrue(input.poll().isEnd());
        assertNull(input.poll());
        assertEquals(0, input.queuedBytes());
    }

    @Test public void shortCandidateAfterDrainingContinuousStillClosesEarlierInput() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.setContinuous(true, 10);
        input.offer(AUDIO, 20, 0);
        input.poll();
        input.beginCandidate(100);
        input.offer(AUDIO, 110, 0);
        input.release(false, 150);
        assertTrue(input.poll().isEnd());
        assertNull(input.poll());
    }

    @Test public void confirmedCandidateStreamsInCaptureOrderBeforeEndMarker() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        input.offer(AUDIO, 110, 0);
        input.confirmCandidate();
        input.offer(new byte[] {5, 6}, 310, 0);
        input.release(true, 350);
        assertEquals(110, input.poll().captureTimeNanos());
        assertEquals(310, input.poll().captureTimeNanos());
        assertTrue(input.poll().isEnd());
        assertNull(input.poll());
    }

    @Test public void rejectsFramesAfterReleaseAndBeforeNextPress() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        assertEquals(RealtimeAudioInput.OfferResult.ACCEPTED, input.offer(AUDIO, 110, 0));
        input.release(false, 150);
        assertEquals(RealtimeAudioInput.OfferResult.IGNORED, input.offer(AUDIO, 160, 0));
        input.beginCandidate(200);
        assertEquals(RealtimeAudioInput.OfferResult.IGNORED, input.offer(AUDIO, 160, 0));
        input.release(true, 300);
        assertNull(input.poll());
    }

    @Test public void exactThirtySecondCapacityIsAllowedAndOverflowFailsClosed() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        assertEquals(RealtimeAudioInput.OfferResult.ACCEPTED,
                input.offer(new byte[RealtimeAudioInput.MAX_BUFFERED_BYTES], 110, 0));
        assertEquals(RealtimeAudioInput.OfferResult.OVERFLOW, input.offer(AUDIO, 120, 0));
        assertTrue(input.failed());
        assertEquals(RealtimeAudioInput.MAX_BUFFERED_BYTES, input.queuedBytes());
        assertEquals(RealtimeAudioInput.OfferResult.IGNORED, input.offer(AUDIO, 130, 0));
        assertNull(input.peek());
        input.reset();
        assertEquals(0, input.queuedBytes());
        assertFalse(input.failed());
    }

    @Test public void transportBacklogCountsTowardCapacityWithoutDroppingOldFrames() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.setContinuous(true, 100);
        input.offer(AUDIO, 110, 0);
        assertEquals(RealtimeAudioInput.OfferResult.OVERFLOW,
                input.offer(AUDIO, 120, RealtimeAudioInput.MAX_BUFFERED_BYTES - AUDIO.length));
        assertEquals(AUDIO.length, input.queuedBytes());
        assertNull(input.peek()); // Failed partial turns must never keep draining.
    }

    @Test public void transportBacklogCannotOverflowArithmetic() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        assertEquals(RealtimeAudioInput.OfferResult.OVERFLOW,
                input.offer(AUDIO, 110, Long.MAX_VALUE));
    }

    @Test public void entriesDefensivelyCopyPcmAndPeekDoesNotConsume() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        byte[] audio = AUDIO.clone();
        input.setContinuous(true, 100);
        input.offer(audio, 110, 0);
        audio[0] = 9;
        input.peek().pcm()[0] = 8;
        assertArrayEquals(AUDIO, input.peek().pcm());
        assertTrue(input.hasPending());
        assertSame(input.peek(), input.poll());
        assertFalse(input.hasPending());
    }

    @Test public void turningContinuousOffClosesInputAndKeepsEarlierFrames() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.setContinuous(true, 100);
        input.offer(AUDIO, 110, 0);
        input.setContinuous(false, 120);
        assertEquals(RealtimeAudioInput.OfferResult.IGNORED, input.offer(AUDIO, 130, 0));
        assertArrayEquals(AUDIO, input.poll().pcm());
        assertTrue(input.poll().isEnd());
        assertNull(input.poll());
    }
}
