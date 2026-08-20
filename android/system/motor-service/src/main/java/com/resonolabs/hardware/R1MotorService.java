package com.resonolabs.hardware;

import android.app.Service;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.content.pm.SigningInfo;
import android.os.Binder;
import android.os.IBinder;
import android.os.RemoteException;
import android.util.Log;

import com.resonolabs.hardware.motor.IR1MotorCallback;
import com.resonolabs.hardware.motor.IR1MotorService;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Privileged CipherOS adapter. Raw motor values never cross this process. */
public final class R1MotorService extends Service {
    private static final String LOG_TAG = "ReSonoMotor";
    static final int POSITION_OUTWARD = 1;
    static final int POSITION_HOME = 2;
    static final int POSITION_INWARD = 3;
    static final int STATE_MOVING = 1;
    static final int STATE_AT_POSITION = 2;
    static final int STATE_FAILED = 3;
    // Physically observed on product R1 919109A5P1600502814D. The donor labels were
    // offset by one state on this unit; physical shutter state is authoritative.
    static final int R1_OUTWARD = 180;
    static final int R1_INWARD = 0;
    static final int R1_CLOSED = 180;
    private static final long SETTLE_MILLIS = 2_000L;
    private static final long CONFIRM_WINDOW_MILLIS = 1_500L;
    private static final long CONFIRM_POLL_MILLIS = 100L;
    private static final String ORIENTATION =
            "/sys/devices/platform/step_motor_ms35774/orientation";
    private static final String ENGINEERING_CLIENT = "com.resonolabs.voice.engineering";
    private static final String PRODUCTION_CLIENT = "com.resonolabs.voice";
    private static final String ENGINEERING_CERT_SHA256 =
            "a3390000a4b6c8bf43774cc235bd967e4c80a9dae30c0e8714c79c01a9b9836a";

    private final ExecutorService moves = Executors.newSingleThreadExecutor(runnable -> {
        Thread thread = new Thread(runnable, "resono-r1-motor");
        thread.setDaemon(true);
        return thread;
    });
    private volatile int state = STATE_AT_POSITION;

    @Override public void onCreate() {
        super.onCreate();
        moves.execute(R1MotorService::bestEffortPrivacy);
    }

    private final IR1MotorService.Stub binder = new IR1MotorService.Stub() {
        @Override public void moveTo(int namedPosition, IR1MotorCallback callback) {
            enforceAuthorizedCaller();
            int raw = rawPositionFor(namedPosition);
            if (raw < 0) {
                notifyState(callback, STATE_FAILED, namedPosition);
                return;
            }
            moves.execute(() -> performMove(namedPosition, raw, callback));
        }

        @Override public void returnHome(IR1MotorCallback callback) {
            enforceAuthorizedCaller();
            moves.execute(() -> performMove(POSITION_HOME, R1_CLOSED, callback));
        }

        @Override public int getState() {
            enforceAuthorizedCaller();
            return state;
        }
    };

    private void enforceAuthorizedCaller() {
        int callerUid = Binder.getCallingUid();
        String[] packages = getPackageManager().getPackagesForUid(callerUid);
        if (packages != null) {
            for (String packageName : packages) {
                if ((ENGINEERING_CLIENT.equals(packageName) || PRODUCTION_CLIENT.equals(packageName))
                        && ENGINEERING_CERT_SHA256.equals(packageCertificateSha256(packageName))) {
                    return;
                }
            }
        }
        throw new SecurityException("r1_motor_caller_not_authorized");
    }

    private String packageCertificateSha256(String packageName) {
        try {
            PackageInfo info = getPackageManager().getPackageInfo(
                    packageName, PackageManager.PackageInfoFlags.of(PackageManager.GET_SIGNING_CERTIFICATES));
            SigningInfo signingInfo = info.signingInfo;
            if (signingInfo == null) return "";
            Signature[] signatures = signingInfo.hasMultipleSigners()
                    ? signingInfo.getApkContentsSigners()
                    : signingInfo.getSigningCertificateHistory();
            if (signatures == null || signatures.length != 1) return "";
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(signatures[0].toByteArray());
            StringBuilder value = new StringBuilder(digest.length * 2);
            for (byte item : digest) value.append(String.format(Locale.ROOT, "%02x", item & 0xff));
            return value.toString();
        } catch (Exception ignored) {
            return "";
        }
    }

