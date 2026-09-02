package com.resonolabs.feature.settings;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.os.Handler;
import android.os.Looper;

import java.util.HashMap;
import java.util.Map;

/** Observes confirmed captive-portal capability on Wi-Fi transports. */
final class WifiCaptivePortalMonitor implements AutoCloseable {
    interface Listener { void onCaptivePortalChanged(boolean active); }

    private final ConnectivityManager connectivity;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final Listener listener;
    private final Map<Network, Boolean> portalNetworks = new HashMap<>();
    private boolean registered;
    private boolean captivePortal;

    private final ConnectivityManager.NetworkCallback callback =
            new ConnectivityManager.NetworkCallback() {
                @Override public void onCapabilitiesChanged(
                        Network network, NetworkCapabilities capabilities) {
                    update(network, capabilities);
                }

                @Override public void onLost(Network network) {
                    if (!registered) return;
                    portalNetworks.remove(network);
                    publishIfChanged();
                }
            };

    WifiCaptivePortalMonitor(Context context, Listener listener) {
        this.connectivity = context.getSystemService(ConnectivityManager.class);
        this.listener = listener;
    }

    void start() {
        if (registered || connectivity == null) return;
        NetworkRequest request = new NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .build();
        try {
            connectivity.registerNetworkCallback(request, callback, mainHandler);
            registered = true;
        } catch (RuntimeException unavailable) {
            registered = false;
            portalNetworks.clear();
            publish(false);
        }
    }

    @Override public void close() {
        if (registered) {
            try {
                connectivity.unregisterNetworkCallback(callback);
            } catch (RuntimeException ignored) { }
            registered = false;
        }
        portalNetworks.clear();
        publish(false);
    }

    private void update(Network network, NetworkCapabilities capabilities) {
        if (!registered) return;
        boolean active = capabilities != null
                && capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
                && capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_CAPTIVE_PORTAL);
        portalNetworks.put(network, active);
        publishIfChanged();
    }

    private void publishIfChanged() {
        publish(portalNetworks.containsValue(true));
    }

    private void publish(boolean active) {
        if (captivePortal == active) return;
        captivePortal = active;
        listener.onCaptivePortalChanged(active);
    }
}
