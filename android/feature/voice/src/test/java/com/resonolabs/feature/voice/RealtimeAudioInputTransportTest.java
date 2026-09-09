package com.resonolabs.feature.voice;

import static org.junit.Assert.*;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import org.json.JSONObject;
import org.junit.Test;

/** Exercises the audio owner's send admission while the transport cannot drain. */
public final class RealtimeAudioInputTransportTest {
    @Test public void releasedAudioAndWholeVadTailFitBeforeTheTransportDrains() throws Exception {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        assertEquals(RealtimeAudioInput.OfferResult.ACCEPTED,
                input.offer(new byte[9_600], 110, 0));
        input.release(true, 300);
        StalledTransport transport = new StalledTransport();

        while (!input.peek().isEnd()) {
            assertTrue("The released tail must not wait for a drain after each block",
                    transport.appendHead(input));
        }

        assertEquals(81_600, transport.sentPcmBytes);
        assertEquals(72_000, transport.sentSilenceBytes);
        assertTrue(transport.bufferedBytes <= 131_072);
        assertTrue(input.poll().isEnd());
        assertNull(input.peek());
        assertEquals(0, input.queuedBytes());
    }

    @Test public void nearFullNextCaptureLimitsEarlierTailButAllowsItToFinish() throws Exception {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.beginCandidate(100);
        input.offer(new byte[480], 110, 0);
        input.release(true, 300);
        int nextCaptureBytes = 1_440_000 - 16_384 - 480;
        input.beginCandidate(400);
        assertEquals(RealtimeAudioInput.OfferResult.ACCEPTED,
                input.offer(new byte[nextCaptureBytes], 410, 0));
        input.confirmCandidate();
        StalledTransport transport = new StalledTransport();
        assertFalse(input.peek().isSyntheticSilence());
        assertTrue(transport.appendHead(input));

        for (int block = 0; block < 6; block++) {
            assertTrue("Reserved workspace must let the earlier END advance",
                    transport.appendHead(input));
            assertEquals(nextCaptureBytes, input.queuedBytes());
            assertTrue("Generated audio must share the total queue budget",
                    input.queuedBytes() + transport.bufferedBytes <= 1_440_000);
            if (block < 5) {
                RealtimeAudioInput.Entry blocked = input.peek();
                assertFalse("A larger transport window must not consume capture capacity",
                        transport.appendHead(input));
                assertSame(blocked, input.peek());
                assertEquals(nextCaptureBytes, input.queuedBytes());
                transport.bufferedBytes = 0; // Only the external transport releases bytes.
            }
        }

        assertEquals(72_000, transport.sentSilenceBytes);
        assertTrue(input.poll().isEnd());
        assertFalse(input.peek().isSyntheticSilence());
        assertEquals(nextCaptureBytes, input.peek().pcm().length);
        assertEquals(nextCaptureBytes, input.queuedBytes());
    }

    @Test public void realAudioUsesAvailableWindowWithoutCrossingItsByteLimit() throws Exception {
        RealtimeAudioInput input = new RealtimeAudioInput();
        input.setContinuous(true, 100);
        input.offer(new byte[480], 110, 0);
        RealtimeAudioInput.Entry frame = input.peek();
        int encodedBytes = encodedBytes(frame.pcm());

        assertTrue("Realtime input needs room beyond the old single-message window",
                input.canAppend(frame, encodedBytes, 65_536));
        assertTrue(input.canAppend(frame, encodedBytes, 131_072 - encodedBytes));
        assertFalse(input.canAppend(frame, encodedBytes, 131_073 - encodedBytes));
        assertFalse(input.canAppend(frame, encodedBytes, Long.MAX_VALUE));
        assertSame(frame, input.peek());
        assertEquals(480, input.queuedBytes());
    }

    private static int encodedBytes(byte[] pcm) throws Exception {
        return new JSONObject().put("type", "input_audio_buffer.append")
                .put("audio", Base64.getEncoder().encodeToString(pcm))
                .toString().getBytes(StandardCharsets.UTF_8).length;
    }

    private static final class StalledTransport {
        long bufferedBytes;
        int sentPcmBytes;
        int sentSilenceBytes;

        boolean appendHead(RealtimeAudioInput input) throws Exception {
            RealtimeAudioInput.Entry entry = input.peek();
            assertNotNull(entry);
            assertFalse(entry.isEnd());
            byte[] pcm = entry.pcm();
            int encodedBytes = encodedBytes(pcm);
            if (!input.canAppend(entry, encodedBytes, bufferedBytes)) return false;
            bufferedBytes += encodedBytes;
            sentPcmBytes += pcm.length;
            if (entry.isSyntheticSilence()) sentSilenceBytes += pcm.length;
            assertSame(entry, input.poll());
            return true;
        }
    }
}
