package com.resonolabs.runtime.host;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.Consumer;

/** Bearer-authenticated device client for the canonical Creation lifecycle. */
public final class RuntimeCreationImportClient implements AutoCloseable {
    private static final String BASE = "http://127.0.0.1:8765/v1/host/creations";
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());

    public void preflight(Context context, JSONObject descriptor, Consumer<JSONObject> success,
                          Consumer<String> failure) {
        post(context, BASE + "/qr/preflight", descriptor, success, failure);
    }

    public void confirm(Context context, String token, boolean replace,
                        Consumer<JSONObject> success, Consumer<String> failure) {
        JSONObject payload = new JSONObject();
        try { payload.put("preflightToken", token); payload.put("replace", replace); }
        catch (Exception error) { failure.accept("Import request is invalid"); return; }
        post(context, BASE + "/confirm", payload, success, failure);
    }

    private void post(Context context, String url, JSONObject payload, Consumer<JSONObject> success,
                      Consumer<String> failure) {
        worker.execute(() -> {
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection) new URL(url).openConnection();
                connection.setRequestMethod("POST"); connection.setDoOutput(true);
                connection.setConnectTimeout(1500); connection.setReadTimeout(7000);
                connection.setRequestProperty("Authorization", "Bearer " +
                        new RuntimeSecretStore(context).loadLocalApiToken());
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setRequestProperty("Accept", "application/json");
                connection.setRequestProperty("X-ReSono-Agent-Audience", "both");
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(payload.toString().getBytes(StandardCharsets.UTF_8));
                }
                int status = connection.getResponseCode();
                InputStream stream = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
                JSONObject body = new JSONObject(stream == null ? "{}" :
                        new String(stream.readAllBytes(), StandardCharsets.UTF_8));
                if (status >= 400) {
                    JSONObject error = body.optJSONObject("error");
                    String message = error == null ? "Creation import failed" :
                            error.optString("message", "Creation import failed");
                    main.post(() -> failure.accept(message));
                } else main.post(() -> success.accept(body));
            } catch (Exception error) {
                main.post(() -> failure.accept("R1 runtime is unavailable"));
            } finally { if (connection != null) connection.disconnect(); }
        });
    }

    @Override public void close() { worker.shutdownNow(); }
}
