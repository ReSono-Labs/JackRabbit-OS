package com.resonolabs.feature.creationimport;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.view.MotionEvent;
import android.view.View;
import android.widget.FrameLayout;

import com.resonolabs.feature.camera.CapturedImage;
import com.resonolabs.feature.creationimport.qr.CreationQrCaptureView;
import com.resonolabs.feature.creationimport.qr.CreationQrDecoder;
import com.resonolabs.feature.creationimport.qr.ZxingCreationQrDecoder;
import com.resonolabs.hardware.motor.MotorController;
import com.resonolabs.runtime.host.RuntimeCreationImportClient;
import com.resonolabs.ui.design.ReSonoTheme;
import com.resonolabs.ui.input.UiInputIntent;
import com.resonolabs.ui.input.UiInputTarget;

import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Removable Settings-owned Creation QR capture, review, and confirmation flow. */
public final class CreationImportView extends FrameLayout implements UiInputTarget, AutoCloseable {
    private final Activity activity;
    private final RuntimeCreationImportClient client;
    private final Runnable close;
    private final CreationQrCaptureView capture;
    private final Overlay overlay;
    private final CreationQrDecoder decoder = new ZxingCreationQrDecoder();
    private final ExecutorService decodeWorker = Executors.newSingleThreadExecutor();
    private CreationImportState state = CreationImportState.POSITIONING;
    private String message = "Positioning camera";
    private String title = "";
    private String description = "";
    private String token = "";
    private boolean replace;
    private Bitmap capturedBitmap;

