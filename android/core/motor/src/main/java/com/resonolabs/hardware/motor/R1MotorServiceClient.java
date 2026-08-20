package com.resonolabs.hardware.motor;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.RemoteException;

/** Client for the privileged, named-position R1 motor service. */
public final class R1MotorServiceClient implements MotorController {
    public static final String SERVICE_ACTION = "com.resonolabs.hardware.motor.R1_MOTOR_SERVICE";
    public static final String SERVICE_PACKAGE = "com.resonolabs.hardware";
    private static final int POSITION_OUTWARD = 1;
    private static final int POSITION_HOME = 2;
    private static final int POSITION_INWARD = 3;
    private static final int STATE_MOVING = 1;
    private static final int STATE_AT_POSITION = 2;
    private static final int STATE_FAILED = 3;
    private static final long MOVE_TIMEOUT_MILLIS = 8_000L;

    private final Context context;
    private final Handler main = new Handler(Looper.getMainLooper());
    private IR1MotorService service;
    private Callback pending;
    private Position pendingPosition;
    private boolean bound;
    private boolean closed;
    private boolean homeRequested;
    private final Runnable timeout = () -> {
        Callback callback = pending;
        pending = null;
        if (callback != null) callback.onState(State.FAILED, pendingPosition);
    };

    private final ServiceConnection connection = new ServiceConnection() {
        @Override public void onServiceConnected(ComponentName name, IBinder binder) {
            service = IR1MotorService.Stub.asInterface(binder);
            issuePendingMove();
        }

        @Override public void onServiceDisconnected(ComponentName name) {
            service = null;
            homeRequested = false;
            failPending(State.UNAVAILABLE);
        }
    };

    public R1MotorServiceClient(Context context) {
        this.context = context.getApplicationContext();
    }

    @Override public void moveTo(Position position, Callback callback) {
        if (closed) { callback.onState(State.UNAVAILABLE, position); return; }
        if (position != Position.HOME) homeRequested = false;
        pending = callback;
        pendingPosition = position;
        callback.onState(State.CONNECTING, position);
        if (service != null) { issuePendingMove(); return; }
        Intent intent = new Intent(SERVICE_ACTION).setPackage(SERVICE_PACKAGE);
        try {
            bound = context.bindService(intent, connection, Context.BIND_AUTO_CREATE);
        } catch (SecurityException exception) {
            bound = false;
        }
        if (!bound) failPending(State.UNAVAILABLE);
    }

    private void issuePendingMove() {
        Callback callback = pending;
        Position position = pendingPosition;
        if (service == null || callback == null || position == null) return;
        callback.onState(State.MOVING, position);
        main.removeCallbacks(timeout);
        main.postDelayed(timeout, MOVE_TIMEOUT_MILLIS);
        try {
            service.moveTo(servicePosition(position),
                    new IR1MotorCallback.Stub() {
                        @Override public void onStateChanged(int state, int reportedPosition) {
                            main.post(() -> handleServiceState(state, reportedPosition));
                        }
                    });
        } catch (RemoteException | SecurityException exception) {
            failPending(State.FAILED);
        }
    }

    private void handleServiceState(int state, int reportedPosition) {
        Callback callback = pending;
        Position requested = pendingPosition;
        if (callback == null || requested == null) return;
        if (state == STATE_MOVING) {
            callback.onState(State.MOVING, requested);
        } else if (state == STATE_AT_POSITION
                && reportedPosition == servicePosition(requested)) {
            main.removeCallbacks(timeout);
            pending = null;
            callback.onState(State.AT_POSITION, requested);
        } else if (state == STATE_FAILED) {
            failPending(State.FAILED);
        }
    }

    private static int servicePosition(Position position) {
        return switch (position) {
            case OUTWARD -> POSITION_OUTWARD;
            case INWARD -> POSITION_INWARD;
            case HOME -> POSITION_HOME;
        };
    }

    private void failPending(State state) {
        main.removeCallbacks(timeout);
        Callback callback = pending;
        Position position = pendingPosition;
        pending = null;
        if (callback != null) main.post(() -> callback.onState(state, position));
    }

    @Override public void returnHome() {
        main.removeCallbacks(timeout);
        pending = null;
        if (service == null || homeRequested) return;
        homeRequested = true;
        try {
            service.returnHome(new IR1MotorCallback.Stub() {
                @Override public void onStateChanged(int state, int position) {
                    if (state == STATE_FAILED) main.post(() -> homeRequested = false);
                }
            });
        } catch (RemoteException | SecurityException ignored) {
            homeRequested = false;
        }
    }

    @Override public void close() {
        if (closed) return;
        closed = true;
        returnHome();
        if (bound) {
            try { context.unbindService(connection); } catch (IllegalArgumentException ignored) { }
        }
        bound = false;
        service = null;
    }
}
