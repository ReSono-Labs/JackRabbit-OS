package com.resonolabs.runtime.host;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.LinkAddress;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.OutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

/** APK-side reader for the local management pairing contract. */
public final class RuntimeManagementClient implements AutoCloseable, ManagementOpenAiSource {
    private static final String BASE_URL = "http://127.0.0.1:8765";
    private final ExecutorService worker = Executors.newSingleThreadExecutor(runnable -> {
        Thread thread = new Thread(runnable, "resono-runtime-management-client");
        thread.setDaemon(true);
        return thread;
    });
    private final Handler main = new Handler(Looper.getMainLooper());
    private final AtomicBoolean closed = new AtomicBoolean();

    public void loadPairing(Context context, Consumer<RuntimeManagementPairing> callback) {
        Context application = context.getApplicationContext();
        worker.execute(() -> {
            RuntimeManagementPairing result = request(application);
            if (!closed.get()) main.post(() -> callback.accept(result));
        });
    }

    public void loadOpenAiSettings(Context context, Consumer<JSONObject> callback) {
        loadOpenAi(context.getApplicationContext(), "/v1/host/openai", "GET", "", callback);
    }

    @Override
    public void load(Context context, Consumer<ManagementOpenAiState> callback) {
        loadOpenAi(context, callback, "/v1/host/openai", "GET", "");
    }

    public void connectOpenAi(Context context, Consumer<JSONObject> callback, String apiKey) {
        loadOpenAi(context.getApplicationContext(), "/v1/host/openai/connect", "POST", body("apiKey", apiKey), callback);
    }

    @Override
    public void connect(Context context, String apiKey, Consumer<ManagementOpenAiState> callback) {
        connectOpenAi(context, payload -> callback.accept(ManagementOpenAiState.fromJson(payload)), apiKey);
    }

    public void disconnectOpenAi(Context context, Consumer<JSONObject> callback) {
        loadOpenAi(context.getApplicationContext(), "/v1/host/openai/disconnect", "POST", "{}", callback);
    }

    @Override
    public void disconnect(Context context, Consumer<ManagementOpenAiState> callback) {
        disconnectOpenAi(context, payload -> callback.accept(ManagementOpenAiState.fromJson(payload)));
    }

    public void setOpenAiProvider(Context context, Consumer<JSONObject> callback, String provider) {
        loadOpenAi(context.getApplicationContext(), "/v1/host/openai/provider", "POST", body("provider", provider), callback);
    }

    @Override
    public void setProvider(Context context, String provider, Consumer<ManagementOpenAiState> callback) {
        setOpenAiProvider(context, payload -> callback.accept(ManagementOpenAiState.fromJson(payload)), provider);
    }

    public void setOpenAiAccessPath(Context context, Consumer<JSONObject> callback, String accessPath) {
        loadOpenAi(
                context.getApplicationContext(),
                "/v1/host/openai/access",
                "POST",
                body("accessPath", accessPath),
                callback
        );
    }

    @Override
    public void setAccessPath(Context context, String accessPath, Consumer<ManagementOpenAiState> callback) {
        setOpenAiAccessPath(context, payload -> callback.accept(ManagementOpenAiState.fromJson(payload)), accessPath);
    }

    public void setOpenAiModels(
            Context context,
            Consumer<JSONObject> callback,
            String textModel,
            String realtimeModel,
            String reasoningEffort
    ) {
        JSONObject body = new JSONObject();
        try {
            body.put("textModel", textModel == null ? JSONObject.NULL : textModel);
            body.put("realtimeModel", realtimeModel == null ? JSONObject.NULL : realtimeModel);
            body.put("reasoningEffort", reasoningEffort == null ? JSONObject.NULL : reasoningEffort);
            loadOpenAi(context.getApplicationContext(), "/v1/host/openai/models", "POST", body.toString(), callback);
        } catch (JSONException error) {
            callback.accept(new JSONObject());
        }
    }

    @Override
    public void setModels(
            Context context,
            String textModel,
            String realtimeModel,
            String reasoningEffort,
            Consumer<ManagementOpenAiState> callback
    ) {
        setOpenAiModels(
                context,
                payload -> callback.accept(ManagementOpenAiState.fromJson(payload)),
                textModel,
                realtimeModel,
                reasoningEffort
        );
    }

