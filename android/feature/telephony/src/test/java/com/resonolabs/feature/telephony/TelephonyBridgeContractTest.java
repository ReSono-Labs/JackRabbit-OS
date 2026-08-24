package com.resonolabs.feature.telephony;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class TelephonyBridgeContractTest {
    @Test
    public void interface_matches_python_bridge_contract() {
        // Signature lock: these names/types are the Python-side contract.
        TelephonyBridge bridge = new TelephonyBridge() {
            @Override public boolean simPresent() { return false; }
            @Override public String simState() { return "ABSENT"; }
            @Override public String carrierName() { return ""; }
            @Override public String networkType() { return ""; }
            @Override public int signalLevel() { return 0; }
            @Override public boolean voiceRegistered() { return false; }
            @Override public String callState() { return "IDLE"; }
        };
        assertNotNull(bridge.simState());
        assertEquals("ABSENT", bridge.simState());
        assertEquals("IDLE", bridge.callState());
        assertTrue(!bridge.simPresent());
    }
}
