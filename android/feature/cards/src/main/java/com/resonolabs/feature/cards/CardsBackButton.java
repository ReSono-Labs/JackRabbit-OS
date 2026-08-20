package com.resonolabs.feature.cards;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.view.MotionEvent;
import android.view.View;

import com.resonolabs.ui.design.ReSonoTheme;

/** One visible return control for every Cards-owned content surface. */
final class CardsBackButton extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Runnable navigateBack;

    CardsBackButton(Context context, Runnable navigateBack) {
        super(context);
        this.navigateBack = navigateBack;
        setContentDescription("Back to Cards");
        setFocusable(true);
    }

    @Override protected void onDraw(Canvas canvas) {
        ReSonoTheme.text(canvas, paint, "‹", 25f, 53f, 43f,
                ReSonoTheme.INK, Paint.Align.LEFT, false);
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        if (event.getActionMasked() == MotionEvent.ACTION_UP) {
            navigateBack.run();
            performClick();
        }
        return true;
    }

    @Override public boolean performClick() {
        super.performClick();
        return true;
    }
}
