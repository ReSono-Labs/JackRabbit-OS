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
}
