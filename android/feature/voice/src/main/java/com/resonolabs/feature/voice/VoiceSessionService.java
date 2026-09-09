package com.resonolabs.feature.voice;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.IBinder;
import android.os.PowerManager;

/** Holds native Voice resources while the screen or its View is not visible. */
public final class VoiceSessionService extends Service {
    private static final String CHANNEL = "resono-voice-session";
    private static VoiceSessionController controller;
    private static long requestedGeneration;
    private long generation;
    private PowerManager.WakeLock wakeLock;

    static synchronized VoiceSessionController controller(Context context) {
        if (controller == null) controller = new VoiceSessionController(context.getApplicationContext());
        return controller;
    }

    static void start(Context context, long generation) {
        requestedGeneration = generation;
        context.startForegroundService(new Intent(context, VoiceSessionService.class)
                .putExtra("generation", generation));
    }

    static void stop(Context context) {
        requestedGeneration = 0;
        context.stopService(new Intent(context, VoiceSessionService.class));
    }

    @Override public void onCreate() {
        super.onCreate();
        try {
            NotificationManager notifications = getSystemService(NotificationManager.class);
            notifications.createNotificationChannel(new NotificationChannel(
                    CHANNEL, "Voice session", NotificationManager.IMPORTANCE_LOW));
            Intent launch = getPackageManager().getLaunchIntentForPackage(getPackageName());
            Notification.Builder builder = new Notification.Builder(this, CHANNEL)
                    .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                    .setContentTitle("JackRabbit Voice")
                    .setContentText("Voice session active. Open Voice to end it.")
                    .setOngoing(true);
            if (launch != null) builder.setContentIntent(PendingIntent.getActivity(this, 0, launch,
                    PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT));
            startForeground(42, builder.build(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
                    | ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
            PowerManager power = getSystemService(PowerManager.class);
            wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "JackRabbit:Voice");
            wakeLock.setReferenceCounted(false);
            wakeLock.acquire();
        } catch (RuntimeException error) {
            if (controller != null) controller.serviceFailed(requestedGeneration);
            stopSelf();
        }
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        long requested = intent == null ? 0 : intent.getLongExtra("generation", 0);
        if (requested == requestedGeneration) generation = requested;
        if (requestedGeneration == 0) stopSelf(startId);
        // A killed process never silently restarts microphone capture.
        return START_NOT_STICKY;
    }

    @Override public void onDestroy() {
        // An old service can finish destroying after a new session was requested.
        if (generation != 0 && generation == requestedGeneration && controller != null) {
            controller.serviceFailed(generation);
        }
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) { return null; }
}
