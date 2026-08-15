package com.resonolabs.ui.input;

import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;

public final class HardwareInputRouter {
    private HardwareInputRouter() {}

    public static UiInputIntent keyIntent(int keyCode) {
        return switch (keyCode) {
            case KeyEvent.KEYCODE_DPAD_UP,
                    KeyEvent.KEYCODE_VOLUME_UP,
                    KeyEvent.KEYCODE_BRIGHTNESS_UP -> UiInputIntent.PREVIOUS;
            case KeyEvent.KEYCODE_DPAD_DOWN,
                    KeyEvent.KEYCODE_VOLUME_DOWN,
                    KeyEvent.KEYCODE_BRIGHTNESS_DOWN -> UiInputIntent.NEXT;
            case KeyEvent.KEYCODE_DPAD_CENTER, KeyEvent.KEYCODE_ENTER -> UiInputIntent.ACTIVATE;
            default -> null;
        };
    }

    public static UiInputIntent motionIntent(MotionEvent event) {
        if ((event.getSource() & InputDevice.SOURCE_CLASS_POINTER) == 0
                || event.getAction() != MotionEvent.ACTION_SCROLL) return null;
        float amount = event.getAxisValue(MotionEvent.AXIS_SCROLL);
        if (amount == 0f) return null;
        return amount > 0f ? UiInputIntent.PREVIOUS : UiInputIntent.NEXT;
    }
}
