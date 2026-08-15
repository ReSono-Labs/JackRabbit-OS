package com.resonolabs.runtime.host;

/** Narrow Java boundary exposed to the embedded runtime. */
public final class RuntimeCredentialBridge {
    private final RuntimeCredentialStore store;

    RuntimeCredentialBridge(RuntimeCredentialStore store) {
        this.store = store;
    }

    public boolean hasOpenAiPlatformKey() {
        return store.hasOpenAiPlatformKey();
    }

    public String getOpenAiPlatformKey() throws Exception {
        return store.getOpenAiPlatformKey();
    }

    public void putOpenAiPlatformKey(String value) throws Exception {
        store.putOpenAiPlatformKey(value);
    }

    public void deleteOpenAiPlatformKey() throws Exception {
        store.deleteOpenAiPlatformKey();
    }

    public boolean hasOpenAiSubscriptionTokens() {
        return store.hasOpenAiSubscriptionTokens();
    }

    public String getOpenAiSubscriptionTokens() throws Exception {
        return store.getOpenAiSubscriptionTokens();
    }

    public void putOpenAiSubscriptionTokens(String value) throws Exception {
        store.putOpenAiSubscriptionTokens(value);
    }

    public void deleteOpenAiSubscriptionTokens() throws Exception {
        store.deleteOpenAiSubscriptionTokens();
    }
}
