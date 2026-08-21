package com.resonolabs.runtime.host;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/** Compact native projection of the canonical background-run record. */
public record BackgroundRunSnapshot(
        String runId, String objective, String state, String label, String activity,
        float fraction, int modelTurns, int toolCalls, String createdAt, String completedAt,
        String outcome, List<TimelineEntry> timeline) {
    public record TimelineEntry(String label, String createdAt) { }

    public boolean active() {
        return !"completed".equals(state) && !"failed".equals(state) && !"cancelled".equals(state);
    }

    static BackgroundRunSnapshot fromJson(JSONObject item) {
        JSONObject progress = item.optJSONObject("progress");
        JSONObject output = item.optJSONObject("output");
        JSONObject failure = item.optJSONObject("failure");
        List<TimelineEntry> events = new ArrayList<>();
        JSONArray timeline = progress == null ? null : progress.optJSONArray("timeline");
        if (timeline != null) {
            for (int index = Math.max(0, timeline.length() - 6); index < timeline.length(); index++) {
                JSONObject event = timeline.optJSONObject(index);
                if (event != null) events.add(new TimelineEntry(
                        event.optString("label", "Activity recorded"),
                        event.optString("createdAt", "")));
            }
        }
        String outcome = "";
        if (failure != null) outcome = failure.optString("message", "Run stopped");
        else if (output != null) outcome = output.optString("summary", "Result committed");
        return new BackgroundRunSnapshot(
                item.optString("runId"), item.optString("objective"), item.optString("state"),
                progress == null ? item.optString("state") : progress.optString("label"),
                progress == null ? "" : progress.optString("activity"),
                (float) (progress == null ? 0d : progress.optDouble("fraction", 0d)),
                progress == null ? 0 : progress.optInt("modelTurns"),
                progress == null ? 0 : progress.optInt("toolCalls"),
                item.optString("createdAt"), item.optString("completedAt"), outcome,
                List.copyOf(events));
    }
}
