package com.resonolabs.voice;

import android.graphics.Canvas;
import android.graphics.Paint;
import android.content.Context;
import android.view.MotionEvent;
import android.view.View;
import android.os.Handler;
import android.os.Looper;

import com.resonolabs.ui.design.ReSonoTheme;
import com.resonolabs.runtime.host.BackgroundRunSnapshot;

import java.util.List;

/** One persistent native owner for product identity and Voice/Cards navigation. */
final class ProductChromeView extends View {
    private static final float WIDTH = 480f;
    private static final float HEIGHT = 142f;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Runnable openSettings;
    private final Runnable openVoice;
    private final Runnable openCards;
    private final Runnable openRunner;
    private final Handler animation = new Handler(Looper.getMainLooper());
    private boolean cardsActive;
    private boolean runnerVisible;
    private boolean runnerActive;
    private int animationFrame;
    private final Runnable animate = new Runnable() {
        @Override public void run() {
            if (!runnerActive) return;
            animationFrame++; invalidate(); animation.postDelayed(this, 320L);
        }
    };

    ProductChromeView(Context context, Runnable openSettings, Runnable openVoice,
                      Runnable openCards, Runnable openRunner) {
        super(context);
        this.openSettings = openSettings;
        this.openVoice = openVoice;
        this.openCards = openCards;
        this.openRunner = openRunner;
        setContentDescription("ReSono navigation. Voice tab, Cards tab, and device settings.");
    }

    void showRuns(List<BackgroundRunSnapshot> runs) {
        boolean wasActive = runnerActive;
        runnerVisible = !runs.isEmpty();
        runnerActive = runs.stream().anyMatch(BackgroundRunSnapshot::active);
        if (runnerActive && !wasActive) animation.post(animate);
        if (!runnerActive) animation.removeCallbacks(animate);
        invalidate();
    }

    void showCards(boolean active) {
        cardsActive = active;
        invalidate();
    }

    @Override protected void onDraw(Canvas canvas) {
        canvas.drawColor(ReSonoTheme.BACKGROUND);
        canvas.save();
        canvas.scale(getWidth() / WIDTH, getHeight() / HEIGHT);
        drawVoiceMark(canvas);
        ReSonoTheme.text(canvas, paint, "Voice", 74f, 57f, 29f,
                ReSonoTheme.INK, Paint.Align.LEFT, false);
        drawDeviceIcon(canvas);
        if (runnerVisible) drawRunner(canvas);
        ReSonoTheme.text(canvas, paint, "Voice", 96f, 119f, 20f,
                cardsActive ? ReSonoTheme.MUTED : ReSonoTheme.INK, Paint.Align.CENTER, false);
        ReSonoTheme.text(canvas, paint, "Cards", 350f, 119f, 20f,
                cardsActive ? ReSonoTheme.INK : ReSonoTheme.MUTED, Paint.Align.CENTER, false);
        paint.setColor(ReSonoTheme.LINE);
        canvas.drawRect(0f, 140f, WIDTH, 142f, paint);
        paint.setColor(ReSonoTheme.MINT);
        canvas.drawRect(cardsActive ? 240f : 18f, 139f, cardsActive ? 480f : 220f, 142f, paint);
        canvas.restore();
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        if (event.getActionMasked() != MotionEvent.ACTION_UP) return true;
        float x = event.getX() * WIDTH / Math.max(1f, getWidth());
        float y = event.getY() * HEIGHT / Math.max(1f, getHeight());
        if (runnerVisible && x >= 185f && x <= 365f && y <= 86f) openRunner.run();
        else if (x >= 392f && y <= 94f) openSettings.run();
        else if (y >= 88f && x < 240f) openVoice.run();
        else if (y >= 88f) openCards.run();
        return true;
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

    private void drawRunner(Canvas canvas) {
        int color = runnerActive ? ReSonoTheme.CYAN : ReSonoTheme.MINT;
        float phase = runnerActive && animationFrame % 2 == 0 ? 4f : -4f;
        paint.setColor(color); paint.setStrokeWidth(3f); paint.setStyle(Paint.Style.STROKE);
        canvas.drawCircle(274f, 30f, 6f, paint);
        canvas.drawLine(270f, 38f, 260f + phase, 51f, paint);
        canvas.drawLine(267f, 42f, 282f, 44f + phase / 2f, paint);
        canvas.drawLine(260f + phase, 51f, 250f, 62f, paint);
        canvas.drawLine(260f + phase, 51f, 276f, 61f, paint);
        paint.setStyle(Paint.Style.FILL);
    }
}
