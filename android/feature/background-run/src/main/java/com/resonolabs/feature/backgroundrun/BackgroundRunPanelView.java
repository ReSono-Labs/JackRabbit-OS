package com.resonolabs.feature.backgroundrun;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.os.Handler;
import android.os.Looper;
import android.view.MotionEvent;
import android.view.View;

import com.resonolabs.runtime.host.BackgroundRunSnapshot;
import com.resonolabs.runtime.host.RuntimeBackgroundRunClient;
import com.resonolabs.ui.design.ReSonoTheme;
import com.resonolabs.ui.input.UiInputIntent;
import com.resonolabs.ui.input.UiInputTarget;

import java.util.List;
import java.util.function.Consumer;

/** Tight 480x640 live run view; canonical history remains in management. */
public final class BackgroundRunPanelView extends View implements UiInputTarget {
    private static final float W = 480f, H = 640f;
    private final RuntimeBackgroundRunClient client;
    private final Consumer<List<BackgroundRunSnapshot>> observer;
    private final Runnable close;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Handler handler = new Handler(Looper.getMainLooper());
    private List<BackgroundRunSnapshot> runs = List.of();
    private boolean started;
    private final Runnable poll = new Runnable() {
        @Override public void run() {
            if (!started) return;
            client.load(getContext(), values -> {
                runs = values;
                observer.accept(values);
                invalidate();
                handler.postDelayed(this, 1500L);
            });
        }
    };

    public BackgroundRunPanelView(Context context, RuntimeBackgroundRunClient client,
                                  Consumer<List<BackgroundRunSnapshot>> observer, Runnable close) {
        super(context); this.client = client; this.observer = observer; this.close = close;
        setContentDescription("Background run activity");
    }

    public void start() { if (!started) { started = true; handler.post(poll); } }
    public void stop() { started = false; handler.removeCallbacks(poll); }

    public void opened() {
        if (runs.isEmpty()) return;
        BackgroundRunSnapshot item = runs.get(0);
        if (!item.active()) client.acknowledge(getContext(), item.runId(), () -> { });
    }

    @Override protected void onDraw(Canvas canvas) {
        canvas.drawColor(ReSonoTheme.BACKGROUND); canvas.save();
        canvas.scale(getWidth() / W, getHeight() / H);
        ReSonoTheme.text(canvas, paint, "‹", 28f, 53f, 42f, ReSonoTheme.CYAN, Paint.Align.CENTER, false);
        ReSonoTheme.text(canvas, paint, "Runner", 58f, 54f, 37f, ReSonoTheme.INK, Paint.Align.LEFT, true);
        if (runs.isEmpty()) {
            ReSonoTheme.text(canvas, paint, "No active or unread runs", 240f, 320f, 24f,
                    ReSonoTheme.MUTED, Paint.Align.CENTER, false);
            canvas.restore(); return;
        }
        BackgroundRunSnapshot run = runs.get(0);
        int accent = run.active() ? ReSonoTheme.CYAN
                : "completed".equals(run.state()) ? ReSonoTheme.MINT : 0xffff6b6b;
        ReSonoTheme.text(canvas, paint, run.state().toUpperCase(), 444f, 52f, 15f,
                accent, Paint.Align.RIGHT, true);
        drawWrapped(canvas, run.objective(), 24f, 104f, 432f, 25f, ReSonoTheme.INK, 3);
        paint.setColor(ReSonoTheme.LINE); canvas.drawRoundRect(24f, 190f, 456f, 198f, 4f, 4f, paint);
        paint.setColor(accent); canvas.drawRoundRect(24f, 190f,
                24f + 432f * Math.max(0f, Math.min(1f, run.fraction())), 198f, 4f, 4f, paint);
        ReSonoTheme.text(canvas, paint, run.label(), 24f, 229f, 22f, accent, Paint.Align.LEFT, true);
        drawWrapped(canvas, run.activity(), 24f, 260f, 432f, 18f, ReSonoTheme.MUTED, 2);
        ReSonoTheme.text(canvas, paint, run.modelTurns() + " turns  •  " + run.toolCalls() + " tools",
                24f, 313f, 17f, ReSonoTheme.MUTED, Paint.Align.LEFT, false);
        float y = 352f;
        for (BackgroundRunSnapshot.TimelineEntry event : run.timeline()) {
            paint.setColor(accent); canvas.drawCircle(28f, y - 5f, 3f, paint);
            String label = event.label().length() > 46 ? event.label().substring(0, 45) + "…" : event.label();
            ReSonoTheme.text(canvas, paint, label, 42f, y, 16f, ReSonoTheme.INK, Paint.Align.LEFT, false);
            y += 34f;
        }
        if (!run.outcome().isBlank()) drawWrapped(canvas, run.outcome(), 24f, 568f, 432f,
                17f, accent, 2);
        canvas.restore();
    }

    private void drawWrapped(Canvas canvas, String text, float x, float y, float width,
                             float size, int color, int maxLines) {
        paint.setTextSize(size);
        String remaining = text == null ? "" : text.trim();
        for (int line = 0; line < maxLines && !remaining.isEmpty(); line++) {
            int cut = remaining.length();
            while (cut > 1 && paint.measureText(remaining.substring(0, cut)) > width) cut--;
            if (cut < remaining.length()) {
                int space = remaining.lastIndexOf(' ', cut); if (space > 0) cut = space;
            }
            String value = remaining.substring(0, cut).trim();
            if (line == maxLines - 1 && cut < remaining.length()) value += "…";
            ReSonoTheme.text(canvas, paint, value, x, y + line * (size + 6f), size,
                    color, Paint.Align.LEFT, line == 0);
            remaining = remaining.substring(cut).trim();
        }
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        if (event.getActionMasked() != MotionEvent.ACTION_UP) return true;
        float x = event.getX() * W / Math.max(1f, getWidth());
        float y = event.getY() * H / Math.max(1f, getHeight());
        if (x < 90f && y < 82f) close.run();
        return true;
    }

    @Override public boolean onInput(UiInputIntent intent) {
        if (intent == UiInputIntent.BACK) { close.run(); return true; }
        return true;
    }
}
