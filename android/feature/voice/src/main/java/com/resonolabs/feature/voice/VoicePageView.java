package com.resonolabs.feature.voice;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;

import com.resonolabs.ui.design.ReSonoTheme;
import com.resonolabs.ui.input.UiInputIntent;

/** Renders the service-owned Voice session and forwards explicit user actions. */
public final class VoicePageView extends View implements AutoCloseable, VoiceSessionHandoff {
    private static final float WIDTH = 480f;
    private static final float HEIGHT = 640f;
    private static final int MICROPHONE_PERMISSION_REQUEST = 41;
    private enum TouchAction { NONE, CONTINUOUS, STOP, HANDOFF }

    private final Activity activity;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final VoiceSessionController controller;
    private final Runnable openHandoff;
    private final Runnable sessionChanged = this::refresh;
    private TouchAction touchAction = TouchAction.NONE;

    public VoicePageView(Activity activity, Runnable openHandoff) {
        super(activity);
        this.activity = activity;
        this.openHandoff = openHandoff;
        controller = VoiceSessionService.controller(activity);
        controller.addListener(sessionChanged);
        setFocusable(true);
        setFocusableInTouchMode(true);
        refresh();
    }

    public boolean onInput(UiInputIntent intent) {
        if (intent == UiInputIntent.ACTIVATE) {
            toggleContinuous();
            return true;
        }
        if (intent == UiInputIntent.BACK && controller.active()) {
            controller.stopSession();
            return true;
        }
        return false;
    }

    public boolean onSideButton(KeyEvent event) {
        if (event.getAction() == KeyEvent.ACTION_DOWN) {
            if (event.getRepeatCount() == 0 && !controller.pressed()) {
                if (requireMicrophone()) controller.keyDown(event.getEventTime());
            }
        } else if (event.getAction() == KeyEvent.ACTION_UP) {
            controller.keyUp(event.getEventTime(), event.isCanceled());
        } else {
            controller.cancelPress();
        }
        return true;
    }

    public boolean isSideButtonPressed() {
        return controller.pressed();
    }

    public void releaseSideButtonForLifecycle() {
        controller.releasePressForLifecycle();
    }

    private boolean requireMicrophone() {
        if (activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                == PackageManager.PERMISSION_GRANTED) return true;
        activity.requestPermissions(
                new String[]{Manifest.permission.RECORD_AUDIO}, MICROPHONE_PERMISSION_REQUEST);
        return false;
    }