    public CreationImportView(Activity activity, MotorController motor,
                              RuntimeCreationImportClient client, Runnable close) {
        super(activity); this.activity = activity; this.client = client; this.close = close;
        capture = new CreationQrCaptureView(activity, motor, new CreationQrCaptureView.Listener() {
            @Override public void onPositioning() { update(CreationImportState.POSITIONING, "Positioning camera"); }
            @Override public void onLive() { update(CreationImportState.LIVE, "Frame the Creation QR code"); }
            @Override public void onCaptured(CapturedImage image) { decode(image); }
            @Override public void onFailure(String value) { update(CreationImportState.ERROR, value); }
        });
        overlay = new Overlay(activity);
        addView(capture, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT));
        addView(overlay, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT));
        setContentDescription("Import a Creation QR code");
    }

    public void start() { reset(); capture.start(); }
    public void stop() { capture.stopCamera(); clearBitmap(); }

    private void decode(CapturedImage image) {
        capturedBitmap = BitmapFactory.decodeByteArray(image.bytes(), 0, image.bytes().length);
        update(CreationImportState.DECODING, "Reading QR code");
        decodeWorker.execute(() -> {
            try {
                String raw = decoder.decode(image.bytes());
                JSONObject descriptor = new JSONObject(raw);
                activity.runOnUiThread(() -> preflight(descriptor));
            } catch (Exception error) {
                activity.runOnUiThread(() -> update(CreationImportState.ERROR,
                        error.getMessage() == null ? "This is not a supported Creation QR code" : error.getMessage()));
            }
        });
    }

    private void preflight(JSONObject descriptor) {
        update(CreationImportState.PREFLIGHT, "Checking Creation");
        client.preflight(activity, descriptor, value -> {
            JSONObject candidate = value.optJSONObject("candidate");
            title = candidate == null ? "Creation" : candidate.optString("title", "Creation");
            description = candidate == null ? "" : candidate.optString("description", "");
            token = value.optString("preflightToken", "");
            replace = value.optJSONObject("current") != null;
            update(CreationImportState.REVIEW, replace ? "This will replace the existing Creation" : "Ready to import");
        }, value -> update(CreationImportState.ERROR, value));
    }

    private void confirm() {
        if (token.isBlank()) return;
        update(CreationImportState.INSTALLING, replace ? "Replacing Creation" : "Importing Creation");
        client.confirm(activity, token, replace,
                ignored -> update(CreationImportState.SUCCESS, "Creation added to Cards"),
                value -> update(CreationImportState.ERROR, value));
    }

    private void retake() { reset(); capture.start(); }
    private void reset() { title=""; description=""; token=""; replace=false; clearBitmap(); }
    private void update(CreationImportState value, String text) { state=value; message=text; overlay.invalidate(); }
    private void clearBitmap() { if (capturedBitmap != null) capturedBitmap.recycle(); capturedBitmap=null; }
    private void exit() { stop(); close.run(); }

    @Override public boolean onInput(UiInputIntent intent) {
        if (intent == UiInputIntent.BACK) { exit(); return true; }
        if (intent == UiInputIntent.ACTIVATE && state == CreationImportState.LIVE) { capture.capture(); return true; }
        if (intent == UiInputIntent.ACTIVATE && state == CreationImportState.REVIEW) { confirm(); return true; }
        return true;
    }

    @Override public void close() { stop(); decodeWorker.shutdownNow(); }

    private final class Overlay extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        Overlay(Activity context) { super(context); }
        @Override protected void onDraw(Canvas canvas) {
            canvas.save(); canvas.scale(getWidth()/480f, getHeight()/640f);
            if (capturedBitmap != null && state != CreationImportState.LIVE && state != CreationImportState.POSITIONING)
                canvas.drawBitmap(capturedBitmap, null, new android.graphics.RectF(0,0,480,640), paint);
            paint.setColor(0xd9051120); canvas.drawRect(0,0,480,84,paint); canvas.drawRect(0,490,480,640,paint);
            ReSonoTheme.text(canvas,paint,"IMPORT CREATION",24,51,17,ReSonoTheme.MINT,Paint.Align.LEFT,true);
            ReSonoTheme.text(canvas,paint,"Cancel",447,51,17,ReSonoTheme.INK,Paint.Align.RIGHT,false);
            if (state == CreationImportState.REVIEW) drawReview(canvas);
            else if (state == CreationImportState.SUCCESS) {
                ReSonoTheme.text(canvas,paint,"CREATION ADDED",240,530,16,ReSonoTheme.MINT,Paint.Align.CENTER,true);
                ReSonoTheme.text(canvas,paint,"Done",240,590,25,ReSonoTheme.INK,Paint.Align.CENTER,true);
            } else {
                int color = state == CreationImportState.ERROR ? ReSonoTheme.RED : ReSonoTheme.INK;
                if (state == CreationImportState.LIVE) {
                    paint.setStyle(Paint.Style.STROKE); paint.setStrokeWidth(2); paint.setColor(ReSonoTheme.MINT);
                    canvas.drawRoundRect(54,126,426,470,18,18,paint); paint.setStyle(Paint.Style.FILL);
                }
                ReSonoTheme.text(canvas,paint,message,240,532,19,color,Paint.Align.CENTER,true);
                String action = state == CreationImportState.LIVE ? "SNAP" : state == CreationImportState.ERROR ? "RETAKE" : "";
                if (!action.isEmpty()) button(canvas,240,588,action,color);
            }
            canvas.restore();
        }
        private void drawReview(Canvas canvas) {
            paint.setColor(0xf00a1d31); canvas.drawRoundRect(18,314,462,624,22,22,paint);
            ReSonoTheme.text(canvas,paint,replace?"REPLACE CREATION":"NEW CREATION",42,353,15,
                    replace?0xffffd166:ReSonoTheme.MINT,Paint.Align.LEFT,true);
            String shown = title.length()>28?title.substring(0,27)+"…":title;
            ReSonoTheme.text(canvas,paint,shown,42,398,29,ReSonoTheme.INK,Paint.Align.LEFT,true);
            String detail = description.isBlank()?message:description;
            if(detail.length()>62)detail=detail.substring(0,61)+"…";
            ReSonoTheme.text(canvas,paint,detail,42,440,17,ReSonoTheme.MUTED,Paint.Align.LEFT,false);
            ReSonoTheme.text(canvas,paint,"Retake",94,574,18,ReSonoTheme.INK,Paint.Align.CENTER,true);
            button(canvas,332,570,replace?"REPLACE":"IMPORT",replace?0xffffd166:ReSonoTheme.MINT);
        }
        private void button(Canvas canvas,float x,float y,String label,int color){paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(3);paint.setColor(color);canvas.drawCircle(x,y,43,paint);paint.setStyle(Paint.Style.FILL);ReSonoTheme.text(canvas,paint,label,x,y+6,13,color,Paint.Align.CENTER,true);}
        @Override public boolean onTouchEvent(MotionEvent event) {
            if(event.getActionMasked()!=MotionEvent.ACTION_UP)return true;
            float x=event.getX()*480f/Math.max(1,getWidth()), y=event.getY()*640f/Math.max(1,getHeight());
            if(y<88&&x>350){exit();return true;}
            if(state==CreationImportState.LIVE&&y>510){capture.capture();return true;}
            if(state==CreationImportState.ERROR&&y>510){retake();return true;}
            if(state==CreationImportState.REVIEW&&y>520){if(x<180)retake();else confirm();return true;}
            if(state==CreationImportState.SUCCESS&&y>500){exit();return true;}
            return true;
        }
    }
}
