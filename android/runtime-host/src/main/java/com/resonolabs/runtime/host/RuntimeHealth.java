package com.resonolabs.runtime.host;

public record RuntimeHealth(String status, int contractVersion, int migrationVersion) {
    public static RuntimeHealth unavailable() {
        return new RuntimeHealth("unavailable", 1, 0);
    }
}