    private void toggleContinuous() {
        if (controller.continuous() || requireMicrophone()) controller.toggleContinuous();
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        TouchAction target = touchTarget(event.getX(), event.getY());
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN -> touchAction = target;
            case MotionEvent.ACTION_MOVE -> {
                if (target != touchAction) touchAction = TouchAction.NONE;
            }
            case MotionEvent.ACTION_UP -> {
                TouchAction action = touchAction;
                touchAction = TouchAction.NONE;
                if (action == TouchAction.NONE || action != target) return true;
                performClick();
                switch (action) {
                    case CONTINUOUS -> toggleContinuous();
                    case STOP -> controller.stopSession();
                    case HANDOFF -> openHandoff.run();
                    default -> { }
                }
            }
            case MotionEvent.ACTION_CANCEL -> touchAction = TouchAction.NONE;
            default -> { }
        }
        return true;
    }

    @Override public boolean performClick() {
        super.performClick();
        return true;
    }

    private TouchAction touchTarget(float rawX, float rawY) {
        float x = rawX * WIDTH / Math.max(1f, getWidth());
        float y = rawY * HEIGHT / Math.max(1f, getHeight());
        if (y >= 168f && y <= 216f) {
            if (x >= 34f && x <= 266f && !controller.pressed()) return TouchAction.CONTINUOUS;
            if (x >= 282f && x <= 446f && controller.active()) return TouchAction.STOP;
        }
        if (x >= 142f && x <= 338f && y >= 565f && y <= 615f && isAvailable()) {
            return TouchAction.HANDOFF;
        }
        return TouchAction.NONE;
    }

    private void refresh() {
        setContentDescription("ReSono Voice. " + headline() + ". "
                + (controller.microphoneOpen() ? "Microphone open. " : "Microphone closed. ")
                + (controller.continuous() ? "Continuous conversation on. " : "Push to talk. ")
                + "Hold the side button to speak; release to send. "
                + "Tap Continuous to change input mode."
                + (controller.active() ? " Tap End session to disconnect." : "")
                + (isAvailable() ? " Hand to Voice opens the camera." : ""));
        invalidate();
    }

    @Override public void close() {
        controller.removeListener(sessionChanged);
        controller.releasePressForLifecycle();
    }

    @Override protected void onDraw(Canvas canvas) {
        canvas.drawColor(ReSonoTheme.BACKGROUND);
        canvas.save();
        canvas.scale(getWidth() / WIDTH, getHeight() / HEIGHT);
        VoiceSessionStateTracker.State state = controller.state();
        int accent = state == VoiceSessionStateTracker.State.ERROR ? ReSonoTheme.RED
                : state == VoiceSessionStateTracker.State.CONNECTING ? ReSonoTheme.AMBER
                : controller.microphoneOpen() || controller.playing()
                ? ReSonoTheme.MINT : ReSonoTheme.CYAN;

        drawControl(canvas, 34f, 168f, 266f, 216f,
                controller.continuous() ? "Continuous: On" : "Continuous: Off",
                controller.pressed() ? ReSonoTheme.MUTED
                        : controller.continuous() ? ReSonoTheme.MINT : ReSonoTheme.INK);
        if (controller.active()) {
            drawControl(canvas, 282f, 168f, 446f, 216f, "End session", ReSonoTheme.INK);
        }

        if (controller.pressed()) {
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(accent);
            paint.setAlpha(36);
            canvas.drawCircle(240f, 300f, 72f, paint);
            paint.setAlpha(255);
        }
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(controller.pressed() ? 4f : 2.5f);
        paint.setColor(accent);
        canvas.drawCircle(240f, 300f, 72f, paint);
        drawMicrophone(canvas, 240f, 300f, accent, controller.microphoneOpen());

        ReSonoTheme.text(canvas, paint, headline(), 240f, 410f, 27f,
                ReSonoTheme.INK, Paint.Align.CENTER, false);
        String input = controller.microphoneOpen() ? "MIC: OPEN" : "MIC: CLOSED";
        String output = controller.playing() ? "PLAYING"
                : state == VoiceSessionStateTracker.State.RESPONDING ? "THINKING" : "QUIET";
        ReSonoTheme.text(canvas, paint, input + "  ·  OUTPUT: " + output, 240f, 440f, 12f,
                state == VoiceSessionStateTracker.State.ERROR ? ReSonoTheme.RED : ReSonoTheme.MUTED,
                Paint.Align.CENTER, true);
        String detail = state == VoiceSessionStateTracker.State.IDLE
                ? "Hold the side button to speak. Release to send."
                : controller.transcript();
        drawWrapped(canvas, detail, 52f, 480f, 376f, 17f,
                state == VoiceSessionStateTracker.State.ERROR ? ReSonoTheme.RED : ReSonoTheme.MUTED);
        if (isAvailable()) {
            drawControl(canvas, 142f, 565f, 338f, 615f, "Hand to Voice", ReSonoTheme.MINT);
        }
        canvas.restore();
    }

    private String headline() {
        VoiceSessionStateTracker.State state = controller.state();
        if (state == VoiceSessionStateTracker.State.ERROR) return "Voice unavailable";
        if (controller.pressed()) {
            return controller.microphoneOpen() ? "Release to send" : "Preparing to listen";
        }
        if (state == VoiceSessionStateTracker.State.CONNECTING) return "Opening voice session";
        if (controller.sending()) return "Sending";
        if (controller.playing()) return "Answering";
        if (state == VoiceSessionStateTracker.State.RESPONDING) return "Thinking";
        if (controller.microphoneOpen()) return "Listening";
        return "Hold side button to speak";
    }

    private void drawControl(Canvas canvas, float left, float top, float right, float bottom,
                             String label, int color) {
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(2f);
        paint.setColor(ReSonoTheme.LINE);
        canvas.drawRoundRect(left, top, right, bottom, 20f, 20f, paint);
        ReSonoTheme.text(canvas, paint, label, (left + right) / 2f, (top + bottom) / 2f + 6f,
                17f, color, Paint.Align.CENTER, true);
    }

    private void drawMicrophone(Canvas canvas, float centerX, float centerY, int color,
                                boolean open) {
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
        if (!open) canvas.drawLine(centerX - 33f, centerY - 35f, centerX + 33f, centerY + 40f, paint);
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

    @Override public boolean isAvailable() {
        return controller.isAvailable();
    }

    @Override public boolean submitImage(byte[] image, String mimeType, String filename) {
        return controller.submitImage(image, mimeType, filename);
    }
}
