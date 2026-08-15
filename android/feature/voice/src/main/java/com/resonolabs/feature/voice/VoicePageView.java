package com.resonolabs.feature.voice;

import android.app.Activity;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.Manifest;
import android.content.pm.PackageManager;
import android.view.MotionEvent;
import android.view.View;

import com.resonolabs.runtime.host.RuntimeVoiceClient;
import com.resonolabs.ui.design.ReSonoTheme;
import com.resonolabs.ui.input.UiInputIntent;

import org.json.JSONObject;

/** Real Voice page. Every visible state is driven by the native/provider session. */
public final class VoicePageView extends View implements AutoCloseable {
    private static final float WIDTH = 480f;
    private static final float HEIGHT = 640f;
    private final Activity activity;
    private final Runnable openSettings;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final StringBuilder assistantDraft = new StringBuilder();
    private final VoiceSessionStateTracker sessionState = new VoiceSessionStateTracker();
    private RuntimeVoiceClient runtimeClient;
    private NativeVoicePeer peer;
    private String transcript = "Tap to start a conversation";
    private String failure = "";
    private JSONObject pendingConnectGreeting;

    public VoicePageView(Activity activity, Runnable openSettings) {
        super(activity);
        this.activity = activity;
        this.openSettings = openSettings;
        setContentDescription("ReSono Voice. Tap the center or press the side button to talk.");
        setFocusable(true);
        setFocusableInTouchMode(true);
    }

    public boolean onInput(UiInputIntent intent) {
        if (intent == UiInputIntent.ACTIVATE) toggle();
        else if (intent == UiInputIntent.BACK
                && sessionState.state() != VoiceSessionStateTracker.State.IDLE) stopSession();
        return true;
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        if (event.getActionMasked() != MotionEvent.ACTION_UP) return true;
        float x = event.getX() * WIDTH / Math.max(1f, getWidth());
        float y = event.getY() * HEIGHT / Math.max(1f, getHeight());
        if (x >= 392f && y <= 94f) openSettings.run();
        else if (y >= 150f && y <= 480f) toggle();
        return true;
    }

    private void toggle() {
        VoiceSessionStateTracker.State state = sessionState.state();
        if (state == VoiceSessionStateTracker.State.CONNECTING
                || state == VoiceSessionStateTracker.State.LIVE
                || state == VoiceSessionStateTracker.State.RESPONDING) {
            stopSession();
        } else {
            startSession();
        }
    }

