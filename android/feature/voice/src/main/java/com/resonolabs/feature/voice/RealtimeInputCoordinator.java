package com.resonolabs.feature.voice;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.json.JSONObject;

/** Correlates ordered PCM appends, VAD items and explicit input boundaries. */
final class RealtimeInputCoordinator {
    // The native input contract is 24 kHz mono PCM16.
    private static final long PCM_BYTES_PER_MILLISECOND = 48;

    interface Sender { boolean send(JSONObject event); }

    interface Listener {
        void onCommitted(String itemId, boolean voiced);
        void onSpeechStarted();
        void onSpeechStopped();
        void onFailure(String reason);
    }

    private static final class Input {
        boolean ended;
        boolean cancelled;
    }

    private static final class Speech {
        final Input input;
        long endByte = -1;
        Speech(Input input) { this.input = input; }
    }

    private static final class Commit {
        final String eventId;
        final Input input;
        final long endByte;
        boolean hadSpeech;
        boolean observedAutoCommit;
        Commit(String eventId, Input input, long endByte) {
            this.eventId = eventId;
            this.input = input;
            this.endByte = endByte;
        }
    }

    private final Sender sender;
    private final Listener listener;
    private final Map<String, Speech> speechItems = new HashMap<>();
    private final Set<String> committedItemIds = new HashSet<>();
    private final Set<String> silentItemIds = new HashSet<>();
    private final List<Commit> pendingCommits = new ArrayList<>();
    private Input input;
    private String speakingItemId;
    private long appendedBytes;
    private long committedBytes;
    private long requestedCommitBytes;
    private long eventSequence;
    private boolean closed = true;

    RealtimeInputCoordinator(Sender sender, Listener listener) {
        this.sender = sender;
        this.listener = listener;
    }

    void reset() {
        close();
        input = new Input();
        closed = false;
    }

    void close() {
        closed = true;
        speechItems.clear();
        committedItemIds.clear();
        silentItemIds.clear();
        pendingCommits.clear();
        speakingItemId = null;
        appendedBytes = committedBytes = requestedCommitBytes = 0;
    }

    /** A confirmed capture may reopen input after cancellation; candidate taps may not. */
    void beginInput() {
        if (!closed && (input.ended || input.cancelled)) input = new Input();
    }

    /** Called only after a PCM append was accepted by the same ordered data channel. */
    void onAudioAppended(int byteCount) {
        if (!closed && byteCount > 0) appendedBytes += byteCount;
    }

    /** Called at the audio queue's end marker, after its final append has been sent. */
    void endInput() {
        if (closed) return;
        input.ended = true;
        if (appendedBytes <= Math.max(committedBytes, requestedCommitBytes)) return;
        Commit commit = new Commit("resono-input-commit-" + (++eventSequence), input, appendedBytes);
        for (Speech speech : speechItems.values()) {
            if (speech.input == input) commit.hadSpeech = true;
        }
        try {
            JSONObject event = new JSONObject().put("type", "input_audio_buffer.commit")
                    .put("event_id", commit.eventId);
            pendingCommits.add(commit);
            requestedCommitBytes = appendedBytes;
            // VAD callbacks can still be in transit. Audio presence is enough to commit;
            // only a preceding server speech_started can make its item answerable.
            if (!sender.send(event)) {
                pendingCommits.remove(commit);
                listener.onFailure("Unable to commit voice input");
            }
        } catch (Exception failure) {
            pendingCommits.remove(commit);
            listener.onFailure("Unable to commit voice input");
        }
    }

    void cancelPendingTurn() {
        if (closed) return;
        input.cancelled = true;
        for (Commit commit : pendingCommits) commit.input.cancelled = true;
        for (Speech speech : speechItems.values()) speech.input.cancelled = true;
        speakingItemId = null;
    }

    boolean isSpeaking() {
        Speech speech = speechItems.get(speakingItemId);
        return !closed && speech != null && !speech.input.cancelled;
    }

    boolean hasPendingCommit() {
        return !closed && !pendingCommits.isEmpty();
    }

    boolean isSilentItem(String itemId) {
        return silentItemIds.contains(itemId);
    }

    /** Returns true only for owned events or an exactly correlated expected error. */
    boolean onEvent(JSONObject event) {
        if (closed || event == null) return false;
        String type = event.optString("type");
        if ("error".equals(type)) return onError(event.optJSONObject("error"));
        String itemId = event.optString("item_id");
        if ("input_audio_buffer.speech_started".equals(type)) {
            onSpeechStarted(itemId);
        } else if ("input_audio_buffer.speech_stopped".equals(type)) {
            onSpeechStopped(itemId, event.optLong("audio_end_ms", -1));
        } else if ("input_audio_buffer.committed".equals(type)) {
            onCommitted(itemId);
        } else {
            return false;
        }
        return true;
    }

