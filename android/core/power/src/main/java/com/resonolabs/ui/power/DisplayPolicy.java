package com.resonolabs.ui.power;

import android.util.Log;
import android.view.Window;
import android.view.WindowManager;

import java.lang.reflect.Field;

public final class DisplayPolicy {
    private static final String TAG = "ReSonoDisplayPolicy";
    // Confirmed from the framework.jar retained from the exact Rabbit R1 image.
    private static final int RABBIT_DISABLE_USER_ACTIVITY = 2;
    public static final long IDLE_TIMEOUT_MS = -1L;
    private static boolean inputPolicyLogged;

    private DisplayPolicy() {}

    public static void apply(Window window) {
        WindowManager.LayoutParams params = window.getAttributes();
        applyDisableUserActivity(params);
        setWindowIdleTimeout(params, IDLE_TIMEOUT_MS);
        // Never override the configured display level from HOME.
        params.screenBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE;
        window.setAttributes(params);
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }

    /** Reapply only the focused-window input policy after lifecycle/focus changes. */
    public static void applyInputPolicy(Window window) {
        WindowManager.LayoutParams params = window.getAttributes();
        applyDisableUserActivity(params);
        window.setAttributes(params);
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }

    private static void setWindowIdleTimeout(
            WindowManager.LayoutParams params, long timeoutMs) {
        try {
            Field field = WindowManager.LayoutParams.class
                    .getDeclaredField("userActivityTimeout");
            field.setAccessible(true);
            field.setLong(params, timeoutMs);
        } catch (ReflectiveOperationException | RuntimeException exception) {
            Log.e(TAG, "Unable to set R1 window userActivityTimeout", exception);
        }
    }

    /**
     * Prevent input delivered to the focused HOME window from poking Android's
     * display user-activity path before HOME receives the event. Both members
     * are hidden platform APIs, so this diagnostic build resolves them from the
     * device's own framework and refuses to apply an unexpected flag value.
     */
    private static void applyDisableUserActivity(WindowManager.LayoutParams params) {
        try {
            Field inputFeaturesField =
                    WindowManager.LayoutParams.class.getDeclaredField("inputFeatures");
            Field disableUserActivityField = WindowManager.LayoutParams.class
                    .getDeclaredField("INPUT_FEATURE_DISABLE_USER_ACTIVITY");
            inputFeaturesField.setAccessible(true);
            disableUserActivityField.setAccessible(true);

            int frameworkFlag = disableUserActivityField.getInt(null);
            if (frameworkFlag != RABBIT_DISABLE_USER_ACTIVITY) {
                Log.e(TAG, "Refusing unexpected DISABLE_USER_ACTIVITY value: "
                        + frameworkFlag);
                return;
            }

            int before = inputFeaturesField.getInt(params);
            int after = before | frameworkFlag;
            inputFeaturesField.setInt(params, after);
            if (!inputPolicyLogged) {
                inputPolicyLogged = true;
                Log.i(TAG, "Applied INPUT_FEATURE_DISABLE_USER_ACTIVITY: before=0x"
                        + Integer.toHexString(before) + " after=0x"
                        + Integer.toHexString(after));
            }
        } catch (ReflectiveOperationException | RuntimeException exception) {
            Log.e(TAG, "Unable to apply INPUT_FEATURE_DISABLE_USER_ACTIVITY", exception);
        }
    }
}
