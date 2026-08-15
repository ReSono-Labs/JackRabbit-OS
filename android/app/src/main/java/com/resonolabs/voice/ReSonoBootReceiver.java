package com.resonolabs.voice;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

import com.resonolabs.runtime.host.RuntimeService;

public final class ReSonoBootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        if (!Intent.ACTION_LOCKED_BOOT_COMPLETED.equals(action)
                && !Intent.ACTION_BOOT_COMPLETED.equals(action)) return;
        SystemSetupState.markComplete(context);
        RuntimeService.start(context);
        context.startActivity(new Intent(context, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_CLEAR_TOP
                        | Intent.FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS));
    }
}
