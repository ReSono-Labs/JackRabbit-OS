package com.resonolabs.feature.voice;

import android.content.Context;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioRecord;
import android.media.AudioTrack;
import android.media.MediaRecorder;
import android.os.Handler;
import android.os.Looper;
import android.util.Base64;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicBoolean;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

/**
 * WebSocket voice transport for Gemini Live (slice 3 "WebRTC -> WebSocket" connector).
 *
 * The Python runtime returns a session descriptor (transport=websocket, url, setup,
 * audio formats, sessionId). This peer owns the socket, the microphone, and the
 * speaker:
 *
 *   - AudioRecord at 16 kHz PCM mono -> base64 frames in {"realtimeInput": {...}}
 *   - Server frames parsed with the same wire vocabulary as providers/gemini/live.py:
 *     setupComplete, serverContent (audio/text/functionCall/grounding),
 *     turnComplete, interrupted, goAway, error
 *   - Function calls are handed to the listener; results are sent back via
 *     {"toolResponse": {"functionResponses": [...]}}
 *
 * CI-compiled only in this pass; device acceptance wires it into VoicePageView
 * alongside NativeVoicePeer (OpenAI WebRTC remains the default transport).
 */
public final class WebSocketVoicePeer {
    private static final String LOG_TAG = "ReSonoGeminiVoice";
    private static final int INPUT_SAMPLE_RATE = 16000;
    private static final int OUTPUT_SAMPLE_RATE = 24000;
    private static final int READ_CHUNK_BYTES = 640; // 20 ms at 16k/16-bit mono
    private static final int MAX_FRAME_BYTES = 262_144;

    public interface Listener {
        void onLive();
        void onTranscript(String text);
        void onFunctionCall(String callId, String name, JSONObject arguments);
        void onTurnComplete();
        void onInterrupted();
        void onFailure(String reason);
    }

    private final Context context;
    private final Listener listener;
    private final JSONObject descriptor;
    private final String sessionId;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final AtomicBoolean closed = new AtomicBoolean();

    private OkHttpClient client;
    private WebSocket socket;
    private AudioRecord recorder;
    private AudioTrack player;
    private Thread captureThread;
    private AudioManager audioManager;
    private boolean setupSent;

    public WebSocketVoicePeer(Context context, JSONObject descriptor, Listener listener) {
        this.context = context.getApplicationContext();
        this.descriptor = descriptor;
        this.listener = listener;
        this.sessionId = descriptor.optString("sessionId", "");
    }

    public String getSessionId() {
        return sessionId;
    }

    /** Connect to the descriptor URL and send the setup message on open. */
    public void connect() {
        if (closed.get()) {
            fail("already-closed");
            return;
        }
        String url = descriptor.optString("url", "");
        JSONObject setup = descriptor.optJSONObject("setup");
        if (url.isEmpty() || setup == null) {
            fail("descriptor-invalid");
            return;
        }
        client = new OkHttpClient();
        Request request = new Request.Builder().url(url).build();
        socket = client.newWebSocket(request, new WebSocketListener() {
            @Override public void onOpen(WebSocket webSocket, Response response) {
                if (closed.get()) {
                    webSocket.close(1000, "closed");
                    return;
                }
                try {
                    webSocket.send(setup.toString());
                    setupSent = true;
                    Log.i(LOG_TAG, "configured session " + sessionId);
                } catch (RuntimeException error) {
                    fail("setup-send-failed");
                }
            }

            @Override public void onMessage(WebSocket webSocket, String text) {
                handleFrame(text);
            }

            @Override public void onFailure(WebSocket webSocket, Throwable error, Response response) {
                fail(error == null ? "websocket-failed" : "websocket-" + error.getClass().getSimpleName());
            }

            @Override public void onClosed(WebSocket webSocket, int code, String reason) {
                if (!closed.get()) fail("websocket-closed-" + code);
            }
        });
    }

    private void handleFrame(String text) {
        if (closed.get() || text.length() > MAX_FRAME_BYTES) {
            fail("frame-invalid");
            return;
        }
        try {
            JSONObject payload = new JSONObject(text);
            if (payload.has("setupComplete")) {
                startAudio();
                handler.post(listener::onLive);
                return;
            }
            if (payload.has("serverContent")) {
                handleServerContent(payload.getJSONObject("serverContent"));
                return;
            }
            if (payload.has("goAway")) {
                Log.i(LOG_TAG, "goAway received; closing session");
                close();
                return;
            }
            if (payload.has("error")) {
                JSONObject error = payload.optJSONObject("error");
                String message = error == null ? "unknown" : error.optString("message", "unknown");
                fail("gemini-error-" + message);
            }
        } catch (JSONException error) {
            fail("frame-json-invalid");
        }
    }

