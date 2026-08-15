package com.resonolabs.runtime.host;

public record RuntimeManagementPairing(
        String status,
        String code,
        String address,
        long expiresAt) {
    static RuntimeManagementPairing unavailable() {
        return new RuntimeManagementPairing("unavailable", "—", "Connect R1 to Wi-Fi", 0L);
    }
}
