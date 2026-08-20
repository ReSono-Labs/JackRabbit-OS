package com.resonolabs.runtime.host;

import android.content.Context;
import android.util.Base64;
import android.util.Log;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/** Native Voice consumer of the private on-device session boundary. */
public final class RuntimeVoiceClient implements AutoCloseable {
    private static final String MCP_VERSION = "2025-11-25";
    private static final String LOG_TAG = "RuntimeVoiceClient";

    public interface Callback {
        void onAnswer(String sdp, String sessionId, JSONObject connectGreetingEvent);
        void onFailure(String reason);
    }

    public interface ToolCallback {
        void onResult(String output);
        void onFailure(String reason);
    }

    public interface FinalizeCallback {
        void onResult(JSONObject response);
        void onFailure(String reason);
    }

    private final ExecutorService worker = Executors.newSingleThreadExecutor(runnable -> {
        Thread thread = new Thread(runnable, "resono-runtime-voice-client");
        thread.setDaemon(true);
        return thread;
    });
    private final Handler main = new Handler(Looper.getMainLooper());
    private final AtomicBoolean closed = new AtomicBoolean();

    public void createCall(Context context, String offerSdp, Callback callback) {
        Context application = context.getApplicationContext();
        worker.execute(() -> request(application, offerSdp, callback));
    }

    public void callTool(Context context, String voiceSessionId, String toolCallId, String userUtterance, long userUtteranceId, String name, JSONObject arguments, ToolCallback callback) {
        Context application = context.getApplicationContext();
        worker.execute(() -> requestTool(application, voiceSessionId, toolCallId, userUtterance, userUtteranceId, name, arguments, callback));
    }

    private void requestTool(Context context, String voiceSessionId, String toolCallId, String userUtterance, long userUtteranceId, String name, JSONObject arguments, ToolCallback callback) {
        try {
            String token = new RuntimeSecretStore(context).loadLocalApiToken();
            JSONObject initialized = new JSONObject()
                    .put("jsonrpc", "2.0")
                    .put("id", 1)
                    .put("method", "initialize")
                    .put("params", new JSONObject()
                            .put("protocolVersion", MCP_VERSION)
                            .put("capabilities", new JSONObject())
                            .put("clientInfo", new JSONObject()
                                    .put("name", "resono-r1-voice")
                                    .put("version", "0.1.0")));
            McpResponse init = postMcp(token, initialized, null, false);
            if (init.sessionId == null || init.sessionId.isBlank()) {
                deliverToolFailure(callback, "mcp-initialize-failed");
                return;
            }
            postMcp(token, new JSONObject()
                    .put("jsonrpc", "2.0")
                    .put("method", "notifications/initialized"), init.sessionId, true);
            JSONObject request = new JSONObject()
                    .put("jsonrpc", "2.0")
                    .put("id", 2)
                    .put("method", "tools/call")
                    .put("params", new JSONObject()
                            .put("name", name)
                            .put("arguments", arguments == null ? new JSONObject() : arguments));
            McpResponse response = postMcp(token, request, init.sessionId, false, voiceSessionId, toolCallId, userUtterance, userUtteranceId);
            JSONObject result = response.payload.optJSONObject("result");
            if (result == null) {
                deliverToolFailure(callback, "mcp-call-failed");
                return;
            }
            if (!closed.get()) main.post(() -> callback.onResult(result.toString()));
        } catch (Exception ignored) {
            deliverToolFailure(callback, "mcp-unavailable");
        }
    }

    private McpResponse postMcp(
            String token,
            JSONObject message,
            String sessionId,
            boolean allowEmpty
    ) throws Exception {
        return postMcp(token, message, sessionId, allowEmpty, null, null, null, 0);
    }

    private McpResponse postMcp(
            String token,
            JSONObject message,
            String sessionId,
            boolean allowEmpty,
            String voiceSessionId,
            String toolCallId,
            String userUtterance,
            long userUtteranceId
    ) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(
                "http://127.0.0.1:8765/v1/mcp").openConnection();
        try {
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(1500);
            // Provider-backed MCP tools such as web_search can legitimately
            // outlive a fast local-domain call. Keep one bounded tool-call
            // window so Voice does not abandon the response while the runtime
            // is still executing it.
            connection.setReadTimeout(65_000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Content-Type", "application/json");
            if (sessionId != null) {
                connection.setRequestProperty("Mcp-Session-Id", sessionId);
                connection.setRequestProperty("MCP-Protocol-Version", MCP_VERSION);
            }
            if (voiceSessionId != null && !voiceSessionId.isBlank()) {
                connection.setRequestProperty("X-ReSono-Voice-Session", voiceSessionId);
            }
            if (toolCallId != null && !toolCallId.isBlank()) {
                connection.setRequestProperty("X-ReSono-Tool-Call", toolCallId);
            }
            if (userUtterance != null && !userUtterance.isBlank()) {
                connection.setRequestProperty(
                        "X-ReSono-Voice-Utterance-B64",
                        Base64.encodeToString(userUtterance.getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP));
            }
            if (userUtteranceId > 0) {
                connection.setRequestProperty("X-ReSono-Voice-Utterance-Id", Long.toString(userUtteranceId));
            }
            connection.getOutputStream().write(message.toString().getBytes(StandardCharsets.UTF_8));
            int status = connection.getResponseCode();
            String returnedSession = connection.getHeaderField("Mcp-Session-Id");
            InputStream source = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
            byte[] bytes = source == null ? new byte[0] : source.readNBytes(65_536);
            if (status >= 400) throw new IllegalStateException("MCP HTTP " + status);
            if (bytes.length == 0 && allowEmpty) return new McpResponse(new JSONObject(), returnedSession);
            JSONObject payload = new JSONObject(new String(bytes, StandardCharsets.UTF_8));
            if (payload.has("error")) throw new IllegalStateException("MCP error");
            return new McpResponse(payload, returnedSession);
        } finally {
            connection.disconnect();
        }
    }

