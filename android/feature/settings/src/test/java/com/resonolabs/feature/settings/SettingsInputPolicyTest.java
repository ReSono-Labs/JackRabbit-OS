package com.resonolabs.feature.settings;

import com.resonolabs.ui.input.UiInputIntent;

import org.junit.Test;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import android.bluetooth.BluetoothAdapter;

public final class SettingsInputPolicyTest {
    @Test public void bluetoothTransitionsRemainVisibleUntilFinalState() {
        assertEquals("Turning on…", SettingsPanelView.bluetoothStateLabel(
                BluetoothAdapter.STATE_TURNING_ON));
        assertEquals("Enabled", SettingsPanelView.bluetoothStateLabel(BluetoothAdapter.STATE_ON));
        assertEquals("Disabled", SettingsPanelView.bluetoothStateLabel(BluetoothAdapter.STATE_OFF));
    }

    @Test public void displayWheelNeverChangesBacklight() {
        assertTrue(SettingsInputPolicy.consumeWheelWithoutAdjustment(
                "Display", UiInputIntent.PREVIOUS));
        assertTrue(SettingsInputPolicy.consumeWheelWithoutAdjustment(
                "Display", UiInputIntent.NEXT));
    }

    @Test public void displayActivationNeverRequestsAdjustment() {
        assertFalse(SettingsInputPolicy.consumeWheelWithoutAdjustment(
                "Display", UiInputIntent.ACTIVATE));
    }

    @Test public void brightnessStepsAreBoundedAwayFromAnUnusableBlackScreen() {
        assertEquals(13, SettingsPanelView.adjustedBrightness(0, false));
        assertEquals(39, SettingsPanelView.adjustedBrightness(13, true));
        assertEquals(255, SettingsPanelView.adjustedBrightness(250, true));
        assertEquals(224, SettingsPanelView.adjustedBrightness(250, false));
    }

    @Test public void soundWheelNeverChangesVolume() {
        assertTrue(SettingsInputPolicy.consumeWheelWithoutAdjustment(
                "Sound", UiInputIntent.PREVIOUS));
        assertTrue(SettingsInputPolicy.consumeWheelWithoutAdjustment(
                "Sound", UiInputIntent.NEXT));
    }

    @Test public void policyDoesNotConsumeActivationOrOtherPages() {
        assertFalse(SettingsInputPolicy.consumeWheelWithoutAdjustment(
                "Display", UiInputIntent.ACTIVATE));
        assertFalse(SettingsInputPolicy.consumeWheelWithoutAdjustment(
                "Wi-Fi", UiInputIntent.NEXT));
    }

    @Test public void aiArrowCyclesAndWrapsDeterministically() {
        String[] values = new String[]{"none", "low", "medium", "high"};
        assertEquals("low", SettingsPanelView.nextOption("none", values));
        assertEquals("none", SettingsPanelView.nextOption("high", values));
        assertEquals("none", SettingsPanelView.nextOption("missing", values));
    }

    @Test public void wifiActionCountOnlyAddsSignInForConfirmedPortal() {
        assertEquals(1, SettingsInputPolicy.wifiActionCount(false));
        assertEquals(2, SettingsInputPolicy.wifiActionCount(true));
    }

    @Test public void wifiConnectedNetworkDetailDistinguishesSignInRequired() {
        assertEquals("NEEDS SIGN-IN", SettingsPanelView.wifiNetworkDetail(true, false, true));
        assertEquals("NEEDS SIGN-IN", SettingsPanelView.wifiNetworkDetail(true, true, true));
        assertEquals("CONNECTED", SettingsPanelView.wifiNetworkDetail(true, false, false));
        assertEquals("CONNECTED", SettingsPanelView.wifiNetworkDetail(true, true, false));
    }

    @Test public void wifiDisconnectedNetworkDetailPreservesSecurityLabels() {
        assertEquals("SECURE", SettingsPanelView.wifiNetworkDetail(false, true, false));
        assertEquals("SECURE", SettingsPanelView.wifiNetworkDetail(false, true, true));
        assertEquals("OPEN", SettingsPanelView.wifiNetworkDetail(false, false, false));
        assertEquals("OPEN", SettingsPanelView.wifiNetworkDetail(false, false, true));
    }

    @Test public void wifiHardwareIndexMapsToPortalActions() {
        assertEquals(SettingsInputPolicy.WifiAction.SCAN_AGAIN,
                SettingsInputPolicy.wifiActionAt(false, 0));
        assertEquals(SettingsInputPolicy.WifiAction.OPEN_SIGN_IN,
                SettingsInputPolicy.wifiActionAt(true, 0));
        assertEquals(SettingsInputPolicy.WifiAction.SCAN_AGAIN,
                SettingsInputPolicy.wifiActionAt(true, 1));
        assertEquals(SettingsInputPolicy.WifiAction.NONE,
                SettingsInputPolicy.wifiActionAt(true, 2));
    }

