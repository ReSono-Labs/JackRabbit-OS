package com.resonolabs.voice;

import android.content.Context;
import android.provider.Settings;
import android.util.Log;

final class SystemSetupState {
    private static final String TAG = "ReSonoSystemSetup";

    private SystemSetupState() { }

    static void markComplete(Context context) {
        try {
            Settings.Global.putInt(context.getContentResolver(),
                    Settings.Global.DEVICE_PROVISIONED, 1);
            Settings.Secure.putInt(context.getContentResolver(),
                    "user_setup_complete", 1);
        } catch (SecurityException exception) {
            Log.w(TAG, "System setup flags unavailable", exception);
        }
    }
}
