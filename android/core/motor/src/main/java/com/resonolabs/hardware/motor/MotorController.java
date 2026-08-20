package com.resonolabs.hardware.motor;

public interface MotorController extends AutoCloseable {
    enum Position { OUTWARD, INWARD, HOME }
    enum State { CONNECTING, MOVING, AT_POSITION, FAILED, UNAVAILABLE }
    interface Callback { void onState(State state, Position position); }

    void moveTo(Position position, Callback callback);
    void returnHome();
    @Override void close();
}
