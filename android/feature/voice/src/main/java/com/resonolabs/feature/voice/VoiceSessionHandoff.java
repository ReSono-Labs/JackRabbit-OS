package com.resonolabs.feature.voice;
/** Sole boundary for sending a captured image into the current Voice conversation. */
public interface VoiceSessionHandoff {
    boolean isAvailable();
    boolean submitImage(byte[] image, String mimeType, String filename);
}
