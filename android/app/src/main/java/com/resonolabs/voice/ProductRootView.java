package com.resonolabs.voice;

import android.app.Activity;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.widget.FrameLayout;

import com.resonolabs.feature.voice.VoicePageView;
import com.resonolabs.feature.settings.SettingsPanelView;
import com.resonolabs.feature.settings.ManagementPairingSource;
import com.resonolabs.ui.input.HardwareInputRouter;
import com.resonolabs.ui.input.UiInputIntent;

final class ProductRootView extends FrameLayout {
    private final VoicePageView voice;
    private final SettingsPanelView settings;
    private boolean settingsOpen;

    ProductRootView(Activity activity, Runnable restart, ManagementPairingSource managementPairing) {
        super(activity);
        voice = new VoicePageView(activity, this::openSettings);
        settings = new SettingsPanelView(activity, this::closeSettings, restart, managementPairing);
        settings.setVisibility(GONE);
        addView(voice, match());
        addView(settings, match());
        setFocusable(true);
        setFocusableInTouchMode(true);
        setContentDescription("ReSono R1 HOME");
    }

    private LayoutParams match() {
        return new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT);
    }

    private void openSettings() {
        settingsOpen = true;
        voice.setVisibility(GONE);
        settings.setVisibility(VISIBLE);
        settings.requestFocus();
    }

    private void closeSettings() {
        settingsOpen = false;
        settings.setVisibility(GONE);
        voice.setVisibility(VISIBLE);
        voice.requestFocus();
    }

    boolean onHardwareKey(KeyEvent event) {
        UiInputIntent intent = HardwareInputRouter.keyIntent(event.getKeyCode());
        if (intent == null) return false;
        if (event.getAction() == KeyEvent.ACTION_DOWN) dispatch(intent);
        return true;
    }

    boolean onHardwareMotion(MotionEvent event) {
        UiInputIntent intent = HardwareInputRouter.motionIntent(event);
        if (intent == null) return false;
        dispatch(intent);
        return true;
    }

    boolean navigateBack() {
        if (settingsOpen) return settings.onInput(UiInputIntent.BACK);
        return true;
    }

    private void dispatch(UiInputIntent intent) {
        if (settingsOpen) settings.onInput(intent);
        else voice.onInput(intent);
    }

    void close() {
        voice.close();
    }
}
