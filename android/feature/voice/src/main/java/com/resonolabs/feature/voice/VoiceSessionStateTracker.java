package com.resonolabs.feature.voice;

/** Canonical native projection of the Browser Voice Realtime state rules. */
final class VoiceSessionStateTracker {
    enum State { IDLE, CONNECTING, LIVE, RESPONDING, ERROR }

    private State state = State.IDLE;
    private int pendingToolCalls;
    private boolean toolFollowUpPending;

    State state() {
        return state;
    }

    void connecting() {
        pendingToolCalls = 0;
        toolFollowUpPending = false;
        state = State.CONNECTING;
    }

    void live() {
        state = State.LIVE;
    }

    void idle() {
        pendingToolCalls = 0;
        toolFollowUpPending = false;
        state = State.IDLE;
    }

    void error() {
        pendingToolCalls = 0;
        toolFollowUpPending = false;
        state = State.ERROR;
    }

    void onRealtimeEvent(String type) {
        switch (type) {
            case "input_audio_buffer.speech_started" -> state = State.LIVE;
            case "input_audio_buffer.speech_stopped", "response.audio.delta" ->
                    state = State.RESPONDING;
            case "response.created" -> {
                toolFollowUpPending = false;
                state = State.RESPONDING;
            }
            case "response.function_call_arguments.done" -> {
                pendingToolCalls += 1;
                state = State.RESPONDING;
            }
            case "response.done" -> state = pendingToolCalls == 0 && !toolFollowUpPending
                    ? State.LIVE : State.RESPONDING;
            default -> { }
        }
    }

    void toolOutputSent() {
        pendingToolCalls = Math.max(0, pendingToolCalls - 1);
        toolFollowUpPending = true;
        state = State.RESPONDING;
    }
}