    @Test public void wifiWheelEntersAndMovesPortalActionSelection() {
        assertEquals(0, SettingsInputPolicy.wifiSelectionAfterWheel(
                true, SettingsInputPolicy.NO_WIFI_ACTION_SELECTED, UiInputIntent.NEXT));
        assertEquals(1, SettingsInputPolicy.wifiSelectionAfterWheel(
                true, SettingsInputPolicy.NO_WIFI_ACTION_SELECTED, UiInputIntent.PREVIOUS));
        assertEquals(1, SettingsInputPolicy.wifiSelectionAfterWheel(
                true, 0, UiInputIntent.NEXT));
        assertEquals(0, SettingsInputPolicy.wifiSelectionAfterWheel(
                true, 1, UiInputIntent.PREVIOUS));
    }

    @Test public void wifiWheelLeavesNonPortalHardwareBehaviorUntouched() {
        assertEquals(SettingsInputPolicy.NO_WIFI_ACTION_SELECTED,
                SettingsInputPolicy.wifiSelectionAfterWheel(
                        false, 0, UiInputIntent.NEXT));
        assertEquals(SettingsInputPolicy.NO_WIFI_ACTION_SELECTED,
                SettingsInputPolicy.wifiSelectionAfterWheel(
                        false, 0, UiInputIntent.PREVIOUS));
    }

    @Test public void wifiActivationPreservesFirstNetworkUntilPortalActionIsSelected() {
        assertEquals(SettingsInputPolicy.WifiAction.CONNECT_FIRST_NETWORK,
                SettingsInputPolicy.wifiActivateAction(false, true,
                        SettingsInputPolicy.NO_WIFI_ACTION_SELECTED));
        assertEquals(SettingsInputPolicy.WifiAction.CONNECT_FIRST_NETWORK,
                SettingsInputPolicy.wifiActivateAction(true, true,
                        SettingsInputPolicy.NO_WIFI_ACTION_SELECTED));
        assertEquals(SettingsInputPolicy.WifiAction.OPEN_SIGN_IN,
                SettingsInputPolicy.wifiActivateAction(true, false,
                        SettingsInputPolicy.NO_WIFI_ACTION_SELECTED));
        assertEquals(SettingsInputPolicy.WifiAction.OPEN_SIGN_IN,
                SettingsInputPolicy.wifiActivateAction(true, true, 0));
        assertEquals(SettingsInputPolicy.WifiAction.SCAN_AGAIN,
                SettingsInputPolicy.wifiActivateAction(true, true, 1));
        assertEquals(SettingsInputPolicy.WifiAction.NONE,
                SettingsInputPolicy.wifiActivateAction(false, false,
                        SettingsInputPolicy.NO_WIFI_ACTION_SELECTED));
    }

    @Test public void wifiPortalTouchMatchesExactButtonBounds() {
        assertEquals(SettingsInputPolicy.WifiAction.OPEN_SIGN_IN,
                SettingsInputPolicy.wifiTouchAction(true, 20f, 532f));
        assertEquals(SettingsInputPolicy.WifiAction.OPEN_SIGN_IN,
                SettingsInputPolicy.wifiTouchAction(true, 232f, 604f));
        assertEquals(SettingsInputPolicy.WifiAction.SCAN_AGAIN,
                SettingsInputPolicy.wifiTouchAction(true, 248f, 532f));
        assertEquals(SettingsInputPolicy.WifiAction.SCAN_AGAIN,
                SettingsInputPolicy.wifiTouchAction(true, 460f, 604f));
    }

    @Test public void wifiPortalTouchRejectsGapAndOutsideEdges() {
        assertEquals(SettingsInputPolicy.WifiAction.NONE,
                SettingsInputPolicy.wifiTouchAction(true, 240f, 570f));
        assertEquals(SettingsInputPolicy.WifiAction.NONE,
                SettingsInputPolicy.wifiTouchAction(true, 19f, 570f));
        assertEquals(SettingsInputPolicy.WifiAction.NONE,
                SettingsInputPolicy.wifiTouchAction(true, 120f, 531f));
        assertEquals(SettingsInputPolicy.WifiAction.NONE,
                SettingsInputPolicy.wifiTouchAction(true, 350f, 605f));
    }

    @Test public void wifiNonPortalTouchKeepsFullWidthScanButton() {
        assertEquals(SettingsInputPolicy.WifiAction.SCAN_AGAIN,
                SettingsInputPolicy.wifiTouchAction(false, -100f, 520f));
        assertEquals(SettingsInputPolicy.WifiAction.SCAN_AGAIN,
                SettingsInputPolicy.wifiTouchAction(false, 240f, 570f));
        assertEquals(SettingsInputPolicy.WifiAction.SCAN_AGAIN,
                SettingsInputPolicy.wifiTouchAction(false, 580f, 620f));
        assertEquals(SettingsInputPolicy.WifiAction.NONE,
                SettingsInputPolicy.wifiTouchAction(false, 240f, 519f));
        assertEquals(SettingsInputPolicy.WifiAction.NONE,
                SettingsInputPolicy.wifiTouchAction(false, 240f, 621f));
    }
}
