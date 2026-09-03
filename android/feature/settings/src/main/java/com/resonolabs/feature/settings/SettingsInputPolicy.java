package com.resonolabs.feature.settings;

import com.resonolabs.ui.input.UiInputIntent;

/** Input rules that keep the R1 wheel separate from device-setting mutations. */
final class SettingsInputPolicy {
    static final int NO_WIFI_ACTION_SELECTED = -1;

    enum WifiAction { NONE, CONNECT_FIRST_NETWORK, OPEN_SIGN_IN, SCAN_AGAIN }

    private SettingsInputPolicy() { }

    static boolean consumeWheelWithoutAdjustment(String page, UiInputIntent intent) {
        if (intent != UiInputIntent.PREVIOUS && intent != UiInputIntent.NEXT) return false;
        return "Sound".equals(page) || "Display".equals(page);
    }

    static int wifiActionCount(boolean captivePortal) {
        return captivePortal ? 2 : 1;
    }

    static WifiAction wifiActionAt(boolean captivePortal, int index) {
        if (captivePortal) {
            if (index == 0) return WifiAction.OPEN_SIGN_IN;
            if (index == 1) return WifiAction.SCAN_AGAIN;
        } else if (index == 0) {
            return WifiAction.SCAN_AGAIN;
        }
        return WifiAction.NONE;
    }

    static int wifiSelectionAfterWheel(
            boolean captivePortal, int selection, UiInputIntent intent) {
        if (!captivePortal) return NO_WIFI_ACTION_SELECTED;
        int lastAction = wifiActionCount(captivePortal) - 1;
        if (intent == UiInputIntent.NEXT) {
            return selection == NO_WIFI_ACTION_SELECTED ? 0 : Math.min(lastAction, selection + 1);
        }
        if (intent == UiInputIntent.PREVIOUS) {
            return selection == NO_WIFI_ACTION_SELECTED ? lastAction : Math.max(0, selection - 1);
        }
        return selection;
    }

    static WifiAction wifiActivateAction(
            boolean captivePortal, boolean hasNetworks, int selection) {
        if (captivePortal && selection != NO_WIFI_ACTION_SELECTED) {
            return wifiActionAt(true, selection);
        }
        if (hasNetworks) return WifiAction.CONNECT_FIRST_NETWORK;
        return captivePortal ? WifiAction.OPEN_SIGN_IN : WifiAction.NONE;
    }

    static WifiAction wifiTouchAction(boolean captivePortal, float x, float y) {
        if (!captivePortal) {
            return y >= 520f && y <= 620f ? WifiAction.SCAN_AGAIN : WifiAction.NONE;
        }
        if (y < 532f || y > 604f) return WifiAction.NONE;
        if (x >= 20f && x <= 232f) return WifiAction.OPEN_SIGN_IN;
        if (x >= 248f && x <= 460f) return WifiAction.SCAN_AGAIN;
        return WifiAction.NONE;
    }
}
