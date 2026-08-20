package com.resonolabs.hardware.motor;

import com.resonolabs.hardware.motor.IR1MotorCallback;

interface IR1MotorService {
    void moveTo(int namedPosition, IR1MotorCallback callback);
    void returnHome(IR1MotorCallback callback);
    int getState();
}
