package com.resonolabs.runtime.host;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.os.IBinder;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import com.resonolabs.feature.telephony.AndroidTelephonyBridge;

import java.io.File;

public final class RuntimeService extends Service {
    private static final String LOG_TAG = "ReSonoRuntime";
    private static final String NOTIFICATION_CHANNEL = "resono_runtime";
    private static final int NOTIFICATION_ID = 4101;
    private final RuntimePythonHost python = new RuntimePythonHost();
    private final Handler main = new Handler(Looper.getMainLooper());
    private ManagementHttpsServer management;
    private Context runtimeStorage;
    private String localApiToken;
    private RuntimeStartupLimiter startupLimiter;
    private RuntimeCredentialBridge credentials;
    private boolean startupReady;

    public static void start(Context context) {
        context.startForegroundService(new Intent(context, RuntimeService.class));
    }

    @Override public void onCreate() {
        super.onCreate();
        startForeground(NOTIFICATION_ID, runtimeNotification());
        runtimeStorage = createDeviceProtectedStorageContext();
        startupLimiter = new RuntimeStartupLimiter(this);
        if (!startupLimiter.mayStart(System.currentTimeMillis())) {
            Log.e(LOG_TAG, "runtime startup paused after repeated failures");
            stopSelf();
            return;
        }
        try {
            localApiToken = new RuntimeSecretStore(this).loadOrCreateLocalApiToken();
            credentials = new RuntimeCredentialBridge(new RuntimeCredentialStore(this));
            management = new ManagementHttpsServer(this, localApiToken);
            management.start();
            startPython();
            startupLimiter.recordHealthy();
            startupReady = true;
            Log.i(LOG_TAG, "runtime process ready");
        } catch (Exception exception) {
            startupLimiter.recordFailure(System.currentTimeMillis());
            Log.e(LOG_TAG, "runtime startup failed", exception);
            stopForeground(STOP_FOREGROUND_REMOVE);
            stopSelf();
        }
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        return startupReady ? START_STICKY : START_NOT_STICKY;
    }

    @Override public void onDestroy() {
        if (management != null) management.close();
        python.stop();
        stopForeground(STOP_FOREGROUND_REMOVE);
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) {
        return null;
    }

    private void startPython() {
        File root = new File(runtimeStorage.getFilesDir(), "runtime");
        AndroidTelephonyBridge telephonyBridge = new AndroidTelephonyBridge(this);
        python.start(this, root.getAbsolutePath(), localApiToken, credentials, this::scheduleRuntimeRestart, telephonyBridge);
    }

    private void scheduleRuntimeRestart() {
        main.postDelayed(() -> {
            python.stop();
            startPython();
        }, 250L);
    }

    private Notification runtimeNotification() {
        NotificationManager notifications = getSystemService(NotificationManager.class);
        NotificationChannel channel = new NotificationChannel(
                NOTIFICATION_CHANNEL,
                "ReSono runtime",
                NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Keeps Voice and local R1 management available.");
        channel.setSound(null, null);
        channel.enableVibration(false);
        channel.setLightColor(Color.rgb(114, 239, 207));
        notifications.createNotificationChannel(channel);
        return new Notification.Builder(this, NOTIFICATION_CHANNEL)
                .setSmallIcon(android.R.drawable.stat_notify_sync_noanim)
                .setContentTitle("ReSono R1")
                .setContentText("Voice and device management are ready")
                .setCategory(Notification.CATEGORY_SERVICE)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .build();
    }
}
