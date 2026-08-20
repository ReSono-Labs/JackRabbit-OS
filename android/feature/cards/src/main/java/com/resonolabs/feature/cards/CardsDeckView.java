package com.resonolabs.feature.cards;

import android.animation.ValueAnimator;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.View;

import com.resonolabs.ui.design.ReSonoTheme;
import com.resonolabs.ui.input.UiInputIntent;

import org.json.JSONArray;
import org.json.JSONObject;

/** Native rolodex for the real Creation catalog. Imported HTML runs elsewhere. */
final class CardsDeckView extends View {
    interface Activation { void open(JSONObject item); }

    private static final float WIDTH = 480f;
    private static final float HEIGHT = 640f;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Activation activation;
    private JSONArray items = new JSONArray();
    private int index;
    private float downY;
    private float settleOffset;

    CardsDeckView(android.content.Context context, Activation activation) {
        super(context);
        this.activation = activation;
        setFocusable(true);
        setContentDescription("Creation cards");
    }

    void showCatalog(JSONObject catalog) {
        items = catalog.optJSONArray("creations");
        if (items == null) items = new JSONArray();
        index = Math.min(index, Math.max(0, items.length() - 1));
        invalidate();
    }

    boolean onInput(UiInputIntent input) {
        if (input == UiInputIntent.PREVIOUS) move(-1);
        else if (input == UiInputIntent.NEXT) move(1);
        else if (input == UiInputIntent.ACTIVATE) activate();
        else return false;
        return true;
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        float y = event.getY() * HEIGHT / Math.max(1f, getHeight());
        float x = event.getX() * WIDTH / Math.max(1f, getWidth());
        if (event.getActionMasked() == MotionEvent.ACTION_DOWN) {
            downY = y;
            return true;
        }
        if (event.getActionMasked() != MotionEvent.ACTION_UP) return true;
        float delta = y - downY;
        if (Math.abs(delta) > 55f) move(delta < 0f ? 1 : -1);
        else if (y >= 560f && x <= 110f) move(-1);
        else if (y >= 560f && x >= 370f) move(1);
        else if (y >= 165f && y <= 500f) activate();
        return true;
    }

    private void move(int direction) {
        if (items.length() == 0) return;
        index = (index + direction + items.length()) % items.length();
        ValueAnimator animator = ValueAnimator.ofFloat(direction * 28f, 0f);
        animator.setDuration(260L);
        animator.addUpdateListener(value -> {
            settleOffset = (float) value.getAnimatedValue();
            invalidate();
        });
        animator.start();
    }

    private void activate() {
        JSONObject item = items.optJSONObject(index);
        if (item == null) return;
        String source = item.optString("sourceType", "local_archive");
        String entry = "rabbit_qr_link".equals(source)
                ? item.optString("entryUrl", "") : item.optString("entryAsset", "");
        if (("rabbit_qr_link".equals(source) && entry.startsWith("https://"))
                || ("local_archive".equals(source) && entry.startsWith("/v1/creations/"))) {
            activation.open(item);
        }
    }

    @Override protected void onDraw(Canvas canvas) {
        canvas.drawColor(ReSonoTheme.BACKGROUND);
        canvas.save();
        canvas.scale(getWidth() / WIDTH, getHeight() / HEIGHT);
        if (items.length() == 0) {
            ReSonoTheme.text(canvas, paint, "No Creations installed.", 240f, 350f, 18f,
                    ReSonoTheme.MUTED, Paint.Align.CENTER, false);
            ReSonoTheme.text(canvas, paint, "Import one from R1 management.", 240f, 380f, 16f,
                    ReSonoTheme.MUTED, Paint.Align.CENTER, false);
        } else {
            for (int depth = Math.min(2, items.length() - 1); depth >= 0; depth--) {
                int itemIndex = (index + depth) % items.length();
                drawCard(canvas, items.optJSONObject(itemIndex), depth);
            }
            drawDots(canvas);
        }
        drawArrow(canvas, 48f, false);
        drawArrow(canvas, 432f, true);
        canvas.restore();
    }

    private void drawCard(Canvas canvas, JSONObject item, int depth) {
        if (item == null) return;
        float inset = 20f + depth * 10f;
        float top = 190f - depth * 25f + (depth == 0 ? settleOffset : 0f);
        float bottom = top + 275f;
        int accent;
        try { accent = Color.parseColor(item.optString("accent", "#72efcf")); }
        catch (IllegalArgumentException ignored) { accent = ReSonoTheme.MINT; }
        paint.setColor(depth == 0 ? ReSonoTheme.PANEL : ReSonoTheme.PANEL_RAISED);
        canvas.drawRoundRect(new RectF(inset, top, WIDTH - inset, bottom), 14f, 14f, paint);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(1.5f);
        paint.setColor(ReSonoTheme.MUTED);
        canvas.drawRoundRect(new RectF(inset, top, WIDTH - inset, bottom), 14f, 14f, paint);
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(accent);
        canvas.drawRoundRect(new RectF(inset, top, inset + 6f, bottom), 6f, 6f, paint);
        if (depth != 0) return;
        ReSonoTheme.text(canvas, paint, "CREATION", inset + 20f, top + 36f, 13f,
                accent, Paint.Align.LEFT, true);
        ReSonoTheme.text(canvas, paint, "READY", WIDTH - inset - 18f, top + 36f, 13f,
                accent, Paint.Align.RIGHT, true);
        ReSonoTheme.text(canvas, paint, item.optString("title", "Creation"), inset + 20f,
                top + 79f, 29f, ReSonoTheme.INK, Paint.Align.LEFT, false);
        drawDescription(canvas, item.optString("description", ""), inset + 20f, top + 113f,
                WIDTH - inset * 2f - 40f);
    }

    private void drawDescription(Canvas canvas, String value, float x, float y, float width) {
        paint.setTextSize(17f);
        String remaining = value == null ? "" : value.trim();
        for (int line = 0; line < 3 && !remaining.isEmpty(); line++) {
            int count = paint.breakText(remaining, true, width, null);
            if (count < remaining.length()) {
                int space = remaining.lastIndexOf(' ', Math.max(0, count - 1));
                if (space > 0) count = space;
            }
            String text = remaining.substring(0, Math.max(1, count)).trim();
            if (line == 2 && count < remaining.length()) text += "…";
            ReSonoTheme.text(canvas, paint, text, x, y + line * 25f, 17f,
                    ReSonoTheme.MUTED, Paint.Align.LEFT, false);
            remaining = remaining.substring(Math.min(remaining.length(), Math.max(1, count))).trim();
        }
    }

    private void drawDots(Canvas canvas) {
        float total = Math.min(items.length(), 8) * 14f;
        float start = 240f - total / 2f + 7f;
        for (int dot = 0; dot < Math.min(items.length(), 8); dot++) {
            paint.setColor(dot == index ? ReSonoTheme.MINT : ReSonoTheme.MUTED);
            canvas.drawCircle(start + dot * 14f, 552f, dot == index ? 4f : 3f, paint);
        }
    }

    private void drawArrow(Canvas canvas, float centerX, boolean next) {
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(1.5f);
        paint.setColor(ReSonoTheme.LINE);
        canvas.drawRoundRect(new RectF(centerX - 24f, 575f, centerX + 24f, 623f), 12f, 12f, paint);
        paint.setStyle(Paint.Style.FILL);
        ReSonoTheme.text(canvas, paint, next ? "›" : "‹", centerX, 609f, 28f,
                ReSonoTheme.INK, Paint.Align.CENTER, false);
    }
}
