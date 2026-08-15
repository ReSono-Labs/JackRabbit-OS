package com.resonolabs.runtime.host;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.LinkAddress;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONObject;

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
public final class RuntimeManagementClient implements AutoCloseable {
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

    private RuntimeManagementPairing request(Context context) {
        HttpURLConnection connection = null;
        try {
            String token = new RuntimeSecretStore(context).loadLocalApiToken();
            connection = (HttpURLConnection) new URL(
                    "http://127.0.0.1:8765/v1/management/pairing").openConnection();
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

    @Override public void close() {
        if (closed.compareAndSet(false, true)) worker.shutdownNow();
    }
}
