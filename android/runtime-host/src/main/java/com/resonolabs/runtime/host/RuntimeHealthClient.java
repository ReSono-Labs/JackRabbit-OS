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
import java.util.function.Consumer;

/** APK-side consumer of the versioned private runtime health contract. */
public final class RuntimeHealthClient implements AutoCloseable {
    private static final int MAX_ATTEMPTS = 20;
    private static final long RETRY_MILLIS = 250L;
    private final ExecutorService worker = Executors.newSingleThreadExecutor(runnable -> {
        Thread thread = new Thread(runnable, "resono-runtime-health-client");
        thread.setDaemon(true);
        return thread;
    });
    private final Handler main = new Handler(Looper.getMainLooper());
    private final AtomicBoolean closed = new AtomicBoolean();

    public void checkUntilReady(Context context, Consumer<RuntimeHealth> callback) {
        Context application = context.getApplicationContext();
        worker.execute(() -> {
            RuntimeHealth result = RuntimeHealth.unavailable();
            for (int attempt = 0; attempt < MAX_ATTEMPTS && !closed.get(); attempt++) {
                result = request(application);
                if ("ready".equals(result.status())) break;
                try {
                    Thread.sleep(RETRY_MILLIS);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
            RuntimeHealth delivered = result;
            if (!closed.get()) main.post(() -> callback.accept(delivered));
        });
    }

    private RuntimeHealth request(Context context) {
        HttpURLConnection connection = null;
        try {
            String token = new RuntimeSecretStore(context).loadLocalApiToken();
            connection = (HttpURLConnection) new URL("http://127.0.0.1:8765/v1/health").openConnection();
            connection.setConnectTimeout(500);
            connection.setReadTimeout(500);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Accept", "application/json");
            if (connection.getResponseCode() != 200) return RuntimeHealth.unavailable();
            try (InputStream input = connection.getInputStream()) {
                JSONObject payload = new JSONObject(new String(input.readAllBytes(), StandardCharsets.UTF_8));
                JSONObject database = payload.getJSONObject("database");
                return new RuntimeHealth(
                        payload.getString("status"),
                        payload.getInt("contractVersion"),
                        database.getInt("migrationVersion"));
            }
        } catch (Exception ignored) {
            return RuntimeHealth.unavailable();
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    @Override public void close() {
        if (closed.compareAndSet(false, true)) worker.shutdownNow();
    }
}
