package com.resonolabs.runtime.host;

import android.content.Context;
import android.util.Base64;
import android.util.Log;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONArray;
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
        void onAnswer(String sdp, String sessionId, JSONObject connectGreetingEvent, boolean live, String greetingText, String transport);
        void onFailure(String reason);
    }

    public interface ToolCallback {
        void onResult(String output, JSONObject sessionUpdate);
        void onFailure(String reason);
    }

    public interface FinalizeCallback {
        void onResult(JSONObject response);
        void onFailure(String reason);
    }

    public interface CompletionCallback {
        void onResult(JSONObject completion);
        void onFailure(String reason);
    }

    public interface DelegationCallback {
        void onResult(String output);
        void onFailure(String reason);
    }

    public void pollCompletion(Context context, String voiceSessionId, CompletionCallback callback) {
        Context application = context.getApplicationContext();
        worker.execute(() -> requestCompletion(application, voiceSessionId, callback));
    }

    public void acknowledgeCompletion(Context context, String voiceSessionId, String runId) {
        Context application = context.getApplicationContext();
        worker.execute(() -> requestCompletionAck(application, voiceSessionId, runId));
    }

    private void requestCompletion(Context context, String voiceSessionId, CompletionCallback callback) {
        HttpURLConnection connection = null;
        try {
            String token = new RuntimeSecretStore(context).loadLocalApiToken();
            connection = (HttpURLConnection) new URL(
                    "http://127.0.0.1:8765/v1/voice/completions/next").openConnection();
            connection.setConnectTimeout(1500);
            connection.setReadTimeout(3000);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("X-ReSono-Voice-Session", voiceSessionId);
            int status = connection.getResponseCode();
            InputStream source = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
            JSONObject payload = new JSONObject(new String(
                    source == null ? new byte[0] : source.readNBytes(65_536), StandardCharsets.UTF_8));
            if (status != 200) throw new IllegalStateException("completion-" + status);
            JSONObject completion = payload.optJSONObject("completion");
            if (!closed.get()) main.post(() -> callback.onResult(completion));
        } catch (Exception error) {
            if (!closed.get()) main.post(() -> callback.onFailure("completion-unavailable"));
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private void requestCompletionAck(Context context, String voiceSessionId, String runId) {
        HttpURLConnection connection = null;
        try {
            String token = new RuntimeSecretStore(context).loadLocalApiToken();
            connection = (HttpURLConnection) new URL(
                    "http://127.0.0.1:8765/v1/voice/completions/ack").openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(1500);
            connection.setReadTimeout(3000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Content-Type", "application/json");
            connection.setRequestProperty("X-ReSono-Voice-Session", voiceSessionId);
            connection.getOutputStream().write(
                    new JSONObject().put("runId", runId).toString().getBytes(StandardCharsets.UTF_8));
            connection.getResponseCode();
        } catch (Exception error) {
            Log.w(LOG_TAG, "completion acknowledgement failed", error);
        } finally {
            if (connection != null) connection.disconnect();
        }
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

    /** Execute an AVAS delegation (free-form request handed to the client).
     *  Lists the granted on-device tools, picks a best-effort match, and runs
     *  it through the same local MCP boundary the realtime model uses.
     *  goal_start requires the session to be in goal_intake mode first, so the
     *  mode switch is issued ahead of it when selected. */
    public void callDelegation(Context context, String voiceSessionId, String delegationItemId,
                               String requestText, DelegationCallback callback) {
        Context application = context.getApplicationContext();
        worker.execute(() -> requestDelegation(application, voiceSessionId, delegationItemId, requestText, callback));
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
            JSONObject sessionUpdate = result.optJSONObject("resonoSessionUpdate");
            result.remove("resonoSessionUpdate");
            JSONObject finalSessionUpdate = sessionUpdate;
            if (!closed.get()) main.post(() -> callback.onResult(result.toString(), finalSessionUpdate));
        } catch (Exception ignored) {
            deliverToolFailure(callback, "mcp-unavailable");
        }
    }

    private void requestDelegation(Context context, String voiceSessionId, String delegationItemId,
                                   String requestText, DelegationCallback callback) {
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
                deliverDelegationFailure(callback, "mcp-initialize-failed");
                return;
            }
            postMcp(token, new JSONObject()
                    .put("jsonrpc", "2.0")
                    .put("method", "notifications/initialized"), init.sessionId, true);
            McpResponse list = postMcp(token, new JSONObject()
                    .put("jsonrpc", "2.0")
                    .put("id", 2)
                    .put("method", "tools/list"), init.sessionId, false);
            JSONObject listResult = list.payload.optJSONObject("result");
            JSONArray tools = listResult == null ? null : listResult.optJSONArray("tools");
            DelegationToolCall selected = selectDelegationTool(requestText, tools);
            if (selected == null) {
                deliverDelegationFailure(callback, "no-matching-tool");
                return;
            }
            if ("goal_start".equals(selected.name)) {
                McpResponse modeSwitch = postMcp(token, new JSONObject()
                        .put("jsonrpc", "2.0")
                        .put("id", 3)
                        .put("method", "tools/call")
                        .put("params", new JSONObject()
                                .put("name", "voice_mode_switch")
                                .put("arguments", new JSONObject().put("modeKey", "goal_intake"))),
                        init.sessionId, false);
                JSONObject modeResult = modeSwitch.payload.optJSONObject("result");
                if (modeResult == null || modeResult.optBoolean("isError", false)) {
                    deliverDelegationFailure(callback, "mode-switch-failed");
                    return;
                }
            }
            McpResponse call = postMcp(token, new JSONObject()
                    .put("jsonrpc", "2.0")
                    .put("id", 4)
                    .put("method", "tools/call")
                    .put("params", new JSONObject()
                            .put("name", selected.name)
                            .put("arguments", selected.arguments)),
                    init.sessionId, false, voiceSessionId, delegationItemId, requestText, 0);
            JSONObject callResult = call.payload.optJSONObject("result");
            if (callResult == null) {
                deliverDelegationFailure(callback, "tool-call-failed");
                return;
            }
            String output = extractToolOutput(callResult);
            if (!closed.get()) main.post(() -> callback.onResult(output));
        } catch (Exception error) {
            Log.w(LOG_TAG, "delegation execution failed", error);
            deliverDelegationFailure(callback, "delegation-unavailable");
        }
    }

    private static final class DelegationToolCall {
        final String name;
        final JSONObject arguments;
        DelegationToolCall(String name, JSONObject arguments) { this.name = name; this.arguments = arguments; }
    }

    private static DelegationToolCall selectDelegationTool(String requestText, JSONArray tools) {
        if (tools == null) return null;
        // ROOT lowercase turns Turkish İ into "i\u0307" (i + combining dot);
        // collapse it so "İnternet" matches the "internet" keyword.
        String text = (requestText == null ? "" : requestText)
                .toLowerCase(java.util.Locale.ROOT)
                .replace("i\u0307", "i");
        if (containsName(tools, "goal_start") && containsAny(text,
                "background", "arka plan", "agent", "goal", "görev")) {
            return new DelegationToolCall("goal_start", goalStartArguments(requestText));
        }
        if (containsName(tools, "web_search") && containsAny(text,
                "web", "search", "internet", "google", " ara", "sorgula")) {
            try {
                return new DelegationToolCall("web_search",
                        new JSONObject().put("query", requestText == null ? "" : requestText));
            } catch (Exception ignored) { return null; }
        }
        if (containsName(tools, "get_device_status") && containsAny(text,
                "durum", "status", "sağlık", "health", "battery", "pil")) {
            return new DelegationToolCall("get_device_status", new JSONObject());
        }
        if (containsName(tools, "memory_lookup") && containsAny(text,
                "hatırla", "remember", "memory", "anı", "geçmiş")) {
            try {
                return new DelegationToolCall("memory_lookup",
                        new JSONObject().put("query", requestText == null ? "" : requestText));
            } catch (Exception ignored) { return null; }
        }
        return null;
    }

    private static boolean containsName(JSONArray tools, String name) {
        for (int i = 0; i < tools.length(); i++) {
            JSONObject tool = tools.optJSONObject(i);
            if (tool != null && name.equals(tool.optString("name", ""))) return true;
        }
        return false;
    }

    /** Keyword match that avoids substring false positives (e.g. "anı" inside
     *  "kullanım"). Multi-word needles match as phrases; single-word needles
     *  match only at token starts, which still covers Turkish inflections
     *  ("hatırla" matches "hatırladın", but not "kullanım"). */
    private static boolean containsAny(String text, String... needles) {
        String[] tokens = text.split("[^a-z0-9çğıöşü]+");
        for (String needle : needles) {
            if (needle.indexOf(' ') >= 0) {
                if (text.contains(needle)) return true;
                continue;
            }
            for (String token : tokens) {
                if (token.startsWith(needle)) return true;
            }
        }
        return false;
    }

    private static JSONObject goalStartArguments(String requestText) {
        try {
            String text = requestText == null ? "" : requestText.trim();
            if (text.isEmpty()) text = "Complete the user's request.";
            return new JSONObject()
                    .put("originalRequest", text)
                    .put("objective", text)
                    .put("successCriteria", new JSONArray().put(
                            "The task described in the original request is completed successfully and its result is verified."))
                    .put("verificationMethod", "Review the final result and confirm it satisfies the original request.")
                    .put("completionConditions", new JSONArray().put(
                            "A final result is produced and reported to the user."))
                    .put("stopConditions", new JSONArray());
        } catch (Exception ignored) {
            return new JSONObject();
        }
    }

    private static String extractToolOutput(JSONObject result) {
        boolean isError = result.optBoolean("isError", false);
        JSONArray content = result.optJSONArray("content");
        String text = "";
        if (content != null && content.length() > 0) {
            text = content.optJSONObject(0).optString("text", "");
        }
        if (text.isBlank()) text = result.toString();
        return isError ? "Error: " + text : text;
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
                String detail = error == null ? payload.optString("message", null) : error.optString("message", null);
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
            final boolean finalLive = payload.optBoolean("live", false);
            final String finalGreetingText = payload.optString("greetingText", "");
            final String finalTransport = payload.optString("transport", "");
            if (!closed.get()) {
                main.post(() -> callback.onAnswer(answer, finalSessionId, finalGreeting, finalLive, finalGreetingText, finalTransport));
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

    private void deliverDelegationFailure(DelegationCallback callback, String reason) {
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
