package com.resonolabs.feature.settings;

import android.app.Activity;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.content.ActivityNotFoundException;
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
import com.resonolabs.runtime.host.ManagementOpenAiSource;
import com.resonolabs.runtime.host.ManagementOpenAiState;

import java.util.List;

/** Large-format settings designed for direct use on the 480x640 R1 display. */
public final class SettingsPanelView extends View implements UiInputTarget {
    private static final float DESIGN_WIDTH = 480f;
    private static final float DESIGN_HEIGHT = 640f;
    private static final float ROW_TOP = 88f;
    private static final float ROW_STEP = 66f;
    private static final float AI_PROVIDER_TOP = 100f;
    private static final float AI_PROVIDER_BOTTOM = 180f;
    private static final float AI_ACCESS_TOP = 196f;
    private static final float AI_ACCESS_BOTTOM = 275f;
    private static final float AI_VOICE_MODEL_TOP = 292f;
    private static final float AI_VOICE_MODEL_BOTTOM = 370f;
    private static final float AI_TEXT_MODEL_TOP = 386f;
    private static final float AI_TEXT_MODEL_BOTTOM = 464f;
    private static final float AI_REASONING_TOP = 480f;
    private static final float AI_REASONING_BOTTOM = 540f;
    private static final float AI_REFRESH_TOP = 556f;
    private static final List<String> ROWS = List.of(
            "Wi-Fi", "Bluetooth", "Management", "AI", "Creations", "Sound", "Display", "About");