    private void startSession() {
        if (activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            activity.requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 41);
            fail("microphone-required");
            return;
        }
        closeTransports();
        failure = "";
        transcript = "Connecting to Voice…";
        sessionState.connecting();
        invalidate();
        runtimeClient = new RuntimeVoiceClient();
        peer = new NativeVoicePeer(activity, new NativeVoicePeer.Listener() {
            @Override public void onOffer(String sdp) {
                activity.runOnUiThread(() -> requestAnswer(sdp));
            }

            @Override public void onLive() {
                activity.runOnUiThread(() -> {
                    sessionState.live();
                    transcript = "I’m listening";
                    if (pendingConnectGreeting != null && peer != null) {
                        peer.sendRealtimeEvent(pendingConnectGreeting);
                        pendingConnectGreeting = null;
                    }
                    invalidate();
                });
            }

            @Override public void onRealtimeEvent(String json) {
                activity.runOnUiThread(() -> handleRealtimeEvent(json));
            }

            @Override public void onFailure(String reason) {
                activity.runOnUiThread(() -> fail(reason));
            }
        });
        peer.createOffer();
    }

    private void requestAnswer(String offer) {
        if (runtimeClient == null) return;
        runtimeClient.createCall(activity, offer, new RuntimeVoiceClient.Callback() {
            @Override public void onAnswer(String sdp, JSONObject connectGreetingEvent) {
                pendingConnectGreeting = connectGreetingEvent;
                if (peer != null) peer.applyAnswer(sdp);
            }

            @Override public void onFailure(String reason) {
                fail(reason);
            }
        });
    }

    private void handleRealtimeEvent(String json) {
        try {
            JSONObject event = new JSONObject(json);
            String type = event.optString("type");
            sessionState.onRealtimeEvent(type);
            if ("input_audio_buffer.speech_started".equals(type)) {
                transcript = "Listening…";
            } else if ("input_audio_buffer.speech_stopped".equals(type)) {
                transcript = "Generating reply…";
            } else if ("conversation.item.input_audio_transcription.completed".equals(type)
                    || "conversation.item.input_audio_transcript.completed".equals(type)) {
                String text = event.optString("transcript", "").trim();
                if (!text.isEmpty()) transcript = text;
            } else if ("response.audio_transcript.delta".equals(type)
                    || "response.output_audio_transcript.delta".equals(type)) {
                assistantDraft.append(event.optString("delta", ""));
                if (assistantDraft.length() > 0) transcript = assistantDraft.toString();
            } else if ("response.audio_transcript.done".equals(type)
                    || "response.output_audio_transcript.done".equals(type)) {
                String text = event.optString("transcript", assistantDraft.toString()).trim();
                assistantDraft.setLength(0);
                if (!text.isEmpty()) transcript = text;
            } else if ("response.function_call_arguments.done".equals(type)) {
                callTool(event);
            } else if ("error".equals(type)) {
                fail("provider-error");
                return;
            }
            invalidate();
        } catch (Exception ignored) {
            fail("event-invalid");
        }
    }

    private void stopSession() {
        closeTransports();
        assistantDraft.setLength(0);
        sessionState.idle();
        transcript = "Tap to start a conversation";
        failure = "";
        invalidate();
    }

    private void fail(String reason) {
        closeTransports();
        sessionState.error();
        failure = messageFor(reason);
        transcript = failure;
        invalidate();
    }

    private void closeTransports() {
        if (peer != null) peer.close();
        if (runtimeClient != null) runtimeClient.close();
        peer = null;
        runtimeClient = null;
        pendingConnectGreeting = null;
    }

    @Override public void close() {
        closeTransports();
    }

    @Override protected void onDraw(Canvas canvas) {
        canvas.drawColor(ReSonoTheme.BACKGROUND);
        canvas.save();
        canvas.scale(getWidth() / WIDTH, getHeight() / HEIGHT);
        drawVoiceMark(canvas);
        ReSonoTheme.text(canvas, paint, "Voice", 74f, 57f, 29f,
                ReSonoTheme.INK, Paint.Align.LEFT, false);
        drawDeviceIcon(canvas);

        ReSonoTheme.text(canvas, paint, "Voice", 96f, 119f, 20f,
                ReSonoTheme.INK, Paint.Align.CENTER, false);
        ReSonoTheme.text(canvas, paint, "Cards", 350f, 119f, 20f,
                ReSonoTheme.MUTED, Paint.Align.CENTER, false);
        paint.setColor(ReSonoTheme.LINE);
        canvas.drawRect(0f, 140f, WIDTH, 142f, paint);
        paint.setColor(ReSonoTheme.MINT);
        canvas.drawRect(18f, 139f, 220f, 142f, paint);

        VoiceSessionStateTracker.State state = sessionState.state();
        int accent = state == VoiceSessionStateTracker.State.ERROR ? ReSonoTheme.RED
                : state == VoiceSessionStateTracker.State.CONNECTING ? ReSonoTheme.AMBER
                : state == VoiceSessionStateTracker.State.LIVE
                || state == VoiceSessionStateTracker.State.RESPONDING
                ? ReSonoTheme.MINT : ReSonoTheme.CYAN;
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(2.5f);
        paint.setColor(accent);
        canvas.drawCircle(240f, 300f, 72f, paint);
        drawMicrophone(canvas, 240f, 300f, accent);

        String headline = switch (state) {
            case IDLE -> "Touch to Start";
            case CONNECTING -> "Opening voice session";
            case LIVE -> "Listening";
            case RESPONDING -> "Responding";
            case ERROR -> "Voice unavailable";
        };
        ReSonoTheme.text(canvas, paint, headline, 240f, 410f, 29f,
                ReSonoTheme.INK, Paint.Align.CENTER, false);
        String sessionLabel = switch (state) {
            case IDLE -> "SESSION: IDLE";
            case CONNECTING -> "STATE: CONNECTING";
            case LIVE -> "STATE: LIVE";
            case RESPONDING -> "STATE: RESPONDING";
            case ERROR -> "STATE: ERROR";
        };
        ReSonoTheme.text(canvas, paint, sessionLabel, 240f, 440f, 12f,
                state == VoiceSessionStateTracker.State.ERROR ? ReSonoTheme.RED : ReSonoTheme.MINT,
                Paint.Align.CENTER, true);
        String detail = state == VoiceSessionStateTracker.State.IDLE
                ? "Press to start a voice session" : transcript;
        drawWrapped(canvas, detail, 52f, 480f, 376f, 17f,
                state == VoiceSessionStateTracker.State.ERROR ? ReSonoTheme.RED : ReSonoTheme.MUTED);
        canvas.restore();
    }

    private void drawVoiceMark(Canvas canvas) {
        paint.setColor(ReSonoTheme.MINT);
        paint.setStrokeWidth(4f);
        paint.setStrokeCap(Paint.Cap.SQUARE);
        float[] heights = {17f, 31f, 47f, 27f, 35f, 18f};
        for (int index = 0; index < heights.length; index++) {
            float x = 25f + index * 6f;
            canvas.drawLine(x, 49f - heights[index] / 2f, x, 49f + heights[index] / 2f, paint);
        }
        paint.setStrokeCap(Paint.Cap.BUTT);
    }

    private void drawDeviceIcon(Canvas canvas) {
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(2.4f);
        paint.setColor(ReSonoTheme.MUTED);
        canvas.drawRoundRect(414f, 27f, 440f, 63f, 5f, 5f, paint);
        canvas.drawLine(424f, 57f, 430f, 57f, paint);
        paint.setStyle(Paint.Style.FILL);
    }

    private void drawMicrophone(Canvas canvas, float centerX, float centerY, int color) {
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(4f);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setColor(color);
        RectF body = new RectF(centerX - 14f, centerY - 30f, centerX + 14f, centerY + 17f);
        canvas.drawRoundRect(body, 14f, 14f, paint);
        RectF arc = new RectF(centerX - 28f, centerY - 6f, centerX + 28f, centerY + 34f);
        canvas.drawArc(arc, 0f, 180f, false, paint);
        canvas.drawLine(centerX, centerY + 34f, centerX, centerY + 45f, paint);
        canvas.drawLine(centerX - 9f, centerY + 45f, centerX + 9f, centerY + 45f, paint);
        paint.setStrokeCap(Paint.Cap.BUTT);
        paint.setStyle(Paint.Style.FILL);
    }

    private void drawWrapped(Canvas canvas, String value, float x, float y, float width,
                             float size, int color) {
        paint.setTextSize(size);
        String remaining = value == null ? "" : value.trim();
        for (int line = 0; line < 3 && !remaining.isEmpty(); line++) {
            int count = paint.breakText(remaining, true, width, null);
            if (count < remaining.length()) {
                int space = remaining.lastIndexOf(' ', Math.max(0, count - 1));
                if (space > 0) count = space;
            }
            String text = remaining.substring(0, Math.max(1, count)).trim();
            if (line == 2 && count < remaining.length()) text = text + "…";
            ReSonoTheme.text(canvas, paint, text, x, y + line * 26f, size, color, Paint.Align.LEFT, false);
            remaining = remaining.substring(Math.min(remaining.length(), Math.max(1, count))).trim();
        }
    }

    private static String messageFor(String reason) {
        return switch (reason) {
            case "credential_unavailable" -> "Connect OpenAI in R1 settings.";
            case "model_required", "unsupported_model" -> "Choose a Realtime model in R1 settings.";
            case "credential_rejected" -> "OpenAI rejected this credential.";
            case "provider_unavailable" -> "OpenAI is currently unreachable.";
            case "runtime-unavailable" -> "The on-device runtime is unavailable.";
            case "microphone-required" -> "Allow microphone access, then tap to try again.";
            default -> "Voice could not start. Tap to try again.";
        };
    }

    private void callTool(JSONObject event) {
        if (runtimeClient == null || peer == null) return;
        String name = event.optString("name", "");
        String callId = event.optString("call_id", "");
        if (name.isBlank() || callId.isBlank()) return;
        JSONObject arguments;
        try {
            arguments = new JSONObject(event.optString("arguments", "{}"));
        } catch (Exception ignored) {
            arguments = new JSONObject();
        }
        runtimeClient.callTool(activity, name, arguments, new RuntimeVoiceClient.ToolCallback() {
            @Override public void onResult(String output) {
                sendToolOutput(callId, output);
            }

            @Override public void onFailure(String reason) {
                sendToolOutput(callId,
                        "{\"isError\":true,\"message\":\"The on-device tool is unavailable.\"}");
            }
        });
    }

    private void sendToolOutput(String callId, String output) {
        if (peer == null) return;
        try {
            boolean outputSent = peer.sendRealtimeEvent(new JSONObject()
                    .put("type", "conversation.item.create")
                    .put("item", new JSONObject()
                            .put("type", "function_call_output")
                            .put("call_id", callId)
                            .put("output", output)));
            boolean responseSent = peer.sendRealtimeEvent(
                    new JSONObject().put("type", "response.create"));
            if (!outputSent || !responseSent) {
                fail("event-invalid");
                return;
            }
            sessionState.toolOutputSent();
            invalidate();
        } catch (Exception ignored) {
            fail("event-invalid");
        }
    }
}
