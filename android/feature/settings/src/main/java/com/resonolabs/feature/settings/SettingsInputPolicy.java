package com.resonolabs.feature.settings;

import com.resonolabs.ui.input.UiInputIntent;

/** Input rules that keep the R1 wheel separate from device-setting mutations. */
final class SettingsInputPolicy {
    private SettingsInputPolicy() { }

    static boolean consumeWheelWithoutAdjustment(String page, UiInputIntent intent) {
        if (intent != UiInputIntent.PREVIOUS && intent != UiInputIntent.NEXT) return false;
        return "Sound".equals(page) || "Display".equals(page);
    }
}
