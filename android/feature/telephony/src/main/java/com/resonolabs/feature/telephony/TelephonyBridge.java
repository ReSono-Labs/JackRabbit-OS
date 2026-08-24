package com.resonolabs.feature.telephony;

/** Read-only native telephony surface exposed to the on-device agent runtime. */
public interface TelephonyBridge {
    boolean simPresent();
    String simState();
    String carrierName();
    String networkType();
    int signalLevel();
    boolean voiceRegistered();
    String callState();

    boolean placeCall(String number);
    boolean sendSms(String to, String text);
}
