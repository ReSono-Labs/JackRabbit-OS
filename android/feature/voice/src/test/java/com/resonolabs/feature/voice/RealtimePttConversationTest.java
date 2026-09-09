package com.resonolabs.feature.voice;

import static org.junit.Assert.*;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.List;
import org.json.JSONObject;
import org.junit.Test;

/** Replays the R1 observation that manual commit leaves the provider's VAD active. */
public final class RealtimePttConversationTest {
    @Test public void coldFirstTurnAndTwoWarmTurnsEachReceiveOneAnswer() throws Exception {
        Fixture f = new Fixture(false);
        f.speakAndRelease(true);
        f.speakAndRelease(false);
        f.speakAndRelease(false);
        assertEquals(List.of(1, 2, 3), f.responsesAfterRelease);
        assertFalse(f.input.hasPendingCommit());
        assertFalse(f.input.isSpeaking());
    }

    @Test public void delayedVadAcknowledgementsStillAnswerEveryReleasedTurnOnce() throws Exception {
        Fixture f = new Fixture(true);
        f.speakAndRelease(true);
        f.speakAndRelease(false);
        f.speakAndRelease(false);
        assertEquals(List.of(1, 2, 3), f.responsesAfterRelease);
        assertFalse(f.input.hasPendingCommit());
    }

    @Test public void shortTapDoesNotUploadAudioOrCreateAnAnswer() throws Exception {
        Fixture f = new Fixture(false);
        f.beginCapture();
        f.audio.release(false, f.now + 50_000_000L);
        f.response.setHeld(false);
        f.drain();
        f.pump(true);
        assertEquals(0, f.appendCommands);
        assertEquals(0, f.responseCommands);
        assertFalse(f.input.hasPendingCommit());
    }

    @Test public void cancelledCaptureDoesNotAnswerOrSuppressTheNextHeldTurn() throws Exception {
        Fixture f = new Fixture(true);
        f.beginCapture();
        f.audio.confirmCandidate();
        f.response.setHeld(false);
        f.drain();
        f.input.cancelPendingTurn();
        f.response.cancelCurrentRound();
        f.audio.release(false, f.now + 1_000_000_000L);
        f.drain();
        f.pump(true);
        assertEquals(0, f.responseCommands);
        f.speakAndRelease(false);
        assertEquals(List.of(1), f.responsesAfterRelease);
        assertFalse(f.input.hasPendingCommit());
    }

    private static final class Fixture implements RealtimeInputCoordinator.Listener {
        final RealtimeAudioInput audio = new RealtimeAudioInput();
        final RealtimeInputCoordinator input = new RealtimeInputCoordinator(this::send, this);
        final RealtimeResponseCoordinator response = new RealtimeResponseCoordinator(
                this::send, new RealtimeResponseCoordinator.Scheduler() {
                    @Override public void schedule(Runnable action, long delayMillis) { }
                    @Override public void cancel(Runnable action) { }
                }, () -> fail("Response transport failed"));
        final ArrayDeque<JSONObject> commands = new ArrayDeque<>();
        final ArrayDeque<JSONObject> events = new ArrayDeque<>();
        final List<Integer> responsesAfterRelease = new ArrayList<>();
        final VadServer server = new VadServer(events);
        final boolean delayAcknowledgements;
        long now;
        boolean segmentStarted;
        int appendCommands;
        int responseCommands;

        Fixture(boolean delayAcknowledgements) {
            this.delayAcknowledgements = delayAcknowledgements;
            input.reset();
            response.reset();
        }

        void beginCapture() {
            now += 2_000_000_000L;
            audio.beginCandidate(now);
            response.setHeld(true);
            byte[] voicedPcm = new byte[48_000]; // One second, 24 kHz mono PCM16.
            Arrays.fill(voicedPcm, (byte) 1);
            assertEquals(RealtimeAudioInput.OfferResult.ACCEPTED,
                    audio.offer(voicedPcm, now + 10_000_000L, 0));
        }

        void speakAndRelease(boolean beforeConnectionReady) throws Exception {
            beginCapture();
            if (!beforeConnectionReady) {
                audio.confirmCandidate();
                response.setHeld(false);
                drain();
            }
            audio.release(true, now + 1_000_000_000L);
            response.setHeld(false);
            drain();
            pump(true);
            responsesAfterRelease.add(responseCommands);
        }

