package com.resonolabs.feature.settings;

import android.Manifest;
import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.provider.Settings;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Foreground-only Wi-Fi discovery. Results never leave the Android device. */
final class WifiNetworkScanner {
    record Network(String ssid, int signalLevel, boolean secured, boolean connected) { }
    interface Listener { void onNetworks(String state, List<Network> networks); }

    private final Activity activity;
    private final WifiManager wifi;
    private final Listener listener;
    private boolean receiverRegistered;
    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            boolean updated = intent == null
                    || intent.getBooleanExtra(WifiManager.EXTRA_RESULTS_UPDATED, true);
            if (updated) publishResults();
            else listener.onNetworks("Wi-Fi scan did not complete", List.of());
        }
    };

    WifiNetworkScanner(Activity activity, Listener listener) {
        this.activity = activity;
        this.listener = listener;
        this.wifi = activity.getSystemService(WifiManager.class);
    }

    void refresh() {
        if (wifi == null || !wifi.isWifiEnabled()) {
            listener.onNetworks("Wi-Fi is off", List.of());
            return;
        }
        if (!hasPermission()) {
            // This is a dedicated embedded HOME. The system image must grant
            // scan access at boot; never interrupt the owner with a dialog.
            listener.onNetworks("R1 image missing Wi-Fi scan grant", List.of());
            return;
        }
        enableLocationForWifiScan();
        registerReceiver();
        listener.onNetworks("Scanning…", List.of());
        try {
            boolean started = wifi.startScan();
            if (!started) listener.onNetworks("Wi-Fi scan could not start", List.of());
        } catch (SecurityException exception) {
            listener.onNetworks("System denied Wi-Fi scan", List.of());
        }
    }

    void onWindowFocusChanged(boolean hasFocus) {
        // Permission prompts are intentionally forbidden on this appliance.
    }

    void close() {
        if (!receiverRegistered) return;
        try { activity.unregisterReceiver(receiver); }
        catch (IllegalArgumentException ignored) { }
        receiverRegistered = false;
    }

    private void registerReceiver() {
        if (receiverRegistered) return;
        IntentFilter filter = new IntentFilter(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION);
        if (Build.VERSION.SDK_INT >= 33) activity.registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED);
        else activity.registerReceiver(receiver, filter);
        receiverRegistered = true;
    }

    @SuppressWarnings("deprecation")
    private void publishResults() {
        try {
            WifiInfo info = wifi.getConnectionInfo();
            String current = normalizeSsid(info == null ? null : info.getSSID());
            Map<String, Network> strongest = new LinkedHashMap<>();
            for (ScanResult result : wifi.getScanResults()) {
                String ssid = normalizeSsid(result.SSID);
                if (ssid.isEmpty()) continue;
                Network candidate = new Network(
                        ssid,
                        WifiManager.calculateSignalLevel(result.level, 4),
                        result.capabilities != null && !result.capabilities.isBlank()
                                && !"[ESS]".equals(result.capabilities),
                        ssid.equals(current));
                Network prior = strongest.get(ssid);
                if (prior == null || candidate.signalLevel() > prior.signalLevel()) strongest.put(ssid, candidate);
            }
            ArrayList<Network> networks = new ArrayList<>(strongest.values());
            networks.sort(Comparator.comparing(Network::connected).reversed()
                    .thenComparing(Comparator.comparingInt(Network::signalLevel).reversed())
                    .thenComparing(Network::ssid, String.CASE_INSENSITIVE_ORDER));
            listener.onNetworks(networks.isEmpty() ? "Scan completed with no results" : "Available networks", networks);
        } catch (SecurityException exception) {
            listener.onNetworks("System denied Wi-Fi results", List.of());
        }
    }

    private boolean hasPermission() {
        // The stock Rabbit launcher bypasses this gate with its platform
        // signature. ReSono has a separate signing identity, so it must use
        // the runtime scan grants that RabbitLauncher also declares.
        boolean coarse = activity.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        boolean location = activity.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        boolean nearby = Build.VERSION.SDK_INT < 33
                || activity.checkSelfPermission(Manifest.permission.NEARBY_WIFI_DEVICES)
                == PackageManager.PERMISSION_GRANTED;
        return coarse && location && nearby;
    }

    private void enableLocationForWifiScan() {
        try {
            Settings.Secure.putInt(activity.getContentResolver(),
                    Settings.Secure.LOCATION_MODE, Settings.Secure.LOCATION_MODE_HIGH_ACCURACY);
        } catch (SecurityException ignored) { }
    }

    private static String normalizeSsid(String value) {
        if (value == null || "<unknown ssid>".equalsIgnoreCase(value)) return "";
        String result = value.trim();
        if (result.length() >= 2 && result.startsWith("\"") && result.endsWith("\"")) {
            result = result.substring(1, result.length() - 1);
        }
        return result;
    }
}
