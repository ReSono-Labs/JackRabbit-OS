package com.resonolabs.feature.telephony;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.telephony.ServiceState;
import android.telephony.SignalStrength;
import android.telephony.SubscriptionManager;
import android.telephony.TelephonyManager;

/** {@link TelephonyBridge} backed by the Android telephony framework. */
public final class AndroidTelephonyBridge implements TelephonyBridge {

    private final Context appContext;
    private final TelephonyManager telephonyManager;
    private final SubscriptionManager subscriptionManager;
    private final android.telephony.SmsManager smsManager;

    public AndroidTelephonyBridge(Context context) {
        this.appContext = context.getApplicationContext();
        this.telephonyManager = context.getSystemService(TelephonyManager.class);
        this.subscriptionManager = context.getSystemService(SubscriptionManager.class);
        this.smsManager = android.telephony.SmsManager.getDefault();
    }

    @Override
    public boolean simPresent() {
        return telephonyManager.getSimState() != TelephonyManager.SIM_STATE_ABSENT;
    }

    @Override
    public String simState() {
        int state = telephonyManager.getSimState();
        switch (state) {
            case TelephonyManager.SIM_STATE_ABSENT: return "ABSENT";
            case TelephonyManager.SIM_STATE_PIN_REQUIRED: return "PIN_REQUIRED";
            case TelephonyManager.SIM_STATE_PUK_REQUIRED: return "PUK_REQUIRED";
            case TelephonyManager.SIM_STATE_NETWORK_LOCKED: return "NETWORK_LOCKED";
            case TelephonyManager.SIM_STATE_READY: return "READY";
            default: return "UNKNOWN";
        }
    }

    @Override
    public String carrierName() {
        try {
            return telephonyManager.getNetworkOperatorName();
        } catch (SecurityException e) {
            return "";
        }
    }

    @Override
    public String networkType() {
        return networkTypeString(telephonyManager.getDataNetworkType());
    }

    @Override
    public int signalLevel() {
        SignalStrength strength = telephonyManager.getSignalStrength();
        return strength == null ? 0 : strength.getLevel();
    }

    @Override
    public boolean voiceRegistered() {
        ServiceState state = telephonyManager.getServiceState();
        return state != null && state.getState() == ServiceState.STATE_IN_SERVICE;
    }

    @Override
    public String callState() {
        int state = telephonyManager.getCallState();
        switch (state) {
            case TelephonyManager.CALL_STATE_IDLE: return "IDLE";
            case TelephonyManager.CALL_STATE_RINGING: return "RINGING";
            case TelephonyManager.CALL_STATE_OFFHOOK: return "OFFHOOK";
            default: return "UNKNOWN";
        }
    }

    @Override
    public boolean placeCall(String number) {
        try {
            Intent intent = new Intent(Intent.ACTION_CALL,
                    Uri.parse("tel:" + number));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            appContext.startActivity(intent);
            return true;
        } catch (SecurityException | android.content.ActivityNotFoundException e) {
            return false;
        }
    }

    @Override
    public boolean sendSms(String to, String text) {
        try {
            smsManager.sendTextMessage(to, null, text, null, null);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private static String networkTypeString(int type) {
        switch (type) {
            case TelephonyManager.NETWORK_TYPE_LTE: return "LTE";
            case TelephonyManager.NETWORK_TYPE_NR: return "NR";
            case TelephonyManager.NETWORK_TYPE_UMTS: return "UMTS";
            case TelephonyManager.NETWORK_TYPE_EDGE: return "EDGE";
            case TelephonyManager.NETWORK_TYPE_GPRS: return "GPRS";
            case TelephonyManager.NETWORK_TYPE_GSM: return "GSM";
            case TelephonyManager.NETWORK_TYPE_CDMA: return "CDMA";
            default: return TelephonyManager.getNetworkTypeName(type);
        }
    }
}