    public void refreshOpenAiSettings(Context context, Consumer<JSONObject> callback) {
        loadOpenAi(context.getApplicationContext(), "/v1/host/openai/refresh", "POST", "{}", callback);
    }

    @Override
    public void refresh(Context context, Consumer<ManagementOpenAiState> callback) {
        refreshOpenAiSettings(context, payload -> callback.accept(ManagementOpenAiState.fromJson(payload)));
    }

    private void loadOpenAi(
            Context context,
            Consumer<ManagementOpenAiState> callback,
            String path,
            String method,
            String body
    ) {
        loadOpenAi(context.getApplicationContext(), path, method, body,
                payload -> callback.accept(ManagementOpenAiState.fromJson(payload))
        );
    }

    private RuntimeManagementPairing request(Context context) {
        HttpURLConnection connection = null;
        try {
            String token = new RuntimeSecretStore(context).loadLocalApiToken();
            connection = (HttpURLConnection) new URL(BASE_URL + "/v1/management/pairing").openConnection();
            connection.setConnectTimeout(700);
            connection.setReadTimeout(700);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Accept", "application/json");
            if (connection.getResponseCode() != 200) return RuntimeManagementPairing.unavailable();
            try (InputStream input = connection.getInputStream()) {
                JSONObject payload = new JSONObject(
                        new String(input.readAllBytes(), StandardCharsets.UTF_8));
                String address = managementAddress(context);
                return new RuntimeManagementPairing(
                        address == null ? "network_unavailable" : "ready",
                        payload.getString("code"),
                        address == null ? "Connect R1 to Wi-Fi" : address,
                        payload.getLong("expiresAt"));
            }
        } catch (Exception ignored) {
            return RuntimeManagementPairing.unavailable();
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static String managementAddress(Context context) {
        ConnectivityManager connectivity = context.getSystemService(ConnectivityManager.class);
        Network network = connectivity == null ? null : connectivity.getActiveNetwork();
        NetworkCapabilities capabilities = network == null || connectivity == null
                ? null : connectivity.getNetworkCapabilities(network);
        boolean localNetwork = capabilities != null
                && (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
                || capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET));
        if (!localNetwork) return null;
        LinkProperties links = network == null || connectivity == null
                ? null : connectivity.getLinkProperties(network);
        if (links == null) return null;
        InetAddress fallback = null;
        for (LinkAddress link : links.getLinkAddresses()) {
            InetAddress address = link.getAddress();
            if (address.isLoopbackAddress() || address.isLinkLocalAddress()) continue;
            if (address instanceof Inet4Address) {
                return "https://" + address.getHostAddress() + ":" + ManagementHttpsServer.PORT;
            }
            fallback = address;
        }
        return fallback == null
                ? null
                : "https://[" + fallback.getHostAddress() + "]:" + ManagementHttpsServer.PORT;
    }

    private void loadOpenAi(
            Context context,
            String path,
            String method,
            String body,
            Consumer<JSONObject> callback
    ) {
        worker.execute(() -> {
            if (closed.get()) return;
            JSONObject result = requestOpenAi(context, path, method, body);
            if (!closed.get()) main.post(() -> callback.accept(result));
        });
    }

    private JSONObject requestOpenAi(Context context, String path, String method, String body) {
        HttpURLConnection connection = null;
        try {
            String token = new RuntimeSecretStore(context).loadLocalApiToken();
            connection = (HttpURLConnection) new URL(BASE_URL + path).openConnection();
            connection.setRequestMethod(method);
            connection.setConnectTimeout(1000);
            connection.setReadTimeout(30000);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Accept", "application/json");
            if (!body.isEmpty()) {
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json");
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(body.getBytes(StandardCharsets.UTF_8));
                }
            }
            int status = connection.getResponseCode();
            InputStream source = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
            byte[] bytes = source == null ? new byte[0] : source.readAllBytes();
            return bytes.length == 0 ? new JSONObject() : new JSONObject(new String(bytes, StandardCharsets.UTF_8));
        } catch (Exception exception) {
            Log.w("ReSonoRuntimeManagement", "openai settings request failed for " + path, exception);
            return new JSONObject();
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    @Override public void close() {
        if (closed.compareAndSet(false, true)) worker.shutdownNow();
    }

    private static String body(String key, String value) {
        try {
            return new JSONObject().put(key, value).toString();
        } catch (JSONException ignored) {
            return "{}";
        }
    }
}
