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

/** Authenticated device-only reader for active local Tasks. */
public final class TaskClient implements AutoCloseable {
    public interface Callback { void onTasks(JSONObject value); void onFailure(); }
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final AtomicBoolean closed = new AtomicBoolean();

    public void loadActive(Context context, Callback callback) {
        worker.execute(() -> {
            HttpURLConnection connection = null;
            try {
                String token = new RuntimeSecretStore(context.getApplicationContext()).loadLocalApiToken();
                connection = (HttpURLConnection) new URL("http://127.0.0.1:8765/v1/tasks/active").openConnection();
                connection.setConnectTimeout(1000);
                connection.setReadTimeout(3000);
                connection.setRequestProperty("Authorization", "Bearer " + token);
                connection.setRequestProperty("Accept", "application/json");
                if (connection.getResponseCode() != 200) { failure(callback); return; }
                try (InputStream input = connection.getInputStream()) {
                    JSONObject value = new JSONObject(new String(input.readAllBytes(), StandardCharsets.UTF_8));
                    if (!closed.get()) main.post(() -> callback.onTasks(value));
                }
            } catch (Exception ignored) { failure(callback); }
            finally { if (connection != null) connection.disconnect(); }
        });
    }

    private void failure(Callback callback) { if (!closed.get()) main.post(callback::onFailure); }
    @Override public void close() { if (closed.compareAndSet(false, true)) worker.shutdownNow(); }
}