        /** Matches the controller's ordered append, byte-accounting and END boundary. */
        void drain() throws Exception {
            for (RealtimeAudioInput.Entry entry; (entry = audio.peek()) != null; ) {
                if (entry.isEnd()) {
                    audio.poll();
                    input.endInput();
                    segmentStarted = false;
                } else {
                    if (!segmentStarted) {
                        input.beginInput();
                        segmentStarted = true;
                    }
                    byte[] pcm = entry.pcm();
                    send(new JSONObject().put("type", "input_audio_buffer.append")
                            .put("audio", Base64.getEncoder().encodeToString(pcm)));
                    audio.poll();
                    input.onAudioAppended(pcm.length);
                }
                pump(!delayAcknowledgements);
            }
        }

        boolean send(JSONObject event) {
            commands.addLast(event);
            if ("input_audio_buffer.append".equals(event.optString("type"))) appendCommands++;
            if ("response.create".equals(event.optString("type"))) responseCommands++;
            return true;
        }

        void pump(boolean deliverEvents) throws Exception {
            while (!commands.isEmpty() || (deliverEvents && !events.isEmpty())) {
                if (!commands.isEmpty()) {
                    JSONObject command = commands.removeFirst();
                    if ("response.create".equals(command.optString("type"))) {
                        String id = "response-" + responseCommands;
                        response.onResponseCreated(id);
                        response.onResponseDone(id);
                    } else {
                        server.accept(command);
                    }
                } else {
                    JSONObject event = events.removeFirst();
                    assertTrue("Unhandled provider event: " + event, input.onEvent(event));
                }
            }
        }

        @Override public void onCommitted(String itemId, boolean voiced) {
            if (voiced) response.requestForInput(itemId);
        }
        @Override public void onSpeechStarted() { }
        @Override public void onSpeechStopped() { }
        @Override public void onFailure(String reason) { fail(reason); }
    }

    /**
     * Only models the observed external boundary: PCM drives VAD, commit clears
     * buffered PCM but not active VAD, and 1200 ms of zeros ends active speech.
     * It deliberately does not invent speech_started on each client commit.
     */
    private static final class VadServer {
        final ArrayDeque<JSONObject> events;
        long receivedBytes;
        long bufferedBytes;
        long silenceBytes;
        int sequence;
        String speakingItem;

        VadServer(ArrayDeque<JSONObject> events) { this.events = events; }

        void accept(JSONObject command) throws Exception {
            switch (command.getString("type")) {
                case "input_audio_buffer.append" -> {
                    byte[] pcm = Base64.getDecoder().decode(command.getString("audio"));
                    for (int offset = 0; offset < pcm.length; offset += 2) {
                        receivedBytes += 2;
                        bufferedBytes += 2;
                        if (pcm[offset] != 0 || pcm[offset + 1] != 0) {
                            silenceBytes = 0;
                            if (speakingItem == null) {
                                speakingItem = "vad-" + (++sequence);
                                events.addLast(event("input_audio_buffer.speech_started", speakingItem)
                                        .put("audio_start_ms", receivedBytes / 48));
                            }
                        } else if (speakingItem != null && (silenceBytes += 2) >= 57_600) {
                            events.addLast(event("input_audio_buffer.speech_stopped", speakingItem)
                                    .put("audio_end_ms", receivedBytes / 48));
                            events.addLast(event("input_audio_buffer.committed", speakingItem));
                            speakingItem = null;
                            silenceBytes = 0;
                            bufferedBytes = 0;
                        }
                    }
                }
                case "input_audio_buffer.commit" -> {
                    if (bufferedBytes < 4_800) {
                        events.addLast(new JSONObject().put("type", "error").put("error",
                                new JSONObject().put("type", "invalid_request_error")
                                        .put("code", "input_audio_buffer_commit_empty")
                                        .put("event_id", command.getString("event_id"))));
                    } else {
                        events.addLast(event("input_audio_buffer.committed", "manual-" + (++sequence)));
                        bufferedBytes = 0;
                    }
                }
                case "conversation.item.delete" -> { }
                default -> fail("Unexpected client command: " + command.getString("type"));
            }
        }

        private static JSONObject event(String type, String itemId) throws Exception {
            return new JSONObject().put("type", type).put("item_id", itemId);
        }
    }
}
