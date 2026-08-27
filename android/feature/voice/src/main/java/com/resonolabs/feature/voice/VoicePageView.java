package com.resonolabs.feature.voice;

import android.app.Activity;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.RadialGradient;
import android.util.Log;
import android.Manifest;
import android.content.pm.PackageManager;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView;
import android.webkit.WebSettings;
import android.widget.FrameLayout;
import org.json.JSONArray;
import org.json.JSONObject;

import com.resonolabs.runtime.host.RuntimeVoiceClient;
import com.resonolabs.ui.design.ReSonoTheme;
import com.resonolabs.ui.input.UiInputIntent;

/** Voice page with Lili robot face rendered in WebView. */
public final class VoicePageView extends FrameLayout implements AutoCloseable, VoiceSessionHandoff {
    private static final String LOG_TAG = "VoicePageView";
    private static final float WIDTH = 480f;
    private static final float HEIGHT = 640f;
    private final Activity activity;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final StringBuilder assistantDraft = new StringBuilder();
    private final JSONArray recordedEntries = new JSONArray();
    private final VoiceSessionStateTracker sessionState = new VoiceSessionStateTracker();
    private RuntimeVoiceClient runtimeClient;
    private NativeVoicePeer peer;
    private String transcript = "Tap to start a conversation";
    private String failure = "";
    private JSONObject pendingConnectGreeting;
    private boolean liveSession = false;
    private boolean productLiveSession = false;
    private String liveGreetingText = "";
    private String sessionId = "";
    private String lastUserUtterance = "";
    private long userUtteranceId = 0;
    private final RealtimeResponseCoordinator responseCoordinator;
    private final RealtimeToolCallQueue toolCallQueue = new RealtimeToolCallQueue();
    private final Runnable openHandoff;
    private PendingModeTool pendingModeTool;
    private WebView robotWebView;
    private final Runnable modeUpdateTimeout = () -> {
        PendingModeTool pending = pendingModeTool;
        pendingModeTool = null;
        if (pending != null) { pending.completion.run(); fail("mode-update-timeout"); }
    };
    private final Runnable completionPoll = this::pollCompletion;

    private static final class PendingModeTool {
        final String callId; final String output; final Runnable completion;
        PendingModeTool(String c, String o, Runnable r) { callId=c; output=o; completion=r; }
    }

    public class RobotBridge {
        @android.webkit.JavascriptInterface
        public void log(String msg) { Log.d("LiliRobot", msg); }
    }

