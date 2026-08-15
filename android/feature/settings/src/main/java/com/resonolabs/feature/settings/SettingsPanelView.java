package com.resonolabs.feature.settings;

import android.app.Activity;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.media.AudioManager;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.wifi.WifiManager;
import android.net.wifi.WifiConfiguration;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.resonolabs.ui.design.ReSonoTheme;
import com.resonolabs.ui.input.UiInputIntent;
import com.resonolabs.ui.input.UiInputTarget;

import java.util.List;

/** Large-format settings designed for direct use on the 480x640 R1 display. */
public final class SettingsPanelView extends View implements UiInputTarget {
    private static final float DESIGN_WIDTH = 480f;
    private static final float DESIGN_HEIGHT = 640f;
    private static final float ROW_TOP = 88f;
    private static final float ROW_STEP = 76f;
    private static final List<String> ROWS = List.of(
            "Wi-Fi", "Bluetooth", "Management", "Sound", "Display", "About");

    private final Activity activity;
    private final Runnable close;
    private final Runnable restart;
    private final ManagementPairingSource managementPairing;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final WifiNetworkScanner wifiScanner;
    private int selected;
    private String openPage;
    private String wifiScanState = "Tap refresh to scan";
    private List<WifiNetworkScanner.Network> wifiNetworks = List.of();
    private String bluetoothStatus = "Ready";
    private ManagementPairingState managementState = ManagementPairingState.loading();
    private boolean bluetoothReceiverRegistered;
    private final BroadcastReceiver bluetoothReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            if (intent == null || !BluetoothAdapter.ACTION_STATE_CHANGED.equals(intent.getAction())) return;
            int state = intent.getIntExtra(BluetoothAdapter.EXTRA_STATE, BluetoothAdapter.ERROR);
            bluetoothStatus = bluetoothStateLabel(state);
            invalidate();
        }
    };

    public SettingsPanelView(
            Activity activity,
            Runnable close,
            Runnable restart,
            ManagementPairingSource managementPairing) {
        super(activity);
        this.activity = activity;
        this.close = close;
        this.restart = restart;
        this.managementPairing = managementPairing;
        this.wifiScanner = new WifiNetworkScanner(activity, (state, networks) -> {
            wifiScanState = state;
            wifiNetworks = List.copyOf(networks);
            invalidate();
        });
        setContentDescription("In-app device settings");
    }

    @Override protected void onDraw(Canvas canvas) {
        canvas.drawColor(ReSonoTheme.BACKGROUND);
        canvas.save();
        canvas.scale(getWidth() / DESIGN_WIDTH, getHeight() / DESIGN_HEIGHT);
        if (openPage == null) drawIndex(canvas); else drawPage(canvas);
        canvas.restore();
    }

    private void drawIndex(Canvas canvas) {
        ReSonoTheme.text(canvas, paint, "Settings", 24f, 56f, 40f,
                ReSonoTheme.INK, Paint.Align.LEFT, true);
        drawClose(canvas);
        for (int i = 0; i < ROWS.size(); i++) {
            float top = ROW_TOP + i * ROW_STEP;
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(ReSonoTheme.PANEL);
            canvas.drawRoundRect(20f, top, 460f, top + 68f, 19f, 19f, paint);
            if (i == selected) {
                paint.setColor(ReSonoTheme.VIOLET);
                // Fixed-size cursor only: changing the entire row luminance can
                // drive Rabbit's MediaTek AAL/PQ backlight compensation.
                canvas.drawRoundRect(20f, top + 8f, 25f, top + 60f, 3f, 3f, paint);
            }
            ReSonoTheme.text(canvas, paint, ROWS.get(i), 46f, top + 45f, 29f,
                ReSonoTheme.INK, Paint.Align.LEFT, true);
            ReSonoTheme.text(canvas, paint, "›", 430f, top + 46f, 36f,
                    ReSonoTheme.MUTED,
                    Paint.Align.CENTER, false);
        }
    }

    private void drawPage(Canvas canvas) {
        ReSonoTheme.text(canvas, paint, "‹", 28f, 53f, 42f,
                ReSonoTheme.CYAN, Paint.Align.CENTER, false);
        ReSonoTheme.text(canvas, paint, openPage, 58f, 54f, 37f,
                ReSonoTheme.INK, Paint.Align.LEFT, true);
        drawClose(canvas);

        if ("Wi-Fi".equals(openPage)) {
            drawWifiPage(canvas);
            return;
        }
        if ("Management".equals(openPage)) {
            drawManagementPage(canvas);
            return;
        }
        SettingValue[] values = statusValues(openPage);
        float top = 102f;
        for (SettingValue value : values) {
            paint.setColor(ReSonoTheme.PANEL_RAISED);
            paint.setStyle(Paint.Style.FILL);
            canvas.drawRoundRect(20f, top, 460f, top + 112f, 22f, 22f, paint);
            ReSonoTheme.text(canvas, paint, value.label, 44f, top + 39f, 21f,
                ReSonoTheme.MUTED, Paint.Align.LEFT, true);
            ReSonoTheme.text(canvas, paint, value.value, 44f, top + 86f, 34f,
                    ReSonoTheme.INK, Paint.Align.LEFT, true);
            top += 126f;
        }

        if ("Sound".equals(openPage)) {
            button(canvas, "−", 20f, 494f, 230f);
            button(canvas, "+", 250f, 494f, 460f);
        } else if ("Display".equals(openPage)) {
            button(canvas, "−", 20f, 494f, 230f);
            button(canvas, "+", 250f, 494f, 460f);
        } else if ("Bluetooth".equals(openPage)) {
            button(canvas, isBluetoothEnabled() ? "TURN OFF" : "TURN ON", 20f, 494f, 460f);
        } else if ("About".equals(openPage)) {
            button(canvas, "RESTART DEVICE", 20f, 494f, 460f);
        } else {
            button(canvas, "REFRESH", 20f, 494f, 460f);
        }
    }

    private void drawWifiPage(Canvas canvas) {
        SettingValue[] values = network();
        ReSonoTheme.text(canvas, paint, values[0].value + "  •  " + values[1].value,
                24f, 91f, 20f, ReSonoTheme.MUTED, Paint.Align.LEFT, true);
        String wifiHint = wifiNetworks.isEmpty() ? wifiScanState : "TAP A NETWORK TO CONNECT";
        ReSonoTheme.text(canvas, paint, wifiHint.toUpperCase(), 24f, 127f, 17f,
                ReSonoTheme.CYAN, Paint.Align.LEFT, true);
        float top = 148f;
        int count = Math.min(6, wifiNetworks.size());
        for (int i = 0; i < count; i++) {
            WifiNetworkScanner.Network network = wifiNetworks.get(i);
            paint.setColor(network.connected() ? 0xff18342e : ReSonoTheme.PANEL_RAISED);
            paint.setStyle(Paint.Style.FILL);
            canvas.drawRoundRect(20f, top, 460f, top + 52f, 17f, 17f, paint);
            String name = network.ssid().length() > 24 ? network.ssid().substring(0, 23) + "…" : network.ssid();
            ReSonoTheme.text(canvas, paint, name, 38f, top + 34f, 22f,
                    ReSonoTheme.INK, Paint.Align.LEFT, true);
            String detail = network.connected() ? "CONNECTED" : (network.secured() ? "SECURE" : "OPEN");
            ReSonoTheme.text(canvas, paint, detail, 425f, top + 32f, 14f,
                    network.connected() ? 0xff57d6a7 : ReSonoTheme.MUTED, Paint.Align.RIGHT, true);
            for (int bar = 0; bar < 4; bar++) {
                paint.setColor(bar < network.signalLevel() ? ReSonoTheme.CYAN : 0xff3d3a4d);
                canvas.drawRoundRect(432f + bar * 6f, top + 39f - bar * 4f,
                        436f + bar * 6f, top + 47f, 2f, 2f, paint);
            }
            top += 59f;
        }
        button(canvas, "SCAN AGAIN", 20f, 532f, 460f);
    }

    private void drawManagementPage(Canvas canvas) {
        paint.setColor(ReSonoTheme.PANEL_RAISED);
        paint.setStyle(Paint.Style.FILL);
        canvas.drawRoundRect(20f, 108f, 460f, 270f, 22f, 22f, paint);
        ReSonoTheme.text(canvas, paint, "PAIRING CODE", 44f, 151f, 19f,
                ReSonoTheme.MUTED, Paint.Align.LEFT, true);
        ReSonoTheme.text(canvas, paint, managementState.code(), 44f, 226f, 54f,
                ReSonoTheme.CYAN, Paint.Align.LEFT, true);

        paint.setColor(ReSonoTheme.PANEL_RAISED);
        canvas.drawRoundRect(20f, 288f, 460f, 440f, 22f, 22f, paint);
        ReSonoTheme.text(canvas, paint, "OPEN ON YOUR COMPUTER", 44f, 331f, 19f,
                ReSonoTheme.MUTED, Paint.Align.LEFT, true);
        String address = managementState.address();
        if (address.length() > 34) address = address.substring(0, 33) + "…";
        ReSonoTheme.text(canvas, paint, address, 44f, 383f, 24f,
                ReSonoTheme.INK, Paint.Align.LEFT, true);
        ReSonoTheme.text(canvas, paint, "HTTPS • SAME NETWORK", 44f, 417f, 16f,
                ReSonoTheme.MUTED, Paint.Align.LEFT, true);
        button(canvas, "REFRESH", 20f, 494f, 460f);
    }

    private void refreshManagement() {
        managementState = ManagementPairingState.loading();
        invalidate();
        managementPairing.load(state -> {
            managementState = state;
            invalidate();
        });
    }

    private void drawClose(Canvas canvas) {
        paint.setColor(ReSonoTheme.PANEL_RAISED);
        paint.setStyle(Paint.Style.FILL);
        canvas.drawCircle(438f, 40f, 25f, paint);
        ReSonoTheme.text(canvas, paint, "×", 438f, 50f, 36f,
                ReSonoTheme.INK, Paint.Align.CENTER, false);
    }

    private SettingValue[] statusValues(String page) {
        return switch (page) {
            case "Wi-Fi" -> network();
            case "Bluetooth" -> bluetooth();
            case "Sound" -> sound();
            case "Display" -> display();
            default -> new SettingValue[]{
                    new SettingValue("DEVICE", "ReSono R1"),
                    new SettingValue("BUILD", android.os.Build.VERSION.INCREMENTAL),
                    new SettingValue("ANDROID", android.os.Build.VERSION.RELEASE)};
        };
    }

    private SettingValue[] network() {
        WifiManager wifi = activity.getSystemService(WifiManager.class);
        ConnectivityManager cm = activity.getSystemService(ConnectivityManager.class);
        Network network = cm == null ? null : cm.getActiveNetwork();
        NetworkCapabilities caps = network == null || cm == null
                ? null : cm.getNetworkCapabilities(network);
        boolean validated = caps != null
                && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);
        return new SettingValue[]{
                new SettingValue("WI-FI", wifi != null && wifi.isWifiEnabled() ? "On" : "Off"),
                new SettingValue("INTERNET", validated ? "Connected" : "Offline")};
    }

    private SettingValue[] bluetooth() {
        BluetoothManager manager = activity.getSystemService(BluetoothManager.class);
        BluetoothAdapter adapter = manager == null ? null : manager.getAdapter();
        return new SettingValue[]{
                new SettingValue("BLUETOOTH", adapter != null && adapter.isEnabled() ? "On" : "Off"),
                new SettingValue("STATUS", bluetoothStatus)};
    }

    private boolean isBluetoothEnabled() {
        BluetoothManager manager = activity.getSystemService(BluetoothManager.class);
        BluetoothAdapter adapter = manager == null ? null : manager.getAdapter();
        return adapter != null && adapter.isEnabled();
    }

    @SuppressWarnings("deprecation")
    private void toggleBluetooth() {
        if (android.os.Build.VERSION.SDK_INT >= 31
                && activity.checkSelfPermission(android.Manifest.permission.BLUETOOTH_CONNECT)
                != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            // The embedded R1 image owns this grant. Never prompt the owner.
            bluetoothStatus = "System grant unavailable";
            invalidate();
            return;
        }
        BluetoothManager manager = activity.getSystemService(BluetoothManager.class);
        BluetoothAdapter adapter = manager == null ? null : manager.getAdapter();
        if (adapter == null) {
            bluetoothStatus = "Adapter unavailable";
            invalidate();
            return;
        }
        try {
            boolean enabling = !adapter.isEnabled();
            boolean accepted = enabling ? adapter.enable() : adapter.disable();
            bluetoothStatus = accepted
                    ? (enabling ? "Turning on…" : "Turning off…")
                    : "System rejected request";
        } catch (SecurityException denied) {
            bluetoothStatus = "System permission unavailable";
        }
        invalidate();
        // MediaTek moves through BLE_TURNING_ON/OFF before the final adapter
        // state. The broadcast is authoritative; these redraws also cover a
        // missed transition without pretending the 500 ms state is final.
        postDelayed(this::invalidate, 500L);
        postDelayed(this::invalidate, 1_500L);
        postDelayed(this::invalidate, 3_000L);
    }

    static String bluetoothStateLabel(int state) {
        return switch (state) {
            case BluetoothAdapter.STATE_ON -> "Enabled";
            case BluetoothAdapter.STATE_OFF -> "Disabled";
            case BluetoothAdapter.STATE_TURNING_ON -> "Turning on…";
            case BluetoothAdapter.STATE_TURNING_OFF -> "Turning off…";
            default -> "State unavailable";
        };
    }

    private SettingValue[] sound() {
        AudioManager audio = activity.getSystemService(AudioManager.class);
        int current = audio == null ? 0 : audio.getStreamVolume(AudioManager.STREAM_MUSIC);
        int max = audio == null ? 0 : audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
        int percent = max == 0 ? 0 : Math.round(current * 100f / max);
        return new SettingValue[]{new SettingValue("VOLUME", percent + "%")};
    }

    private SettingValue[] display() {
        int brightness = Settings.System.getInt(activity.getContentResolver(),
                Settings.System.SCREEN_BRIGHTNESS, 0);
        return new SettingValue[]{
                new SettingValue("BRIGHTNESS", Math.round(brightness * 100f / 255f) + "%"),
                new SettingValue("SCREEN SLEEP", "Manual while open")};
    }

    private void button(Canvas canvas, String label, float left, float top, float right) {
        paint.setColor(0xff1c2d37);
        paint.setStyle(Paint.Style.FILL);
        canvas.drawRoundRect(left, top, right, top + 72f, 20f, 20f, paint);
        ReSonoTheme.text(canvas, paint, label, (left + right) / 2f, top + 48f, 28f,
                ReSonoTheme.CYAN, Paint.Align.CENTER, true);
    }

    private void adjustVolume(boolean increase) {
        AudioManager audio = activity.getSystemService(AudioManager.class);
        if (audio != null) audio.adjustStreamVolume(AudioManager.STREAM_MUSIC,
                increase ? AudioManager.ADJUST_RAISE : AudioManager.ADJUST_LOWER, 0);
        invalidate();
    }

    private void adjustBrightness(boolean increase) {
        int current = Settings.System.getInt(activity.getContentResolver(),
                Settings.System.SCREEN_BRIGHTNESS, 128);
        int next = adjustedBrightness(current, increase);
        try {
            Settings.System.putInt(activity.getContentResolver(),
                    Settings.System.SCREEN_BRIGHTNESS_MODE,
                    Settings.System.SCREEN_BRIGHTNESS_MODE_MANUAL);
            if (Settings.System.putInt(activity.getContentResolver(),
                    Settings.System.SCREEN_BRIGHTNESS, next)) {
                WindowManager.LayoutParams params = activity.getWindow().getAttributes();
                params.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE;
                activity.getWindow().setAttributes(params);
            }
        } catch (SecurityException ignored) {
            // The standalone system image owns the privileged Settings grant.
            // Keep the displayed value authoritative if that grant is absent.
        }
        invalidate();
    }

    static int adjustedBrightness(int current, boolean increase) {
        int bounded = Math.max(13, Math.min(255, current));
        return Math.max(13, Math.min(255, bounded + (increase ? 26 : -26)));
    }

    private void selectNetwork(WifiNetworkScanner.Network network) {
        if (network.connected()) return;
        if (!network.secured()) {
            connect(network.ssid(), null);
            return;
        }
        EditText password = new EditText(activity);
        password.setSingleLine(true);
        password.setHint("Network password");
        password.setTextColor(ReSonoTheme.INK);
        password.setHintTextColor(ReSonoTheme.MUTED);
        password.setTextSize(20f);
        password.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        password.setPadding(24, 18, 24, 18);
        LinearLayout sheet = new LinearLayout(activity);
        sheet.setOrientation(LinearLayout.VERTICAL);
        sheet.setPadding(28, 24, 28, 12);
        TextView title = new TextView(activity);
        title.setText(network.ssid());
        title.setTextColor(ReSonoTheme.INK);
        title.setTextSize(28f);
        title.setGravity(Gravity.START);
        sheet.addView(title);
        sheet.addView(password, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 76));
        AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle("Connect to Wi-Fi")
                .setView(sheet)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Connect", (ignored, which) ->
                        connect(network.ssid(), password.getText().toString()))
                .create();
        dialog.setOnShowListener(ignored -> {
            if (dialog.getWindow() != null) dialog.getWindow().setSoftInputMode(
                    WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE);
            password.requestFocus();
            password.postDelayed(() -> {
                InputMethodManager keyboard = activity.getSystemService(InputMethodManager.class);
                if (keyboard != null) keyboard.showSoftInput(password, InputMethodManager.SHOW_IMPLICIT);
            }, 160L);
        });
        dialog.show();
    }

    @SuppressWarnings("deprecation")
    private void connect(String ssid, String password) {
        WifiManager wifi = activity.getSystemService(WifiManager.class);
        if (wifi == null) { wifiScanState = "Wi-Fi unavailable"; invalidate(); return; }
        WifiConfiguration config = new WifiConfiguration();
        config.SSID = quote(ssid);
        if (password == null || password.isBlank()) config.allowedKeyManagement.set(WifiConfiguration.KeyMgmt.NONE);
        else config.preSharedKey = quote(password);
        try {
            int id = wifi.addNetwork(config);
            if (id < 0) { wifiScanState = "Could not save network"; invalidate(); return; }
            wifi.disconnect();
            wifi.enableNetwork(id, true);
            wifi.reconnect();
            wifiScanState = "Connecting to " + ssid + "…";
            postDelayed(wifiScanner::refresh, 1800L);
        } catch (SecurityException denied) {
            wifiScanState = "System Wi-Fi permission unavailable";
        }
        invalidate();
    }

    private static String quote(String value) { return '"' + value.replace("\"", "\\\"") + '"'; }

    @Override public boolean onTouchEvent(MotionEvent event) {
        if (event.getActionMasked() != MotionEvent.ACTION_UP) return true;
        float x = event.getX() * DESIGN_WIDTH / Math.max(1f, getWidth());
        float y = event.getY() * DESIGN_HEIGHT / Math.max(1f, getHeight());
        if (x > 400f && y < 76f) { close.run(); return true; }
        if (openPage != null && x < 90f && y < 82f) {
            openPage = null;
            invalidate();
            return true;
        }
        if (openPage == null) {
            int row = (int) ((y - ROW_TOP) / ROW_STEP);
            float within = (y - ROW_TOP) % ROW_STEP;
            if (row >= 0 && row < ROWS.size() && within <= 64f) {
                selected = row;
                openPage = ROWS.get(row);
                if ("Wi-Fi".equals(openPage)) wifiScanner.refresh();
                if ("Management".equals(openPage)) refreshManagement();
                invalidate();
            }
        } else if ("Wi-Fi".equals(openPage)) {
            float networkTop = 148f;
            int row = (int) ((y - networkTop) / 59f);
            float within = (y - networkTop) % 59f;
            if (y >= networkTop && row >= 0 && row < Math.min(6, wifiNetworks.size()) && within <= 52f) {
                selectNetwork(wifiNetworks.get(row));
            } else if (y >= 520f && y <= 620f) {
                wifiScanner.refresh();
            }
        } else if (y >= 482f && y <= 584f) {
            if ("Sound".equals(openPage)) {
                adjustVolume(x >= DESIGN_WIDTH / 2f);
            } else if ("Display".equals(openPage)) {
                adjustBrightness(x >= DESIGN_WIDTH / 2f);
            } else if ("Bluetooth".equals(openPage)) {
                toggleBluetooth();
            } else if ("About".equals(openPage)) {
                restart.run();
            } else if ("Management".equals(openPage)) {
                refreshManagement();
            } else {
                invalidate();
            }
        }
        return true;
    }

    @Override public boolean onInput(UiInputIntent intent) {
        if (intent == UiInputIntent.BACK) {
            if (openPage != null) { openPage = null; invalidate(); }
            else close.run();
            return true;
        }
        if (openPage == null && intent == UiInputIntent.PREVIOUS) {
            selected = Math.max(0, selected - 1); invalidate(); return true;
        }
        if (openPage == null && intent == UiInputIntent.NEXT) {
            selected = Math.min(ROWS.size() - 1, selected + 1); invalidate(); return true;
        }
        if (openPage == null && intent == UiInputIntent.ACTIVATE) {
            openPage = ROWS.get(selected);
            if ("Wi-Fi".equals(openPage)) wifiScanner.refresh();
            if ("Management".equals(openPage)) refreshManagement();
            invalidate(); return true;
        }
        if ("Wi-Fi".equals(openPage) && intent == UiInputIntent.ACTIVATE) {
            if (!wifiNetworks.isEmpty()) selectNetwork(wifiNetworks.get(0));
            return true;
        }
        if (SettingsInputPolicy.consumeWheelWithoutAdjustment(openPage, intent)) {
            // The R1 wheel stays navigation-only. Sound and Display changes
            // require their explicit on-screen buttons.
            return true;
        }
        if ("Bluetooth".equals(openPage) && intent == UiInputIntent.ACTIVATE) {
            toggleBluetooth();
            return true;
        }
        if ("About".equals(openPage) && intent == UiInputIntent.ACTIVATE) {
            restart.run();
            return true;
        }
        if ("Management".equals(openPage) && intent == UiInputIntent.ACTIVATE) {
            refreshManagement();
            return true;
        }
        return false;
    }

    @Override public void onWindowFocusChanged(boolean hasWindowFocus) {
        super.onWindowFocusChanged(hasWindowFocus);
        wifiScanner.onWindowFocusChanged(hasWindowFocus);
    }

    @Override protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        if (bluetoothReceiverRegistered) return;
        IntentFilter filter = new IntentFilter(BluetoothAdapter.ACTION_STATE_CHANGED);
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            activity.registerReceiver(bluetoothReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            activity.registerReceiver(bluetoothReceiver, filter);
        }
        bluetoothReceiverRegistered = true;
    }

    @Override protected void onDetachedFromWindow() {
        wifiScanner.close();
        if (bluetoothReceiverRegistered) {
            try { activity.unregisterReceiver(bluetoothReceiver); }
            catch (IllegalArgumentException ignored) { }
            bluetoothReceiverRegistered = false;
        }
        super.onDetachedFromWindow();
    }

    private record SettingValue(String label, String value) { }
}
