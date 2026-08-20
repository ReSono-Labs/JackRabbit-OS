package com.resonolabs.voice;

import android.graphics.Canvas;
import android.graphics.Paint;
import android.content.Context;
import android.view.MotionEvent;
import android.view.View;

import com.resonolabs.ui.design.ReSonoTheme;

/** One persistent native owner for product identity and Voice/Cards navigation. */
final class ProductChromeView extends View {
    private static final float WIDTH = 480f;
    private static final float HEIGHT = 142f;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Runnable openSettings;
    private final Runnable openVoice;
    private final Runnable openCards;
    private boolean cardsActive;

    ProductChromeView(Context context, Runnable openSettings, Runnable openVoice, Runnable openCards) {
        super(context);
        this.openSettings = openSettings;
        this.openVoice = openVoice;
        this.openCards = openCards;
        setContentDescription("ReSono navigation. Voice tab, Cards tab, and device settings.");
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
        if (x >= 392f && y <= 94f) openSettings.run();
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
}