    public VoicePageView(Activity activity, Runnable openHandoff) {
        super(activity);
        this.activity = activity;
        this.openHandoff = openHandoff;
        this.responseCoordinator = new RealtimeResponseCoordinator(
                event -> peer != null && peer.sendRealtimeEvent(event),
                new RealtimeResponseCoordinator.Scheduler() {
                    @Override public void schedule(Runnable r, long d) { postDelayed(r, d); }
                    @Override public void cancel(Runnable r) { removeCallbacks(r); }
                },
                () -> fail("event-invalid"));
        setContentDescription("Lili Voice. Tap to talk.");
        setFocusable(true);
        setFocusableInTouchMode(true);

        // Robot yüz WebView
        robotWebView = new WebView(activity);
        WebSettings ws = robotWebView.getSettings();
        ws.setJavaScriptEnabled(true);
        robotWebView.setWebViewClient(new android.webkit.WebViewClient());
        robotWebView.setBackgroundColor(0xFF060E1A);
        robotWebView.setClickable(false);
        robotWebView.setLongClickable(false);
        robotWebView.setFocusable(false);
        robotWebView.setFocusableInTouchMode(false);
        robotWebView.addJavascriptInterface(new RobotBridge(), "LiliBridge");
        addView(robotWebView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));
        robotWebView.loadUrl("file:///android_asset/robot_face.html");
    }

    public boolean onInput(UiInputIntent intent) {
        if (intent == UiInputIntent.ACTIVATE) toggle();
        else if (intent == UiInputIntent.BACK
                && sessionState.state() != VoiceSessionStateTracker.State.IDLE) stopSession();
        return true;
    }

    @Override public boolean onInterceptTouchEvent(MotionEvent event) {
        return onTouchEvent(event);
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        if (event.getActionMasked() != MotionEvent.ACTION_UP) return true;
        float y = event.getY() * HEIGHT / Math.max(1f, getHeight());
        if (y >= 150f && y <= 480f) toggle();
        else if (y >= 555f && isAvailable()) openHandoff.run();
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

    private void updateRobotFace(String state) {
        if (robotWebView != null) {
            post(() -> robotWebView.evaluateJavascript(
                "setEyeState('" + state + "')", null));
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
        failure = ""; sessionId = ""; lastUserUtterance = ""; userUtteranceId = 0;
        responseCoordinator.reset(); toolCallQueue.reset(); clearPendingModeTool();
        clearRecordedEntries();
        transcript = "Connecting to Voice…";
        sessionState.connecting();
        updateRobotFace("connecting");
        invalidate();
        runtimeClient = new RuntimeVoiceClient();
        liveSession = false;
        productLiveSession = false;
        peer = new NativeVoicePeer(activity, new NativeVoicePeer.Listener() {
            @Override public void onOffer(String sdp) {
                activity.runOnUiThread(() -> requestAnswer(sdp));
            }
            @Override public void onLive() {
                activity.runOnUiThread(() -> {
                    sessionState.live();
                    updateRobotFace("thinking");
                    transcript = "I\u2019m listening";
                    if (liveSession) {
                        sendLiveGreeting();
                    } else if (pendingConnectGreeting != null && peer != null) {
                        responseCoordinator.request(pendingConnectGreeting);
                        pendingConnectGreeting = null;
                    }
                    invalidate();
                    scheduleCompletionPoll();
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
        Log.i(LOG_TAG, "voice offer sdp b64: " + android.util.Base64.encodeToString(offer.getBytes(), android.util.Base64.NO_WRAP));
        runtimeClient.createCall(activity, offer, new RuntimeVoiceClient.Callback() {
            @Override public void onAnswer(String sdp, String connectedSessionId, JSONObject connectGreetingEvent, boolean live, String greetingText, String transport) {
                Log.i(LOG_TAG, "voice session established sessionId=" + connectedSessionId + " live=" + live + " transport=" + transport);
                sessionId = connectedSessionId;
                pendingConnectGreeting = connectGreetingEvent;
                liveSession = live;
                productLiveSession = live && "live-product".equals(transport);
                liveGreetingText = greetingText;
                if (peer != null) peer.applyAnswer(sdp);
            }
            @Override public void onFailure(String reason) { fail(reason); }
        });
    }

    private void handleRealtimeEvent(String json) {
        try {
            JSONObject event = new JSONObject(json);
            String type = event.optString("type");
            if (liveSession) {
                handleLiveEvent(event, type);
                return;
            }
            sessionState.onRealtimeEvent(type);
            if ("response.created".equals(type)) { responseCoordinator.onResponseCreated(); updateRobotFace("responding"); }
            else if ("response.done".equals(type)) {
                responseCoordinator.onResponseDone();
                // TTS bitince sessizlik durumuna geç (3 sn gecikme)
                postDelayed(() -> updateRobotFace("thinking"), 3000);
            }
            if ("input_audio_buffer.speech_started".equals(type)) {
                transcript = "Listening…";
                updateRobotFace("listening");
            } else if ("input_audio_buffer.speech_stopped".equals(type)) {
                transcript = "Generating reply…";
                updateRobotFace("thinking");
            } else if ("conversation.item.input_audio_transcription.completed".equals(type)
                    || "conversation.item.input_audio_transcript.completed".equals(type)) {
                String text = event.optString("transcript", "").trim();
                lastUserUtterance = text;
                if (!text.isEmpty()) userUtteranceId += 1;
                recordTranscript("user", type, text);
                if (!text.isEmpty()) transcript = text;
            } else if ("response.audio_transcript.delta".equals(type)
                    || "response.output_audio_transcript.delta".equals(type)) {
                assistantDraft.append(event.optString("delta", ""));
                if (assistantDraft.length() > 0) transcript = assistantDraft.toString();
            } else if ("response.audio_transcript.done".equals(type)
                    || "response.output_audio_transcript.done".equals(type)) {
                String text = event.optString("transcript", assistantDraft.toString()).trim();
                recordTranscript("assistant", type, text);
                assistantDraft.setLength(0);
                if (!text.isEmpty()) transcript = text;
            } else if ("response.function_call_arguments.done".equals(type)) {
                callTool(event);
            } else if ("session.updated".equals(type)) {
                completePendingModeTool();
            } else if ("error".equals(type)) {
                Log.w(LOG_TAG, "Realtime provider error: " + event.optJSONObject("error"));
                JSONObject error = event.optJSONObject("error");
                String code = error == null ? "" : error.optString("code", "");
                String message = error == null ? "" : error.optString("message", "");
                if ("conversation_already_has_active_response".equals(code)
                        || message.contains("active response in progress")) {
                    responseCoordinator.onActiveResponseRejection();
                    invalidate();
                    return;
                }
                fail("provider-error");
                return;
            }
            invalidate();
        } catch (Exception ignored) {
            fail("event-invalid");
        }
    }

    /** AVAS (gpt-live-1) speaks the greeting as its first turn and streams the
     *  model audio as base64 PCM output_audio.delta events over the data channel.
     *  The session update must match the Codex frameless-bidi shape exactly
     *  ({audio: {output: {voice}}, delegation: {type: client}}); any unknown
     *  parameter (e.g. output_modalities) makes the broker reject the whole
     *  update, leaving audio output disabled and the model answering in text. */
    private void sendLiveGreeting() {
        if (peer == null) return;
        // Product Voice backend (/realtime/wm) pre-configures voice and
        // instructions at call time; any session.update closes the channel.
        if (productLiveSession) {
            transcript = "I\u2019m listening";
            updateRobotFace("listening");
            invalidate();
            return;
        }
        try {
            JSONObject session = new JSONObject()
                    .put("audio", new JSONObject()
                            .put("output", new JSONObject()
                                    .put("voice", "sol")))
                    .put("delegation", new JSONObject()
                            .put("ack_filler", false)
                            .put("type", "client"));
            if (peer.sendRealtimeEvent(new JSONObject()
                    .put("type", "session.update")
                    .put("session", session))) {
                if (liveGreetingText != null && !liveGreetingText.isEmpty()) {
                    JSONObject greeting = new JSONObject()
                            .put("type", "session.context.append")
                            .put("channel", "speakable")
                            .put("content", new org.json.JSONArray().put(
                                    new JSONObject().put("type", "input_text")
                                            .put("text", "Say exactly: \"" + liveGreetingText
                                                    + "\" Then stop and wait for the user.")));
                    if (peer.sendRealtimeEvent(greeting)) return;
                }
                return;
            }
        } catch (Exception ignored) {
        }
        transcript = "I\u2019m listening";
        updateRobotFace("listening");
    }

    private void handleLiveEvent(JSONObject event, String type) {
        if ("output_audio.delta".equals(type)) {
            String audioB64 = event.optString("audio", "");
            if (!audioB64.isEmpty() && peer != null) {
                peer.playPcm(android.util.Base64.decode(audioB64, android.util.Base64.DEFAULT));
            }
            invalidate();
            return;
        }
        if ("output_transcript.added".equals(type)) {
            JSONObject item = event.optJSONObject("item");
            String delta = item == null ? "" : item.optString("text", "");
            if (!delta.isEmpty()) {
                assistantDraft.append(delta);
                transcript = assistantDraft.toString();
            }
            invalidate();
            return;
        }
        if ("input_transcript.added".equals(type)) {
            JSONObject item = event.optJSONObject("item");
            String text = item == null ? "" : item.optString("text", "").trim();
            if (!text.isEmpty()) {
                lastUserUtterance = text;
                userUtteranceId += 1;
                recordTranscript("user", type, text);
                transcript = text;
            }
            invalidate();
            return;
        }
        if ("turn.done".equals(type)) {
            JSONObject turn = event.optJSONObject("turn");
            if (turn != null) {
                String role = turn.optString("role", "");
                String text = turn.optString("transcript", "").trim();
                if ("assistant".equals(role) && !text.isEmpty()) {
                    recordTranscript("assistant", type, text);
                    transcript = text;
                    assistantDraft.setLength(0);
                }
            }
            invalidate();
            return;
        }
        if ("delegation.created".equals(type)) {
            handleLiveDelegation(event, type);
            return;
        }
        if ("session.started".equals(type) || "session.updated".equals(type)) {
            invalidate();
            return;
        }
        if ("error".equals(type)) {
            // AVAS rejects events it does not support; surface but keep the
            // session alive so a single bad event does not kill the call.
            Log.w(LOG_TAG, "AVAS provider error: " + event.optJSONObject("error"));
            invalidate();
            return;
        }
        invalidate();
    }

    /** AVAS delegation: the model hands the turn to the client (e.g. to run an
     *  MCP/background tool). The free-form request is matched against the
     *  granted on-device tools and executed through the local MCP boundary;
     *  the result is returned via delegation.context.append so the model can
     *  speak the outcome. Always replying (even on failure) prevents the
     *  handoff loop observed as handoff_1..handoff_N. */
    private void handleLiveDelegation(JSONObject event, String type) {
        JSONObject item = event.optJSONObject("item");
        if (item == null || peer == null) { invalidate(); return; }
        final String delegationItemId = item.optString("id", "");
        final String requestText = extractDelegationText(item);
        if (delegationItemId.isEmpty()) { invalidate(); return; }
        if (!requestText.isEmpty()) recordTranscript("delegation", type, requestText);
        transcript = "Working: " + requestText;
        updateRobotFace("thinking");
        invalidate();
        if (runtimeClient == null) { sendDelegationResult(delegationItemId, "The client was unavailable to execute the delegation."); return; }
        runtimeClient.callDelegation(activity, sessionId, delegationItemId, requestText,
                new RuntimeVoiceClient.DelegationCallback() {
                    @Override public void onResult(String output) {
                        sendDelegationResult(delegationItemId, "Tool execution result: " + output);
                    }
                    @Override public void onFailure(String reason) {
                        sendDelegationResult(delegationItemId, "The client could not execute this delegation (" + reason
                                + "). Tell the user the action was not performed and ask how to proceed.");
                    }
                });
    }

    private String extractDelegationText(JSONObject item) {
        JSONArray content = item.optJSONArray("content");
        if (content != null && content.length() > 0) {
            return content.optJSONObject(0).optString("text", "");
        }
        return "";
    }

    private void sendDelegationResult(String delegationItemId, String text) {
        if (peer == null) return;
        try {
            peer.sendRealtimeEvent(new JSONObject()
                    .put("type", "delegation.context.append")
                    .put("delegation_item_id", delegationItemId)
                    .put("channel", "commentary")
                    .put("content", new JSONArray().put(new JSONObject()
                            .put("type", "input_text")
                            .put("text", text))));
        } catch (Exception ignored) {
            Log.w(LOG_TAG, "delegation result send failed");
        }
    }

    private void stopSession() {
        removeCallbacks(completionPoll);
        clearPendingModeTool();
        if (peer != null) { peer.close(); peer = null; }
        dispatchPendingFinalize();
        sessionState.idle();
        updateRobotFace("idle");
        transcript = "Tap to start a conversation";
        failure = ""; pendingConnectGreeting = null; sessionId = "";
        lastUserUtterance = ""; userUtteranceId = 0;
        assistantDraft.setLength(0);
        invalidate();
        if (runtimeClient != null) { runtimeClient.close(); runtimeClient = null; }
    }

    private void dispatchPendingFinalize() {
        if (sessionId == null || sessionId.isBlank()
                || recordedEntries.length() == 0 || runtimeClient == null) return;
        final String sessionToFinalize = sessionId;
        final RuntimeVoiceClient clientToFinalize = runtimeClient;
        runtimeClient = null;
        JSONArray entries = new JSONArray();
        for (int i = 0; i < recordedEntries.length(); i++) entries.put(recordedEntries.opt(i));
        clearRecordedEntries();
        clientToFinalize.finalizeVoiceSession(activity, sessionToFinalize, entries, new RuntimeVoiceClient.FinalizeCallback() {
            @Override public void onResult(JSONObject response) {
                Log.i(LOG_TAG, "session finalized: " + response.optString("sessionId", ""));
                clientToFinalize.close();
            }
            @Override public void onFailure(String reason) {
                Log.w(LOG_TAG, "session finalize failed: " + reason);
                clientToFinalize.close();
            }
        });
    }

    private void fail(String reason) {
        Log.w(LOG_TAG, "voice page failure reason=" + reason);
        dispatchPendingFinalize();
        closeTransports();
        sessionState.error();
        updateRobotFace("error");
        failure = messageFor(reason);
        transcript = failure;
        invalidate();
    }

    private void clearRecordedEntries() {
        while (recordedEntries.length() > 0) recordedEntries.remove(0);
    }

    private void closeTransports() {
        responseCoordinator.close(); toolCallQueue.close();
        if (peer != null) peer.close();
        if (runtimeClient != null) runtimeClient.close();
        peer = null; runtimeClient = null; pendingConnectGreeting = null;
    }

    @Override public void close() {
        dispatchPendingFinalize(); closeTransports();
    }

    private void recordTranscript(String role, String eventType, String text) {
        if (sessionId == null || sessionId.isBlank() || text == null || text.isBlank()) return;
        try {
            recordedEntries.put(new JSONObject().put("role", role).put("eventType", eventType).put("text", text));
        } catch (Exception ignored) {}
    }

    private void callTool(JSONObject event) {
        if (runtimeClient == null || peer == null) return;
        String name = event.optString("name", "");
        String callId = event.optString("call_id", "");
        if (name.isBlank() || callId.isBlank()) return;
        JSONObject arguments;
        try { arguments = new JSONObject(event.optString("arguments", "{}")); }
        catch (Exception ignored) { arguments = new JSONObject(); }
        final JSONObject toolArguments = arguments;
        toolCallQueue.enqueue(completion -> {
            if (runtimeClient == null || peer == null) { completion.complete(); return; }
            runtimeClient.callTool(activity, sessionId, callId, lastUserUtterance, userUtteranceId, name, toolArguments, new RuntimeVoiceClient.ToolCallback() {
                @Override public void onResult(String output, JSONObject sessionUpdate) {
                    if (sessionUpdate != null) {
                        beginModeUpdate(callId, output, sessionUpdate, completion::complete);
                    } else {
                        sendToolOutput(callId, output);
                        completion.complete();
                    }
                }
                @Override public void onFailure(String reason) {
                    sendToolOutput(callId, "{\"isError\":true,\"message\":\"Tool unavailable.\"}");
                    completion.complete();
                }
            });
        });
    }

    private void beginModeUpdate(String callId, String output, JSONObject sessionUpdate, Runnable completion) {
        if (peer == null || pendingModeTool != null) { completion.run(); fail("mode-update-conflict"); return; }
        pendingModeTool = new PendingModeTool(callId, output, completion);
        if (!peer.sendRealtimeEvent(sessionUpdate)) {
            PendingModeTool pending = pendingModeTool;
            pendingModeTool = null;
            pending.completion.run();
            fail("mode-update-invalid");
            return;
        }
        postDelayed(modeUpdateTimeout, 5000L);
    }

    private void completePendingModeTool() {
        PendingModeTool pending = pendingModeTool;
        if (pending == null) return;
        pendingModeTool = null;
        removeCallbacks(modeUpdateTimeout);
        sendToolOutput(pending.callId, pending.output);
        pending.completion.run();
    }

    private void clearPendingModeTool() {
        removeCallbacks(modeUpdateTimeout);
        PendingModeTool pending = pendingModeTool;
        pendingModeTool = null;
        if (pending != null) pending.completion.run();
    }

    private void scheduleCompletionPoll() {
        removeCallbacks(completionPoll);
        if (isAvailable() && runtimeClient != null) postDelayed(completionPoll, 2000L);
    }

    private void pollCompletion() {
        if (!isAvailable() || runtimeClient == null) return;
        if (pendingModeTool != null) { scheduleCompletionPoll(); return; }
        runtimeClient.pollCompletion(activity, sessionId, new RuntimeVoiceClient.CompletionCallback() {
            @Override public void onResult(JSONObject completion) {
                if (completion != null) deliverCompletion(completion);
                scheduleCompletionPoll();
            }
            @Override public void onFailure(String reason) { scheduleCompletionPoll(); }
        });
    }

    private void deliverCompletion(JSONObject completion) {
        if (peer == null || runtimeClient == null) return;
        String runId = completion.optString("runId", "").trim();
        if (runId.isEmpty()) return;
        try {
            JSONObject event = new JSONObject()
                    .put("type", "conversation.item.create")
                    .put("item", new JSONObject()
                            .put("type", "message")
                            .put("role", "user")
                            .put("content", new JSONArray().put(new JSONObject()
                                    .put("type", "input_text")
                                    .put("text", "Background goal completion: " + completion))));
            if (!peer.sendRealtimeEvent(event)) return;
            runtimeClient.acknowledgeCompletion(activity, sessionId, runId);
            responseCoordinator.requestDefault();
        } catch (Exception error) {
            Log.w(LOG_TAG, "background completion injection failed", error);
        }
    }

    private void sendToolOutput(String callId, String output) {
        if (peer == null) return;
        try {
            boolean sent = peer.sendRealtimeEvent(new JSONObject()
                    .put("type", "conversation.item.create")
                    .put("item", new JSONObject().put("type", "function_call_output")
                            .put("call_id", callId).put("output", output)));
            if (!sent) { fail("event-invalid"); return; }
            responseCoordinator.requestDefault();
            sessionState.toolOutputSent();
            invalidate();
        } catch (Exception ignored) { fail("event-invalid"); }
    }

    @Override public boolean isAvailable() {
        VoiceSessionStateTracker.State state = sessionState.state();
        return peer != null && sessionId != null && !sessionId.isBlank()
                && (state == VoiceSessionStateTracker.State.LIVE || state == VoiceSessionStateTracker.State.RESPONDING);
    }

    @Override public boolean submitImage(byte[] image, String mimeType, String filename) {
        if (!isAvailable() || image == null || image.length == 0
                || image.length > 160 * 1024 || mimeType == null || !mimeType.startsWith("image/")) return false;
        try {
            String imageUrl = "data:" + mimeType + ";base64," +
                    android.util.Base64.encodeToString(image, android.util.Base64.NO_WRAP);
            boolean sent = peer.sendRealtimeEvent(new JSONObject().put("type", "conversation.item.create")
                    .put("item", new JSONObject().put("type", "message").put("role", "user")
                            .put("content", new JSONArray().put(new JSONObject()
                                    .put("type", "input_image").put("image_url", imageUrl)))));
            if (!sent) return false;
            responseCoordinator.requestDefault();
            String t = "[Image handoff]";
            recordTranscript("user", "conversation.item.input_image.completed", t);
            sessionState.toolOutputSent(); transcript = t; invalidate();
            return true;
        } catch (Exception ignored) { return false; }
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
        int sep = reason.indexOf(":");
        if (sep > 0) {
            String code = reason.substring(0, sep);
            String detail = reason.substring(sep + 1).trim();
            if ("provider_unavailable".equals(code)) return "OpenAI is unavailable: " + detail;
            if ("provider_rejected".equals(code)) return "OpenAI rejected: " + detail;
            if ("credential_rejected".equals(code)) return "OpenAI credential issue: " + detail;
            if ("unsupported_model".equals(code)) return "Model rejected: " + detail;
            if ("openai_error".equals(code)) return detail;
            if (detail == null || detail.isBlank()) return messageFor(code);
        }
        return switch (reason) {
            case "credential_unavailable" -> "Connect OpenAI in R1 settings.";
            case "model_required", "unsupported_model" -> "Choose a Realtime model in settings.";
            case "credential_rejected" -> "OpenAI rejected this credential.";
            case "provider_unavailable" -> "OpenAI is currently unreachable.";
            case "runtime-unavailable" -> "The on-device runtime is unavailable.";
            case "microphone-required" -> "Allow microphone access.";
            default -> "Voice could not start. Tap to try again.";
        };
    }
}