    private void request(Context context, String offerSdp, Callback callback) {
        HttpURLConnection connection = null;
        try {
            String token = new RuntimeSecretStore(context).loadLocalApiToken();
            connection = (HttpURLConnection) new URL(
                    "http://127.0.0.1:8765/v1/voice/calls").openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(1500);
            connection.setReadTimeout(30_000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Content-Type", "application/json");
            byte[] body = new JSONObject().put("sdp", offerSdp).toString()
                    .getBytes(StandardCharsets.UTF_8);
            connection.getOutputStream().write(body);
            int status = connection.getResponseCode();
            InputStream source = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
            JSONObject payload = new JSONObject(new String(
                    source == null ? new byte[0] : source.readNBytes(524_288),
                    StandardCharsets.UTF_8));
            if (status != 200) {
                JSONObject error = payload.optJSONObject("error");
                String code = error == null ? "session-failed" : error.optString("code", "session-failed");
                String detail = error == null ? null : error.optString("message", null);
                Log.w(LOG_TAG, "voice call rejected code=" + code + " detail=" + detail);
                if (detail == null && error != null) {
                    Object details = error.opt("details");
                    if (details instanceof String) {
                        detail = (String) details;
                    } else if (details instanceof org.json.JSONObject) {
                        JSONObject detailsObject = (JSONObject) details;
                        detail = detailsObject.optString("message", null);
                        if (detail == null) {
                            detail = detailsObject.optString("code", null);
                        }
                    }
                }
                deliverFailure(
                    callback,
                    detail != null && !detail.isBlank()
                            ? code + ":" + detail
                            : code
                );
                return;
            }
            String answer = payload.optString("sdp", "");
            if (!answer.startsWith("v=0")) {
                deliverFailure(callback, "answer-invalid");
                return;
            }
            JSONObject greeting = payload.optJSONObject("connectGreetingEvent");
            if (greeting == null) {
                greeting = new JSONObject();
            }
            String sessionId = payload.optString("sessionId", "");
            final String finalSessionId = sessionId;
            final org.json.JSONObject finalGreeting = greeting;
            if (!closed.get()) {
                main.post(() -> callback.onAnswer(answer, finalSessionId, finalGreeting));
            }
        } catch (Exception ignored) {
            Log.w(LOG_TAG, "voice call request failed", ignored);
            deliverFailure(callback, "runtime-unavailable");
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    public void finalizeVoiceSession(
            Context context,
            String sessionId,
            org.json.JSONArray entries,
            FinalizeCallback callback
    ) {
        Context application = context.getApplicationContext();
        worker.execute(() -> requestFinalize(application, sessionId, entries, callback));
    }

    private void requestFinalize(
            Context context,
            String sessionId,
            org.json.JSONArray entries,
            FinalizeCallback callback
    ) {
        HttpURLConnection connection = null;
        try {
            if (sessionId == null || sessionId.isBlank()) {
                deliverFinalizeFailure(callback, "missing-session");
                return;
            }
            String token = new RuntimeSecretStore(context).loadLocalApiToken();
            connection = (HttpURLConnection) new URL(
                    "http://127.0.0.1:8765/v1/voice/sessions/finalize").openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(1500);
            // Finalize runs the full review agent + embeddings synchronously server-side;
            // match the management proxy's long timeout for the same operation.
            connection.setReadTimeout(65_000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Content-Type", "application/json");
            JSONObject body = new JSONObject()
                    .put("sessionId", sessionId)
                    .put("entries", entries == null ? new org.json.JSONArray() : entries);
            connection.getOutputStream().write(body.toString().getBytes(StandardCharsets.UTF_8));
            int status = connection.getResponseCode();
            InputStream source = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
            byte[] bytes = source == null ? new byte[0] : source.readNBytes(65_536);
            JSONObject response = new JSONObject(new String(bytes, StandardCharsets.UTF_8));
            if (status >= 300) {
                String message = response.optJSONObject("error") != null
                        ? response.optJSONObject("error").optString("message", "")
                        : "";
                deliverFinalizeFailure(callback, "finalize-" + status + ":" + message);
                return;
            }
            if (!closed.get()) main.post(() -> callback.onResult(response));
        } catch (Exception error) {
            Log.w(LOG_TAG, "finalize request failed", error);
            if (!closed.get()) main.post(() -> callback.onFailure("finalize-failed"));
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private void deliverFailure(Callback callback, String reason) {
        if (!closed.get()) main.post(() -> callback.onFailure(reason));
    }

    private void deliverToolFailure(ToolCallback callback, String reason) {
        if (!closed.get()) main.post(() -> callback.onFailure(reason));
    }

    private void deliverFinalizeFailure(FinalizeCallback callback, String reason) {
        if (!closed.get()) main.post(() -> callback.onFailure(reason));
    }

    private record McpResponse(JSONObject payload, String sessionId) {}

    @Override public void close() {
        if (closed.compareAndSet(false, true)) worker.shutdownNow();
    }
}
