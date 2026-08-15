package com.resonolabs.feature.settings;

import java.util.function.Consumer;

public interface ManagementPairingSource {
    void load(Consumer<ManagementPairingState> callback);
}
