package com.resonolabs.runtime.host;

import android.content.Context;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

final class RuntimePythonHost {
    private boolean running;

    synchronized void start(
            Context context,
            String rootPath,
            String localApiToken,
            RuntimeCredentialBridge credentials,
            Runnable restartRequest,
            Object telephonyBridge) {
        if (running) return;
        if (!Python.isStarted()) Python.start(new AndroidPlatform(context));
        Python.getInstance()
                .getModule("resono_runtime.entrypoint")
                .callAttr("start", rootPath, localApiToken, credentials, restartRequest, telephonyBridge);
        running = true;
    }

    synchronized void stop() {
        if (!running || !Python.isStarted()) return;
        Python.getInstance().getModule("resono_runtime.entrypoint").callAttr("stop");
        running = false;
    }
}