    static int rawPositionFor(int namedPosition) {
        return switch (namedPosition) {
            case POSITION_OUTWARD -> R1_OUTWARD;
            case POSITION_INWARD -> R1_INWARD;
            case POSITION_HOME -> R1_CLOSED;
            default -> -1;
        };
    }

    private void performMove(int namedPosition, int rawPosition, IR1MotorCallback callback) {
        Log.i(LOG_TAG, "move requested named=" + namedPosition + " raw=" + rawPosition);
        state = STATE_MOVING;
        notifyState(callback, STATE_MOVING, namedPosition);
        try {
            // The sysfs node is the hardware authority across app/service lifetimes. Reopening
            // Camera after an already-completed move must not depend on stale in-process state.
            String reported = readOrientation();
            if (reportedPositionMatches(reported, rawPosition)) {
                state = STATE_AT_POSITION;
                notifyState(callback, STATE_AT_POSITION, namedPosition);
                return;
            }

            // The r1's normal direction flip travels through the physical privacy position.
            // Do not ask the stepper driver to reverse directly across its full 180-degree arc.
            if (requiresPrivacyWaypoint(reported, rawPosition)) {
                moveAndConfirm(R1_CLOSED, "privacy waypoint");
            }
            moveAndConfirm(rawPosition, "target");
            state = STATE_AT_POSITION;
            notifyState(callback, STATE_AT_POSITION, namedPosition);
        } catch (Exception exception) {
            Log.e(LOG_TAG, "named move failed position=" + namedPosition
                    + " type=" + exception.getClass().getSimpleName()
                    + " message=" + exception.getMessage());
            state = STATE_FAILED;
            notifyState(callback, STATE_FAILED, namedPosition);
            if (namedPosition != POSITION_HOME) bestEffortPrivacy();
        }
    }

    static boolean reportedPositionMatches(String reported, int expectedRawPosition) {
        return Integer.toString(expectedRawPosition).equals(
                reported == null ? "" : reported.trim());
    }

    static boolean requiresPrivacyWaypoint(String reported, int targetRawPosition) {
        return (reportedPositionMatches(reported, R1_OUTWARD)
                && targetRawPosition == R1_INWARD)
                || (reportedPositionMatches(reported, R1_INWARD)
                && targetRawPosition == R1_OUTWARD);
    }

    private static void moveAndConfirm(int rawPosition, String stage) throws Exception {
        writeOrientation(rawPosition);
        Thread.sleep(SETTLE_MILLIS);
        String reported = awaitReportedPosition(rawPosition);
        if (!reportedPositionMatches(reported, rawPosition)) {
            throw new IllegalStateException(stage + " motor position mismatch; reported=" + reported);
        }
    }

    /**
     * CipherOS can expose a short transitional value when travel completes. Keep the camera
     * closed and poll only for a bounded interval; never treat timeout as confirmation.
     */
    private static String awaitReportedPosition(int expectedRawPosition) throws Exception {
        long deadlineNanos = System.nanoTime() + CONFIRM_WINDOW_MILLIS * 1_000_000L;
        String reported = readOrientation();
        while (!reportedPositionMatches(reported, expectedRawPosition)
                && System.nanoTime() < deadlineNanos) {
            Thread.sleep(CONFIRM_POLL_MILLIS);
            reported = readOrientation();
        }
        return reported;
    }

    private static void notifyState(IR1MotorCallback callback, int state, int position) {
        if (callback == null) return;
        try { callback.onStateChanged(state, position); } catch (RemoteException ignored) { }
    }

    private static void bestEffortPrivacy() {
        try {
            writeOrientation(R1_CLOSED);
        } catch (Exception ignored) { }
    }

    private static void writeOrientation(int value) throws Exception {
        try (FileOutputStream output = new FileOutputStream(ORIENTATION, false)) {
            output.write(Integer.toString(value).getBytes(StandardCharsets.US_ASCII));
            output.flush();
        }
    }

    private static String readOrientation() throws Exception {
        try (BufferedReader input = new BufferedReader(new InputStreamReader(
                new FileInputStream(ORIENTATION), StandardCharsets.US_ASCII))) {
            String value = input.readLine();
            return value == null ? "" : value.trim();
        }
    }

    @Override public IBinder onBind(Intent intent) { return binder; }

    @Override public void onTaskRemoved(Intent rootIntent) {
        moves.execute(R1MotorService::bestEffortPrivacy);
        super.onTaskRemoved(rootIntent);
    }

    @Override public void onDestroy() {
        moves.execute(R1MotorService::bestEffortPrivacy);
        moves.shutdown();
        super.onDestroy();
    }
}
