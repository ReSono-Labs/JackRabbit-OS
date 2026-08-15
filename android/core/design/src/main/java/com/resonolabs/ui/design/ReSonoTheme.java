package com.resonolabs.ui.design;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;

public final class ReSonoTheme {
    public static final int BACKGROUND = Color.rgb(6, 22, 41);
    public static final int BACKGROUND_TOP = Color.rgb(4, 17, 31);
    public static final int INK = Color.rgb(237, 246, 255);
    public static final int MUTED = Color.rgb(159, 179, 202);
    public static final int VIOLET = Color.rgb(61, 137, 215);
    public static final int CYAN = Color.rgb(53, 201, 255);
    public static final int MINT = Color.rgb(114, 239, 207);
    public static final int PINK = Color.rgb(255, 122, 122);
    public static final int RED = Color.rgb(255, 122, 122);
    public static final int AMBER = Color.rgb(243, 201, 105);
    public static final int LINE = Color.argb(51, 166, 199, 224);
    public static final int PANEL = Color.rgb(10, 28, 50);
    public static final int PANEL_RAISED = Color.rgb(12, 33, 57);
    public static final int ORB_MID = Color.argb(105, 53, 201, 255);
    public static final int TRANSPARENT = Color.TRANSPARENT;

    private ReSonoTheme() {}

    public static void text(Canvas canvas, Paint paint, String value, float x, float baseline,
                            float size, int color, Paint.Align align, boolean bold) {
        paint.setShader(null);
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(color);
        paint.setTextAlign(align);
        paint.setTextSize(size);
        paint.setTypeface(Typeface.create("sans", bold ? Typeface.BOLD : Typeface.NORMAL));
        canvas.drawText(value == null ? "" : value, x, baseline, paint);
    }
}