    private void onSpeechStarted(String itemId) {
        if (itemId.isEmpty() || committedItemIds.contains(itemId) || speechItems.containsKey(itemId)) return;
        Input owner = input;
        if (!pendingCommits.isEmpty()) {
            // An earlier automatic segment does not acknowledge the explicit commit.
            // Ordered server events finish that command before later input is processed.
            Commit commit = pendingCommits.get(0);
            owner = commit.input;
            commit.hadSpeech = true;
        }
        speechItems.put(itemId, new Speech(owner));
        speakingItemId = itemId;
        if (!owner.cancelled) listener.onSpeechStarted();
    }

    private void onSpeechStopped(String itemId, long audioEndMillis) {
        Speech speech = speechItems.get(itemId);
        if (speech == null || speech.endByte >= 0) return;
        speech.endByte = audioEndMillis < 0 ? appendedBytes
                : Math.min(appendedBytes, audioEndMillis * PCM_BYTES_PER_MILLISECOND);
        if (itemId.equals(speakingItemId)) speakingItemId = null;
        if (!speech.input.cancelled) listener.onSpeechStopped();
    }

    private void onCommitted(String itemId) {
        if (itemId.isEmpty() || !committedItemIds.add(itemId)) return;
        Speech speech = speechItems.remove(itemId);
        String vadItemId = itemId;
        if (speech == null && !pendingCommits.isEmpty()) {
            Commit pending = pendingCommits.get(0);
            // Explicit commit during active VAD may use a different item id.
            for (Map.Entry<String, Speech> entry : speechItems.entrySet()) {
                if (entry.getValue().input == pending.input && entry.getValue().endByte < 0) {
                    vadItemId = entry.getKey();
                    speech = entry.getValue();
                    break;
                }
            }
            if (speech != null) {
                speechItems.remove(vadItemId);
                committedItemIds.add(vadItemId);
            }
        }
        Input owner;
        if (speech != null) {
            owner = speech.input;
            Commit matching = null;
            for (Commit commit : pendingCommits) {
                if (commit.input == owner && (speech.endByte < 0 || !commit.observedAutoCommit)) {
                    matching = commit;
                    if (speech.endByte >= 0) commit.observedAutoCommit = true;
                    break;
                }
            }
            long boundary = speech.endByte >= 0 ? speech.endByte
                    : matching == null ? appendedBytes : matching.endByte;
            committedBytes = Math.max(committedBytes, boundary);
            if (matching != null && speech.endByte < 0) pendingCommits.remove(matching);
            if (vadItemId.equals(speakingItemId)) {
                speakingItemId = null;
                if (!owner.cancelled) listener.onSpeechStopped();
            }
        } else {
            silentItemIds.add(itemId);
            Commit commit = pendingCommits.isEmpty() ? null : pendingCommits.remove(0);
            owner = commit == null ? input : commit.input;
            if (commit != null) committedBytes = Math.max(committedBytes, commit.endByte);
            if (!deleteSilentItem(itemId)) return;
        }
        // Cancelled voiced input remains in context, but must not resurrect an answer.
        if (!closed && !owner.cancelled) listener.onCommitted(itemId, speech != null);
    }

    private boolean onError(JSONObject error) {
        if (error == null || !"input_audio_buffer_commit_empty".equals(error.optString("code"))) return false;
        String eventId = error.optString("event_id");
        for (int index = 0; index < pendingCommits.size(); index++) {
            Commit commit = pendingCommits.get(index);
            if (!commit.eventId.equals(eventId)) continue;
            if (commit.hadSpeech && !commit.observedAutoCommit) return false;
            for (Speech speech : speechItems.values()) {
                if (speech.input == commit.input) return false;
            }
            pendingCommits.remove(index);
            committedBytes = Math.max(committedBytes, commit.endByte);
            return true;
        }
        return false;
    }

    private boolean deleteSilentItem(String itemId) {
        try {
            if (sender.send(new JSONObject().put("type", "conversation.item.delete").put("item_id", itemId))) return true;
        } catch (Exception ignored) {
            // Report the same transport failure as an unsuccessful send.
        }
        listener.onFailure("Unable to discard silent voice input");
        return false;
    }
}
