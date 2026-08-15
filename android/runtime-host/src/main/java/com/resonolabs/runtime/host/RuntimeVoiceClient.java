package com.resonolabs.runtime.host;

import android.content.Context;
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

    public interface Callback {
        void onAnswer(String sdp, JSONObject connectGreetingEvent);
        void onFailure(String reason);
    }

    public interface ToolCallback {
        void onResult(String output);
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

    public void callTool(Context context, String name, JSONObject arguments, ToolCallback callback) {
        Context application = context.getApplicationContext();
        worker.execute(() -> requestTool(application, name, arguments, callback));
    }

    private void requestTool(Context context, String name, JSONObject arguments, ToolCallback callback) {
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
            McpResponse response = postMcp(token, request, init.sessionId, false);
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
        HttpURLConnection connection = (HttpURLConnection) new URL(
                "http://127.0.0.1:8765/v1/mcp").openConnection();
        try {
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(1500);
            connection.setReadTimeout(10_000);
            connection.setDoOutput(true);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Content-Type", "application/json");
            if (sessionId != null) {
                connection.setRequestProperty("Mcp-Session-Id", sessionId);
                connection.setRequestProperty("MCP-Protocol-Version", MCP_VERSION);
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
                deliverFailure(callback, error == null ? "session-failed" : error.optString("code", "session-failed"));
                return;
            }
            String answer = payload.optString("sdp", "");
            if (!answer.startsWith("v=0")) {
                deliverFailure(callback, "answer-invalid");
                return;
            }
            JSONObject greeting = payload.optJSONObject("connectGreetingEvent");
            if (!closed.get()) main.post(() -> callback.onAnswer(answer, greeting));
        } catch (Exception ignored) {
            deliverFailure(callback, "runtime-unavailable");
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

    private record McpResponse(JSONObject payload, String sessionId) {}

    @Override public void close() {
        if (closed.compareAndSet(false, true)) worker.shutdownNow();
    }
}
