package com.resonolabs.runtime.host;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class CreationCatalogClient implements AutoCloseable {
    public interface Callback {
        void onCatalog(JSONObject catalog);
        void onFailure();
    }

    public record Asset(byte[] body, String contentType) {}

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());

    public void load(Context context, Callback callback) {
        worker.execute(() -> {
            try {
                Asset asset = request(context, "/v1/cards/catalog", 512 * 1024);
                JSONObject value = new JSONObject(new String(asset.body(), java.nio.charset.StandardCharsets.UTF_8));
                main.post(() -> callback.onCatalog(value));
            } catch (Exception ignored) {
                main.post(callback::onFailure);
            }
        });
    }

    public Asset asset(Context context, String path) throws Exception {
        if (!path.startsWith("/v1/creations/") || !path.contains("/assets/")) {
            throw new IllegalArgumentException("Invalid Creation asset path");
        }
        return request(context, path, 8 * 1024 * 1024);
    }

    private Asset request(Context context, String path, int limit) throws Exception {
        String token = new RuntimeSecretStore(context).loadLocalApiToken();
        HttpURLConnection connection = (HttpURLConnection) new URL("http://127.0.0.1:8765" + path).openConnection();
        try {
            connection.setConnectTimeout(1500);
            connection.setReadTimeout(5000);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            int status = connection.getResponseCode();
            if (status != 200) throw new IllegalStateException("Creation HTTP " + status);
            InputStream input = connection.getInputStream();
            byte[] body = input.readNBytes(limit + 1);
            if (body.length > limit) throw new IllegalStateException("Creation response too large");
            return new Asset(body, connection.getContentType());
        } finally {
            connection.disconnect();
        }
    }

    @Override public void close() {
        worker.shutdownNow();
    }
}
