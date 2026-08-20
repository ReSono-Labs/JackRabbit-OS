package com.resonolabs.feature.voice;
/** Sole boundary for injecting inspected context into the current Voice conversation. */
public interface VoiceSessionHandoff { boolean isAvailable(); String sessionId(); boolean submitInspected(String providerText,String transcriptText,String fileKey); }