    private final Activity activity;
    private final Runnable close;
    private final Runnable restart;
    private final Runnable openCreationImport;
    private final ManagementPairingSource managementPairing;
    private final ManagementOpenAiSource openAiSource;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final WifiNetworkScanner wifiScanner;
    private final WifiCaptivePortalMonitor wifiPortalMonitor;
    private int selected;
    private String openPage;
    private String wifiScanState = "Tap refresh to scan";
    private List<WifiNetworkScanner.Network> wifiNetworks = List.of();
    private boolean wifiCaptivePortal;
    private int wifiActionSelected = SettingsInputPolicy.NO_WIFI_ACTION_SELECTED;
    private String wifiActionStatus = "";
    private String bluetoothStatus = "Ready";
    private ManagementPairingState managementState = ManagementPairingState.loading();
    private ManagementOpenAiState openAiState = ManagementOpenAiState.loading();
    private String openAiMessage = "";
    private String draftProvider = "openai";
    private String draftAccessPath = "platform";
    private String draftTextModel;
    private String draftRealtimeModel;
    private String draftReasoning = "none";
    private boolean aiDraftDirty;
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
            Runnable openCreationImport,
            ManagementPairingSource managementPairing,
            ManagementOpenAiSource openAiSource) {
        super(activity);
        this.activity = activity;
        this.close = close;
        this.restart = restart;
        this.openCreationImport = openCreationImport;
        this.managementPairing = managementPairing;
        this.openAiSource = openAiSource;
        this.wifiScanner = new WifiNetworkScanner(activity, (state, networks) -> {
            wifiScanState = state;
            wifiNetworks = List.copyOf(networks);
            invalidate();
        });
        this.wifiPortalMonitor = new WifiCaptivePortalMonitor(activity, active -> {
            if (wifiCaptivePortal != active) {
                wifiActionSelected = SettingsInputPolicy.NO_WIFI_ACTION_SELECTED;
            }
            wifiCaptivePortal = active;
            if (!active) wifiActionStatus = "";
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
            canvas.drawRoundRect(20f, top, 460f, top + 58f, 17f, 17f, paint);
            if (i == selected) {
                paint.setColor(ReSonoTheme.VIOLET);
                // Fixed-size cursor only: changing the entire row luminance can
                // drive Rabbit's MediaTek AAL/PQ backlight compensation.
                canvas.drawRoundRect(20f, top + 7f, 25f, top + 51f, 3f, 3f, paint);
            }
            ReSonoTheme.text(canvas, paint, ROWS.get(i), 46f, top + 39f, 26f,
                ReSonoTheme.INK, Paint.Align.LEFT, true);
            ReSonoTheme.text(canvas, paint, "›", 430f, top + 40f, 34f,
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
        if ("AI".equals(openPage)) {
            drawAiPage(canvas);
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
        } else if ("AI".equals(openPage)) {
            button(canvas, "REFRESH", 20f, 494f, 460f);
        } else {
            button(canvas, "REFRESH", 20f, 494f, 460f);
        }
    }

    private void drawWifiPage(Canvas canvas) {
        SettingValue[] values = network();
        String internet = wifiCaptivePortal ? "Sign-in required" : values[1].value;
        ReSonoTheme.text(canvas, paint, values[0].value + "  •  " + internet,
                24f, 91f, 20f, ReSonoTheme.MUTED, Paint.Align.LEFT, true);
        String wifiHint;
        if (!wifiActionStatus.isBlank()) {
            wifiHint = wifiActionStatus;
        } else if (wifiCaptivePortal) {
            wifiHint = "Sign in via system Wi-Fi";
        } else {
            wifiHint = wifiNetworks.isEmpty() ? wifiScanState : "Tap a network to connect";
        }
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
            String detail = wifiNetworkDetail(network.connected(), network.secured(), wifiCaptivePortal);
            ReSonoTheme.text(canvas, paint, detail, 425f, top + 32f, 14f,
                    network.connected() ? 0xff57d6a7 : ReSonoTheme.MUTED, Paint.Align.RIGHT, true);
            for (int bar = 0; bar < 4; bar++) {
                paint.setColor(bar < network.signalLevel() ? ReSonoTheme.CYAN : 0xff3d3a4d);
                canvas.drawRoundRect(432f + bar * 6f, top + 39f - bar * 4f,
                        436f + bar * 6f, top + 47f, 2f, 2f, paint);
            }
            top += 59f;
        }
        if (wifiCaptivePortal) {
            wifiActionButton(canvas, "WI-FI SETTINGS", 20f, 232f, wifiActionSelected == 0);
            wifiActionButton(canvas, "SCAN AGAIN", 248f, 460f, wifiActionSelected == 1);
        } else {
            button(canvas, "SCAN AGAIN", 20f, 532f, 460f);
        }
    }

    static String wifiNetworkDetail(boolean connected, boolean secured, boolean captivePortal) {
        if (connected) return captivePortal ? "NEEDS SIGN-IN" : "CONNECTED";
        return secured ? "SECURE" : "OPEN";
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

    private void drawAiPage(Canvas canvas) {
        paint.setColor(ReSonoTheme.PANEL_RAISED);
        paint.setStyle(Paint.Style.FILL);
        canvas.drawRoundRect(20f, 100f, 460f, 180f, 20f, 20f, paint);
        ReSonoTheme.text(canvas, paint, "PROVIDER", 44f, 138f, 19f,
                ReSonoTheme.MUTED, Paint.Align.LEFT, true);
        ReSonoTheme.text(canvas, paint, providerLabel(draftProvider), 44f, 170f, 35f,
                resonoAIColor(openAiState.connected() || openAiState.platformConnected() || openAiState.subscriptionConnected()),
                Paint.Align.LEFT, true);
        selectionArrow(canvas, 149f);

        paint.setColor(ReSonoTheme.PANEL_RAISED);
        canvas.drawRoundRect(20f, 196f, 460f, 275f, 20f, 20f, paint);
        ReSonoTheme.text(canvas, paint, "ACCESS PATH", 44f, 233f, 19f,
                resonoAIColor(openAiState.connected()), Paint.Align.LEFT, true);
        ReSonoTheme.text(canvas, paint, draftAccessPath, 44f, 265f, 32f,
                ReSonoTheme.INK, Paint.Align.LEFT, true);
        selectionArrow(canvas, 245f);

        paint.setColor(ReSonoTheme.PANEL_RAISED);
        canvas.drawRoundRect(20f, 292f, 460f, 370f, 20f, 20f, paint);
        ReSonoTheme.text(canvas, paint, "VOICE MODEL", 44f, 329f, 19f,
                ReSonoTheme.MUTED, Paint.Align.LEFT, true);
        ReSonoTheme.text(canvas, paint,
                draftRealtimeModel == null || draftRealtimeModel.isBlank()
                        ? "—"
                        : draftRealtimeModel,
                44f, 361f, 32f, ReSonoTheme.INK, Paint.Align.LEFT, true);
        selectionArrow(canvas, 341f);

        paint.setColor(ReSonoTheme.PANEL_RAISED);
        canvas.drawRoundRect(20f, 386f, 460f, 464f, 20f, 20f, paint);
        ReSonoTheme.text(canvas, paint, "TEXT MODEL", 44f, 423f, 19f,
                resonoAIColor(openAiState.selectedTextModel() != null),
                Paint.Align.LEFT, true);
        ReSonoTheme.text(canvas, paint,
                draftTextModel == null || draftTextModel.isBlank()
                        ? "—"
                        : draftTextModel,
                44f, 455f, 32f, ReSonoTheme.INK, Paint.Align.LEFT, true);
        selectionArrow(canvas, 435f);

        paint.setColor(ReSonoTheme.PANEL_RAISED);
        canvas.drawRoundRect(20f, 480f, 460f, 540f, 20f, 20f, paint);
        ReSonoTheme.text(canvas, paint, "REASONING", 44f, 517f, 19f,
                ReSonoTheme.MUTED, Paint.Align.LEFT, true);
        ReSonoTheme.text(canvas, paint, draftReasoning,
                44f, 549f, 32f, resonoAIColor(), Paint.Align.LEFT, true);
        selectionArrow(canvas, 515f);
        if (openAiState.fallbackMessage() != null) {
            paint.setColor(ReSonoTheme.PANEL);
            canvas.drawRoundRect(20f, 560f, 460f, 602f, 18f, 18f, paint);
            ReSonoTheme.text(canvas, paint, openAiState.fallbackMessage(), 44f, 594f, 16f,
                    ReSonoTheme.MUTED, Paint.Align.LEFT, true);
        }
        ReSonoTheme.text(canvas, paint, openAiMessage, 44f, 621f, 16f,
                ReSonoTheme.MUTED, Paint.Align.LEFT, true);
        button(canvas, "SAVE", 20f, AI_REFRESH_TOP, 460f);
    }

    private void selectionArrow(Canvas canvas, float centerY) {
        ReSonoTheme.text(canvas, paint, "›", 428f, centerY + 12f, 38f,
                ReSonoTheme.CYAN, Paint.Align.CENTER, false);
    }

    private int resonoAIColor(boolean active) {
        return active ? ReSonoTheme.CYAN : ReSonoTheme.MUTED;
    }

    private int resonoAIColor() {
        return openAiState.error() ? 0xffe2a1a1 : ReSonoTheme.INK;
    }

    private void refreshOpenAi() {
        openAiMessage = "Refreshing AI settings…";
        openAiState = ManagementOpenAiState.loading();
        invalidate();
        openAiSource.refresh(activity, state -> {
            openAiState = state;
            syncAiDraft(state);
            openAiMessage = state.fallbackMessage() == null
                    ? "" : state.fallbackMessage();
            invalidate();
        });
    }

    private void syncAiDraft(ManagementOpenAiState state) {
        draftProvider = state.provider();
        draftAccessPath = state.accessPath();
        draftTextModel = state.selectedTextModel();
        draftRealtimeModel = state.selectedRealtimeModel();
        draftReasoning = state.reasoningEffort() == null ? "none" : state.reasoningEffort();
        aiDraftDirty = false;
    }

    private String providerLabel(String provider) {
        String[] ids = openAiState.providerIds();
        String[] names = openAiState.providerNames();
        for (int i = 0; i < ids.length && i < names.length; i++) {
            if (ids[i].equals(provider)) return names[i];
        }
        return provider;
    }

    static String nextOption(String current, String[] options) {
        if (options == null || options.length == 0) return current;
        for (int i = 0; i < options.length; i++) {
            if (options[i].equals(current)) return options[(i + 1) % options.length];
        }
        return options[0];
    }

    private void cycleProvider() {
        draftProvider = nextOption(draftProvider, openAiState.providerIds());
        markAiDraftChanged();
    }

    private void cycleAccessPath() {
        if (!openAiState.platformConnected() && !openAiState.subscriptionConnected()) {
            openAiMessage = "Connect OpenAI in management first.";
            invalidate();
            return;
        }
        if (openAiState.platformConnected() && openAiState.subscriptionConnected()) {
            draftAccessPath = nextOption(draftAccessPath, new String[]{"platform", "subscription"});
        } else {
            draftAccessPath = openAiState.platformConnected() ? "platform" : "subscription";
        }
        markAiDraftChanged();
    }

    private void cycleRealtimeModel() {
        draftRealtimeModel = nextOption(draftRealtimeModel, openAiState.realtimeModels());
        markAiDraftChanged();
    }

    private void cycleTextModel() {
        draftTextModel = nextOption(draftTextModel, openAiState.textModels());
        markAiDraftChanged();
    }

    private void cycleReasoning() {
        draftReasoning = nextOption(draftReasoning, new String[]{"none", "low", "medium", "high"});
        markAiDraftChanged();
    }

    private void markAiDraftChanged() {
        aiDraftDirty = true;
        openAiMessage = "Unsaved changes";
        invalidate();
    }

    private void saveAiDraft() {
        if (!aiDraftDirty) {
            openAiMessage = "Settings are already saved.";
            invalidate();
            return;
        }
        openAiMessage = "Saving AI settings…";
        invalidate();
        openAiSource.setProvider(activity, draftProvider, providerState -> {
            if (providerState.error()) { finishAiSave(providerState); return; }
            openAiSource.setAccessPath(activity, draftAccessPath, accessState -> {
                if (accessState.error()) { finishAiSave(accessState); return; }
                openAiSource.setModels(
                        activity,
                        draftTextModel,
                        draftRealtimeModel,
                        draftReasoning,
                        this::finishAiSave);
            });
        });
    }

    private void finishAiSave(ManagementOpenAiState state) {
        openAiState = state;
        if (state.error()) {
            openAiMessage = state.fallbackMessage() == null ? "AI settings were not saved." : state.fallbackMessage();
        } else {
            syncAiDraft(state);
            openAiMessage = "AI settings saved.";
        }
        invalidate();
    }

    private void pickProvider() {
        String[] ids = openAiState.providerIds();
        if (ids.length == 0) {
            openAiMessage = "No providers available.";
            invalidate();
            return;
        }
        int checked = 0;
        String[] labels = new String[ids.length];
        for (int i = 0; i < ids.length; i++) {
            if (ids[i].equals(openAiState.provider())) checked = i;
            labels[i] = openAiState.providerNames()[i] + " (" + ids[i] + ")";
        }
        new AlertDialog.Builder(activity)
                .setTitle("Select provider")
                .setSingleChoiceItems(labels, checked, (dialog, which) -> {
                    dialog.dismiss();
                    setProvider(ids[which]);
                })
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void setProvider(String provider) {
        openAiMessage = "Saving provider…";
        invalidate();
        openAiSource.setProvider(activity, provider, state -> {
            openAiState = state;
            openAiMessage = "Provider set.";
            invalidate();
        });
    }

    private void pickAccessPath() {
        if (!openAiState.platformConnected() && !openAiState.subscriptionConnected()) {
            openAiMessage = "Connect OpenAI first.";
            invalidate();
            return;
        }
        String[] options = new String[2];
        String[] optionValues = new String[2];
        int total = 0;
        if (openAiState.platformConnected()) {
            optionValues[total] = "platform";
            options[total] = "OpenAI Platform API";
            total++;
        }
        if (openAiState.subscriptionConnected()) {
            optionValues[total] = "subscription";
            options[total] = "ChatGPT / Codex";
            total++;
        }
        String[] visible = new String[total];
        String[] values = new String[total];
        for (int i = 0; i < total; i++) {
            visible[i] = options[i];
            values[i] = optionValues[i];
        }
        if (total == 0) {
            openAiMessage = "No access path is available.";
            invalidate();
            return;
        }
        int checked = 0;
        for (int i = 0; i < total; i++) {
            if (values[i].equals(openAiState.accessPath())) checked = i;
        }
        new AlertDialog.Builder(activity)
                .setTitle("Use for text and Voice")
                .setSingleChoiceItems(visible, checked, (dialog, which) -> {
                    dialog.dismiss();
                    setAccessPath(values[which]);
                })
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void setAccessPath(String accessPath) {
        openAiMessage = "Saving connection type…";
        invalidate();
        openAiSource.setAccessPath(activity, accessPath, state -> {
            openAiState = state;
            openAiMessage = "Connection updated.";
            invalidate();
        });
    }

    private void pickRealtimeModel() {
        String[] options = openAiState.realtimeModels();
        if (options.length == 0) {
            openAiMessage = "Refresh after connecting to OpenAI.";
            invalidate();
            return;
        }
        showSingleChoice("Select voice model", options, openAiState.selectedRealtimeModel(), value ->
                setModels(openAiState.selectedTextModel(), value, openAiState.reasoningEffort())
        );
    }

    private void pickTextModel() {
        String[] options = openAiState.textModels();
        if (options.length == 0) {
            openAiMessage = "Refresh after connecting to OpenAI.";
            invalidate();
            return;
        }
        showSingleChoice("Select text model", options, openAiState.selectedTextModel(), value ->
                setModels(value, openAiState.selectedRealtimeModel(), openAiState.reasoningEffort())
        );
    }

    private void pickReasoning() {
        String[] options = new String[]{"none", "low", "medium", "high"};
        showSingleChoice("Reasoning", options, openAiState.reasoningEffort(), value ->
                setModels(openAiState.selectedTextModel(), openAiState.selectedRealtimeModel(), value)
        );
    }

    private void showSingleChoice(String title, String[] values, String checkedValue, ChoiceHandler handler) {
        int checked = 0;
        for (int i = 0; i < values.length; i++) {
            if (values[i].equals(checkedValue)) checked = i;
        }
        new AlertDialog.Builder(activity)
                .setTitle(title)
                .setSingleChoiceItems(values, checked, (dialog, which) -> {
                    dialog.dismiss();
                    handler.onChoice(values[which]);
                })
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void setModels(String textModel, String realtimeModel, String reasoningEffort) {
        openAiMessage = "Saving models…";
        openAiSource.setModels(activity, textModel, realtimeModel, reasoningEffort, state -> {
            openAiState = state;
            openAiMessage = "Model selection saved.";
            invalidate();
        });
    }

    private void connectOpenAiFromSettings() {
        EditText key = new EditText(activity);
        key.setSingleLine(true);
        key.setHint("Platform API key");
        key.setTextColor(ReSonoTheme.INK);
        key.setHintTextColor(ReSonoTheme.MUTED);
        key.setTextSize(20f);
        key.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        key.setPadding(24, 18, 24, 18);
        LinearLayout sheet = new LinearLayout(activity);
        sheet.setOrientation(LinearLayout.VERTICAL);
        sheet.setPadding(28, 24, 28, 12);
        TextView title = new TextView(activity);
        title.setText("Connect OpenAI Platform");
        title.setTextColor(ReSonoTheme.INK);
        title.setTextSize(24f);
        title.setGravity(Gravity.START);
        sheet.addView(title);
        sheet.addView(key, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 76));
        AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle("OpenAI Platform Key")
                .setView(sheet)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Save", (ignored, which) -> {
                    String value = key.getText().toString();
                    if (value == null || value.isBlank()) {
                        openAiMessage = "Key cannot be empty.";
                        invalidate();
                        return;
                    }
                    openAiMessage = "Saving key…";
                    invalidate();
                    openAiSource.connect(activity, value.trim(), state -> {
                        openAiState = state;
                        openAiMessage = "OpenAI key connected.";
                        invalidate();
                    });
                })
                .create();
        dialog.setOnShowListener(ignored -> {
            if (dialog.getWindow() != null) dialog.getWindow().setSoftInputMode(
                    WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE);
            key.requestFocus();
            key.postDelayed(() -> {
                InputMethodManager keyboard = activity.getSystemService(InputMethodManager.class);
                if (keyboard != null) keyboard.showSoftInput(key, InputMethodManager.SHOW_IMPLICIT);
            }, 160L);
        });
        dialog.show();
    }

    @FunctionalInterface
    private interface ChoiceHandler {
        void onChoice(String value);
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
                    new SettingValue("DEVICE", "Rabbit R1"),
                    new SettingValue("VERSION", appVersion()),
                    new SettingValue("ANDROID", android.os.Build.VERSION.RELEASE)};
        };
    }

    private String appVersion() {
        try {
            String version = activity.getPackageManager()
                    .getPackageInfo(activity.getPackageName(), 0).versionName;
            return version == null || version.isBlank() ? "Unavailable" : version.replace('-', ' ');
        } catch (android.content.pm.PackageManager.NameNotFoundException unavailable) {
            return "Unavailable";
        }
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

    private void wifiActionButton(
            Canvas canvas, String label, float left, float right, boolean selected) {
        button(canvas, label, left, 532f, right);
        if (!selected) return;
        paint.setColor(ReSonoTheme.VIOLET);
        paint.setStyle(Paint.Style.FILL);
        canvas.drawRoundRect(left, 546f, left + 5f, 590f, 3f, 3f, paint);
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

    private void performWifiAction(SettingsInputPolicy.WifiAction action) {
        if (action == SettingsInputPolicy.WifiAction.CONNECT_FIRST_NETWORK) {
            if (!wifiNetworks.isEmpty()) selectNetwork(wifiNetworks.get(0));
        } else if (action == SettingsInputPolicy.WifiAction.OPEN_SIGN_IN) {
            openWifiSignIn();
        } else if (action == SettingsInputPolicy.WifiAction.SCAN_AGAIN) {
            wifiActionStatus = "";
            wifiScanner.refresh();
        }
    }

    private void openWifiSignIn() {
        if (!wifiCaptivePortal) return;
        try {
            activity.startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS));
            wifiActionStatus = "Opened system Wi-Fi settings";
        } catch (ActivityNotFoundException missing) {
            wifiActionStatus = "Wi-Fi settings unavailable";
        } catch (SecurityException denied) {
            wifiActionStatus = "System denied Wi-Fi settings";
        } catch (RuntimeException failed) {
            wifiActionStatus = "Could not open Wi-Fi settings";
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
            if (row >= 0 && row < ROWS.size() && within <= 58f) {
                selected = row;
                activateSelectedRow();
            }
        } else if ("Wi-Fi".equals(openPage)) {
            float networkTop = 148f;
            int row = (int) ((y - networkTop) / 59f);
            float within = (y - networkTop) % 59f;
            if (y >= networkTop && row >= 0 && row < Math.min(6, wifiNetworks.size()) && within <= 52f) {
                selectNetwork(wifiNetworks.get(row));
            } else {
                SettingsInputPolicy.WifiAction action = SettingsInputPolicy.wifiTouchAction(
                        wifiCaptivePortal, x, y);
                if (action != SettingsInputPolicy.WifiAction.NONE) {
                    if (wifiCaptivePortal) {
                        wifiActionSelected = action == SettingsInputPolicy.WifiAction.OPEN_SIGN_IN
                                ? 0 : 1;
                    }
                    performWifiAction(action);
                }
            }
        } else if ("AI".equals(openPage)) {
            boolean arrow = x >= 390f && x <= 460f;
            if (arrow && y >= AI_PROVIDER_TOP && y <= AI_PROVIDER_BOTTOM) {
                cycleProvider();
            } else if (arrow && y >= AI_ACCESS_TOP && y <= AI_ACCESS_BOTTOM) {
                cycleAccessPath();
            } else if (arrow && y >= AI_VOICE_MODEL_TOP && y <= AI_VOICE_MODEL_BOTTOM) {
                cycleRealtimeModel();
            } else if (arrow && y >= AI_TEXT_MODEL_TOP && y <= AI_TEXT_MODEL_BOTTOM) {
                cycleTextModel();
            } else if (arrow && y >= AI_REASONING_TOP && y <= AI_REASONING_BOTTOM) {
                cycleReasoning();
            } else if (y >= AI_REFRESH_TOP && y <= AI_REFRESH_TOP + 72f) {
                saveAiDraft();
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
            activateSelectedRow(); return true;
        }
        if ("Wi-Fi".equals(openPage) && wifiCaptivePortal
                && (intent == UiInputIntent.PREVIOUS || intent == UiInputIntent.NEXT)) {
            wifiActionSelected = SettingsInputPolicy.wifiSelectionAfterWheel(
                    true, wifiActionSelected, intent);
            invalidate();
            return true;
        }
        if ("Wi-Fi".equals(openPage) && intent == UiInputIntent.ACTIVATE) {
            performWifiAction(SettingsInputPolicy.wifiActivateAction(
                    wifiCaptivePortal, !wifiNetworks.isEmpty(), wifiActionSelected));
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
        if ("AI".equals(openPage) && intent == UiInputIntent.ACTIVATE) {
            saveAiDraft();
            return true;
        }
        return false;
    }

    private void activateSelectedRow() {
        String page = ROWS.get(selected);
        if ("Creations".equals(page)) {
            openCreationImport.run();
            return;
        }
        openPage = page;
        if ("Wi-Fi".equals(openPage)) {
            wifiActionSelected = SettingsInputPolicy.NO_WIFI_ACTION_SELECTED;
            wifiScanner.refresh();
        }
        if ("Management".equals(openPage)) refreshManagement();
        if ("AI".equals(openPage)) refreshOpenAi();
        invalidate();
    }

    @Override public void onWindowFocusChanged(boolean hasWindowFocus) {
        super.onWindowFocusChanged(hasWindowFocus);
        wifiScanner.onWindowFocusChanged(hasWindowFocus);
    }

    @Override protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        wifiPortalMonitor.start();
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
        wifiPortalMonitor.close();
        if (bluetoothReceiverRegistered) {
            try { activity.unregisterReceiver(bluetoothReceiver); }
            catch (IllegalArgumentException ignored) { }
            bluetoothReceiverRegistered = false;
        }
        super.onDetachedFromWindow();
    }

    private record SettingValue(String label, String value) { }
}