    private void handleServerContent(JSONObject content) {
        boolean interrupted = content.optBoolean("interrupted");
        boolean turnComplete = content.optBoolean("turnComplete");
        JSONObject modelTurn = content.optJSONObject("modelTurn");
        JSONArray parts = modelTurn == null ? null : modelTurn.optJSONArray("parts");
        if (parts == null || parts.length() == 0) {
            if (interrupted) handler.post(listener::onInterrupted);
            if (turnComplete) handler.post(listener::onTurnComplete);
            return;
        }
        final StringBuilder transcript = new StringBuilder();
        for (int i = 0; i < parts.length(); i++) {
            JSONObject part = parts.optJSONObject(i);
            if (part == null) continue;
            String text = part.optString("text", "");
            if (!text.isEmpty()) transcript.append(text);
            JSONObject inline = part.optJSONObject("inlineData");
            if (inline != null) {
                playAudio(inline.optString("data", ""));
            }
            JSONObject functionCall = part.optJSONObject("functionCall");
            if (functionCall != null) {
                final String callId = functionCall.optString("id", "");
                final String name = functionCall.optString("name", "");
                final JSONObject args = functionCall.optJSONObject("args");
                handler.post(() -> listener.onFunctionCall(
                        callId, name, args == null ? new JSONObject() : args));
            }
        }
        if (transcript.length() > 0) {
            final String text = transcript.toString();
            handler.post(() -> listener.onTranscript(text));
        }
        if (interrupted) {
            flushPlayback();
            handler.post(listener::onInterrupted);
        }
        if (turnComplete) handler.post(listener::onTurnComplete);
    }

    // --- audio -------------------------------------------------------------

    private void startAudio() {
        audioManager = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        if (audioManager != null) {
            audioManager.setMode(AudioManager.MODE_NORMAL);
            audioManager.setSpeakerphoneOn(true);
        }
        try {
            recorder = new AudioRecord(
                    MediaRecorder.AudioSource.VOICE_RECOGNITION,
                    INPUT_SAMPLE_RATE,
                    AudioFormat.CHANNEL_IN_MONO,
                    AudioFormat.ENCODING_PCM_16BIT,
                    READ_CHUNK_BYTES * 8);
            player = new AudioTrack(
                    android.media.AudioManager.STREAM_MUSIC,
                    OUTPUT_SAMPLE_RATE,
                    AudioFormat.CHANNEL_OUT_MONO,
                    AudioFormat.ENCODING_PCM_16BIT,
                    READ_CHUNK_BYTES * 16,
                    AudioTrack.MODE_STREAM);
        } catch (RuntimeException error) {
            fail("audio-init-failed");
            return;
        }
        if (recorder.getState() != AudioRecord.STATE_INITIALIZED
                || player.getState() != AudioTrack.STATE_INITIALIZED) {
            fail("audio-init-failed");
            return;
        }
        player.play();
        recorder.startRecording();
        captureThread = new Thread(this::captureLoop, "gemini-live-capture");
        captureThread.start();
    }

    private void captureLoop() {
        byte[] buffer = new byte[READ_CHUNK_BYTES];
        while (!closed.get() && socket != null) {
            int read = recorder.read(buffer, 0, buffer.length);
            if (read <= 0) continue;
            JSONObject frame = new JSONObject();
            JSONObject input = new JSONObject();
            JSONObject chunk = new JSONObject();
            try {
                chunk.put("mimeType", "audio/pcm;rate=16000");
                chunk.put("data", Base64.encodeToString(buffer, 0, read, Base64.NO_WRAP));
                input.put("audio", chunk); // Blob shape; mediaChunks is deprecated
                frame.put("realtimeInput", input);
            } catch (JSONException error) {
                continue;
            }
            try {
                socket.send(frame.toString());
            } catch (RuntimeException error) {
                fail("audio-send-failed");
                return;
            }
        }
    }

    private void playAudio(String base64Data) {
        if (closed.get() || player == null || base64Data.isEmpty()) return;
        byte[] pcm;
        try {
            pcm = Base64.decode(base64Data, Base64.DEFAULT);
        } catch (IllegalArgumentException error) {
            return;
        }
        final byte[] samples = pcm;
        handler.post(() -> {
            if (player != null && !closed.get()) player.write(samples, 0, samples.length);
        });
    }

    private void flushPlayback() {
        handler.post(() -> {
            if (player != null && player.getPlayState() == AudioTrack.PLAYSTATE_PLAYING) {
                player.pause();
                player.flush();
                player.play();
            }
        });
    }

    // --- tool responses ----------------------------------------------------

    /** Send a tool result for a functionCall previously delivered via the listener. */
    public boolean sendToolResult(String callId, String name, JSONObject response) {
        if (closed.get() || socket == null || !setupSent) return false;
        try {
            JSONObject responseObject = new JSONObject()
                    .put("toolResponse", new JSONObject()
                            .put("functionResponses", new JSONArray()
                                    .put(new JSONObject()
                                            .put("id", callId)
                                            .put("name", name)
                                            .put("response", response == null ? new JSONObject() : response))));
            socket.send(responseObject.toString());
            return true;
        } catch (JSONException | RuntimeException error) {
            fail("tool-send-failed");
            return false;
        }
    }

    // --- lifecycle ---------------------------------------------------------

    public void close() {
        if (closed.getAndSet(true)) return;
        try {
            if (socket != null) socket.close(1000, "closed");
        } catch (RuntimeException ignored) {
        }
        if (recorder != null) {
            try {
                recorder.stop();
            } catch (IllegalStateException ignored) {
            }
            recorder.release();
            recorder = null;
        }
        if (player != null) {
            player.stop();
            player.release();
            player = null;
        }
        if (client != null) client.dispatcher().executorService().shutdown();
        if (audioManager != null) audioManager.setMode(AudioManager.MODE_NORMAL);
        socket = null;
        client = null;
    }

    private void fail(String reason) {
        if (closed.get()) return;
        Log.w(LOG_TAG, "peer failure: " + reason);
        handler.post(() -> listener.onFailure(reason));
    }
}
