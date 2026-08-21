package com.resonolabs.runtime.host;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

/** Device-local client for native background-run notifications. */
public final class RuntimeBackgroundRunClient implements AutoCloseable {
    private static final String BASE = "http://127.0.0.1:8765/v1/host/background-agent/notifications";
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final AtomicBoolean closed = new AtomicBoolean();

    public void load(Context context, Consumer<List<BackgroundRunSnapshot>> callback) {
        request(context.getApplicationContext(), BASE, "GET", payload -> {
            JSONArray items = payload.optJSONArray("runs");
            List<BackgroundRunSnapshot> runs = new ArrayList<>();
            if (items != null) for (int i = 0; i < items.length(); i++) {
                JSONObject item = items.optJSONObject(i);
                if (item != null) runs.add(BackgroundRunSnapshot.fromJson(item));
            }
            callback.accept(List.copyOf(runs));
        });
    }

    public void acknowledge(Context context, String runId, Runnable complete) {
        request(context.getApplicationContext(), BASE + "/" + runId + "/view", "POST",
                ignored -> complete.run());
    }

    private void request(Context context, String url, String method, Consumer<JSONObject> callback) {
        worker.execute(() -> {
            JSONObject result = new JSONObject();
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection) new URL(url).openConnection();
                connection.setRequestMethod(method);
                connection.setConnectTimeout(800);
                connection.setReadTimeout(1500);
                connection.setRequestProperty("Authorization", "Bearer " +
                        new RuntimeSecretStore(context).loadLocalApiToken());
                connection.setRequestProperty("Accept", "application/json");
                if ("POST".equals(method)) {
                    connection.setDoOutput(true);
                    connection.setRequestProperty("Content-Type", "application/json");
                    try (OutputStream output = connection.getOutputStream()) {
                        output.write("{}".getBytes(StandardCharsets.UTF_8));
                    }
                }
                InputStream stream = connection.getResponseCode() >= 400
                        ? connection.getErrorStream() : connection.getInputStream();
                if (stream != null) result = new JSONObject(
                        new String(stream.readAllBytes(), StandardCharsets.UTF_8));
            } catch (Exception ignored) { }
            finally { if (connection != null) connection.disconnect(); }
            JSONObject delivered = result;
            if (!closed.get()) main.post(() -> callback.accept(delivered));
        });
    }

    @Override public void close() {
        if (closed.compareAndSet(false, true)) worker.shutdownNow();
    }
}
