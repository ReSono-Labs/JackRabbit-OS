package com.resonolabs.runtime.host;

import android.content.Context;
import android.content.SharedPreferences;

final class RuntimeStartupLimiter {
    private static final String STORE = "runtime-supervision";
    private static final String FIRST_FAILURE = "first-failure";
    private static final String FAILURE_COUNT = "failure-count";
    private static final int MAX_FAILURES = 3;
    private static final long WINDOW_MILLIS = 5 * 60 * 1000L;
    private final SharedPreferences preferences;

    RuntimeStartupLimiter(Context context) {
        preferences = context.createDeviceProtectedStorageContext()
                .getSharedPreferences(STORE, Context.MODE_PRIVATE);
    }

    boolean mayStart(long now) {
        long first = preferences.getLong(FIRST_FAILURE, 0L);
        int count = preferences.getInt(FAILURE_COUNT, 0);
        if (first == 0L || now - first > WINDOW_MILLIS) {
            preferences.edit().clear().apply();
            return true;
        }
        return count < MAX_FAILURES;
    }

    void recordFailure(long now) {
        long first = preferences.getLong(FIRST_FAILURE, 0L);
        int count = preferences.getInt(FAILURE_COUNT, 0);
        if (first == 0L || now - first > WINDOW_MILLIS) {
            first = now;
            count = 0;
        }
        preferences.edit()
                .putLong(FIRST_FAILURE, first)
                .putInt(FAILURE_COUNT, count + 1)
                .apply();
    }

    void recordHealthy() {
        preferences.edit().clear().apply();
    }
}
