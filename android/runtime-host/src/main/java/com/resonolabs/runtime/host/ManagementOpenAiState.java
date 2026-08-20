package com.resonolabs.runtime.host;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/** Canonical OpenAI contract payload surfaced in native settings. */
public record ManagementOpenAiState(
        String provider,
        String accessPath,
        boolean connected,
        boolean platformConnected,
        boolean subscriptionConnected,
        String selectedTextModel,
        String selectedRealtimeModel,
        String reasoningEffort,
        String[] providerIds,
        String[] providerNames,
        String[] textModels,
        String[] realtimeModels,
        String message,
        boolean error,
        boolean available) {
    private static final String DEFAULT_PROVIDER = "openai";

    public static ManagementOpenAiState loading() {
        return new ManagementOpenAiState(
                DEFAULT_PROVIDER,
                "platform",
                false,
                false,
                false,
                null,
                null,
                "none",
                new String[]{DEFAULT_PROVIDER},
                new String[]{"OpenAI"},
                new String[0],
                new String[0],
                null,
                false,
                true);
    }

    public static ManagementOpenAiState fromJson(JSONObject payload) {
        if (payload == null) {
            return new ManagementOpenAiState(
                    DEFAULT_PROVIDER,
                    "platform",
                    false,
                    false,
                    false,
                    null,
                    null,
                    "none",
                    new String[0],
                    new String[0],
                    new String[0],
                    new String[0],
                    "Runtime unavailable",
                    true,
                    false);
        }
        if (payload.has("error")) {
            JSONObject error = payload.optJSONObject("error");
            return new ManagementOpenAiState(
                    DEFAULT_PROVIDER,
                    "platform",
                    false,
                    false,
                    false,
                    null,
                    null,
                    "none",
                    new String[0],
                    new String[0],
                    new String[0],
                    new String[0],
                    error == null ? "Request failed" : error.optString("message", "Request failed"),
                    true,
                    false);
        }
        JSONObject connections = payload.optJSONObject("connections");
        JSONObject models = payload.optJSONObject("models");
        JSONObject selection = payload.optJSONObject("selection");
        JSONArray providers = payload.optJSONArray("providers");
        String[] providerIds = new String[providers == null ? 0 : providers.length()];
        String[] providerNames = new String[providerIds.length];
        if (providers != null) {
            for (int i = 0; i < providers.length(); i++) {
                try {
                    JSONObject provider = providers.getJSONObject(i);
                    providerIds[i] = provider.optString("id", DEFAULT_PROVIDER);
                    providerNames[i] = provider.optString("name", providerIds[i]);
                } catch (JSONException ignored) {
                    providerIds[i] = DEFAULT_PROVIDER;
                    providerNames[i] = "OpenAI";
                }
            }
        }
        return new ManagementOpenAiState(
                payload.optString("provider", DEFAULT_PROVIDER),
                payload.optString("accessPath", "platform"),
                payload.optBoolean("connected", false),
                connections != null && connections.optBoolean("platform", false),
                connections != null && connections.optBoolean("subscription", false),
                selection != null ? selection.optString("text", null) : null,
                selection != null ? selection.optString("realtime", null) : null,
                selection != null ? selection.optString("reasoning", "none") : "none",
                providerIds,
                providerNames,
                toArray(models, "text"),
                toArray(models, "realtime"),
                null,
                false,
                true);
    }

    public String selectedProviderLabel() {
        for (int i = 0; i < providerIds.length; i++) {
            if (providerIds[i].equals(provider)) {
                return providerNames[i];
            }
        }
        return provider;
    }

    private static String[] toArray(JSONObject source, String key) {
        if (source == null) return new String[0];
        JSONArray array = source.optJSONArray(key);
        if (array == null) return new String[0];
        String[] values = new String[array.length()];
        for (int i = 0; i < array.length(); i++) {
            values[i] = array.optString(i, "");
        }
        return values;
    }

    public String fallbackMessage() {
        return message == null || message.isBlank() ? null : message;
    }
}

