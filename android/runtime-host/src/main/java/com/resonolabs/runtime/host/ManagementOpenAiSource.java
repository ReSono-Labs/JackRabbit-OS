package com.resonolabs.runtime.host;

import android.content.Context;

import java.util.function.Consumer;

public interface ManagementOpenAiSource {
    void load(Context context, Consumer<ManagementOpenAiState> callback);
    void connect(Context context, String apiKey, Consumer<ManagementOpenAiState> callback);
    void disconnect(Context context, Consumer<ManagementOpenAiState> callback);
    void setProvider(Context context, String provider, Consumer<ManagementOpenAiState> callback);
    void setAccessPath(Context context, String accessPath, Consumer<ManagementOpenAiState> callback);
    void setModels(
            Context context,
            String textModel,
            String realtimeModel,
            String reasoningEffort,
            Consumer<ManagementOpenAiState> callback);
    void refresh(Context context, Consumer<ManagementOpenAiState> callback);
}

