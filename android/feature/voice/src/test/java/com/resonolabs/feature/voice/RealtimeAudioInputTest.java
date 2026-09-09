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
        assertSilenceThenEnd(input);
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
        assertSilenceThenEnd(input);
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
        assertSilenceThenEnd(input);
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
        assertSilenceThenEnd(input);
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
        assertSilenceThenEnd(input);
        assertNull(input.poll());
    }

    @Test public void nextPressCannotOvertakePreviousVadEndingSilence() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        input.offer(AUDIO, 110, 0);
        input.release(true, 300);
        input.beginCandidate(400);
        input.offer(new byte[] {5, 6}, 410, 0);
        input.release(true, 600);
        assertArrayEquals(AUDIO, input.poll().pcm());
        assertSilenceThenEnd(input);
        assertArrayEquals(new byte[] {5, 6}, input.poll().pcm());
        assertSilenceThenEnd(input);
        assertNull(input.poll());
        assertEquals(0, input.queuedBytes());
    }

    @Test public void fullThirtySecondsCanReleaseWithoutAllocatingTheWholeSilenceTail() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        assertEquals(RealtimeAudioInput.OfferResult.ACCEPTED,
                input.offer(new byte[1_440_000], 110, 0));
        input.release(true, 300);
        assertFalse(input.failed());
        assertEquals(1_440_000, input.queuedBytes());
        assertEquals(1_440_000, input.poll().pcm().length);
        assertSilenceThenEnd(input);
        assertFalse(input.hasPending());
        assertEquals(0, input.queuedBytes());
    }

    @Test public void queuedEndReservesWorkspaceBeforeAcceptingAnotherFullCapture() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        input.offer(AUDIO, 110, 0);
        input.release(true, 300);
        input.beginCandidate(400);
        assertEquals(RealtimeAudioInput.OfferResult.OVERFLOW,
                input.offer(new byte[1_440_000 - AUDIO.length], 410, 0));
        assertEquals(AUDIO.length, input.queuedBytes());
    }

    @Test public void reservedWorkspaceDrainsEarlierTailWithoutConsumingTheNextCapture() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        input.offer(AUDIO, 110, 0);
        input.release(true, 300);
        byte[] nextCapture = new byte[1_440_000 - 16_384 - AUDIO.length];
        input.beginCandidate(400);
        assertEquals(RealtimeAudioInput.OfferResult.ACCEPTED, input.offer(nextCapture, 410, 0));
        input.confirmCandidate();

        RealtimeAudioInput.Entry first = input.poll();
        assertFalse(first.isSyntheticSilence());
        assertArrayEquals(AUDIO, first.pcm());
        assertEquals(nextCapture.length, input.queuedBytes());
        assertSilenceThenEnd(input);
        assertEquals(nextCapture.length, input.queuedBytes());
        RealtimeAudioInput.Entry second = input.poll();
        assertFalse(second.isSyntheticSilence());
        assertArrayEquals(nextCapture, second.pcm());
        assertEquals(0, input.queuedBytes());
        assertNull(input.peek());
    }

    @Test public void resetDiscardsPeekedTailAndRestoresTheFullCaptureCapacity() {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        input.offer(AUDIO, 110, 0);
        input.release(true, 300);
        assertFalse(input.poll().isSyntheticSilence());
        RealtimeAudioInput.Entry oldTail = input.peek();
        assertTrue(oldTail.isSyntheticSilence());

        input.reset();
        assertNull(input.peek());
        input.beginCandidate(400);
        assertEquals(RealtimeAudioInput.OfferResult.ACCEPTED,
                input.offer(new byte[1_440_000], 410, 0));
        input.confirmCandidate();
        RealtimeAudioInput.Entry next = input.peek();
        assertNotSame(oldTail, next);
        assertFalse(next.isSyntheticSilence());
        assertEquals(1_440_000, next.pcm().length);
        assertSame(next, input.poll());
        assertNull(input.peek());
        assertEquals(0, input.queuedBytes());
    }

    private static void assertSilenceThenEnd(RealtimeAudioInput input) {
        int silenceBytes = 0;
        int queuedBytes = input.queuedBytes();
        while (true) {
            RealtimeAudioInput.Entry entry = input.peek();
            assertNotNull(entry);
            assertSame(entry, input.peek());
            assertSame(entry, input.poll());
            assertEquals(queuedBytes, input.queuedBytes());
            if (entry.isEnd()) break;
            assertTrue(entry.isSyntheticSilence());
            byte[] pcm = entry.pcm();
            assertTrue("Bound each encoded data-channel message", pcm.length <= 12_000);
            assertArrayEquals(new byte[pcm.length], pcm);
            silenceBytes += pcm.length;
        }
        // 24 kHz mono PCM16 must cover the configured 1200 ms VAD silence window.
        assertTrue("End must close server VAD before the next turn", silenceBytes >= 57_600);
        assertTrue("Ending silence must remain bounded", silenceBytes <= 96_000);
    }
}
