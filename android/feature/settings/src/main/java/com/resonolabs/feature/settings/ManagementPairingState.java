package com.resonolabs.feature.settings;

public record ManagementPairingState(String status, String code, String address, long expiresAt) {
    public static ManagementPairingState loading() {
        return new ManagementPairingState("loading", "—", "Reading on-device runtime…", 0L);
    }
}
