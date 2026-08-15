package com.resonolabs.ui.input;

import android.view.KeyEvent;
import org.junit.Test;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

public final class HardwareInputRouterTest {
    @Test public void wheelKeysBecomeContentIntents() {
        assertEquals(UiInputIntent.PREVIOUS, HardwareInputRouter.keyIntent(KeyEvent.KEYCODE_VOLUME_UP));
        assertEquals(UiInputIntent.PREVIOUS, HardwareInputRouter.keyIntent(KeyEvent.KEYCODE_BRIGHTNESS_UP));
        assertEquals(UiInputIntent.NEXT, HardwareInputRouter.keyIntent(KeyEvent.KEYCODE_BRIGHTNESS_DOWN));
        assertEquals(UiInputIntent.NEXT, HardwareInputRouter.keyIntent(KeyEvent.KEYCODE_DPAD_DOWN));
        assertNull(HardwareInputRouter.keyIntent(KeyEvent.KEYCODE_DPAD_LEFT));
    }
}
