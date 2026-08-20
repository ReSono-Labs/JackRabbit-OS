package com.resonolabs.feature.camera;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.view.MotionEvent;
import android.view.TextureView;
import android.view.View;
import android.widget.FrameLayout;

import com.resonolabs.feature.voice.VoiceSessionHandoff;
import com.resonolabs.hardware.motor.MotorController;
import com.resonolabs.ui.design.ReSonoTheme;

/** Full-screen capture/review/send composition. Voice and provider transport remain external owners. */
public final class CameraHandoffPage extends FrameLayout implements AutoCloseable {
    private enum State { POSITIONING, OPENING, LIVE, REVIEW, SENDING, ERROR }
    private static final int CAMERA_PERMISSION_REQUEST = 2402;
    private final Activity activity;
    private final MotorController motor;
    private final VoiceSessionHandoff voice;
    private final Runnable returnToVoice;
    private final TextureView preview;
    private final Controls controls;
    private Camera2Producer producer;
    private CapturedImage captured;
    private Bitmap reviewBitmap;
    private boolean handoffMode;
    private boolean returnHomePending;
    private MotorController.Position activePosition = MotorController.Position.OUTWARD;
    private MotorController.Position positionAfterClose;
    private State state = State.POSITIONING;
    private String message = "Positioning camera";

    public CameraHandoffPage(Activity activity, MotorController motor, VoiceSessionHandoff voice,
                             Runnable returnToVoice) {
        super(activity);
        this.activity = activity; this.motor = motor; this.voice = voice; this.returnToVoice = returnToVoice;
        setBackgroundColor(Color.BLACK);
        preview = new TextureView(activity);
        controls = new Controls(activity);
        addView(preview, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT));
        addView(controls, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT));
        setContentDescription("Hand a photo to the current Voice session");
    }

    public void startPreview() { start(false); }
    public void startHandoff() { start(true); }

    private void start(boolean directHandoff) {
        handoffMode = directHandoff;
        activePosition = MotorController.Position.OUTWARD;
        clearReview();
        if (handoffMode && !voice.isAvailable()) { fail("Voice session ended"); return; }
        if (activity.checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            activity.requestPermissions(new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION_REQUEST);
            fail("Camera permission required");
            return;
        }
        state = State.POSITIONING; message = "Positioning camera"; controls.invalidate();
        moveThenOpen(activePosition);
    }

    private void moveThenOpen(MotorController.Position requested) {
        motor.moveTo(requested, (motorState, position) -> activity.runOnUiThread(() -> {
            if (!isShown()) return;
            if (motorState == MotorController.State.AT_POSITION && position == requested) openCamera();
            else if (motorState == MotorController.State.UNAVAILABLE) fail("Motor unavailable");
            else if (motorState == MotorController.State.FAILED) fail("Motor failed");
        }));
    }

    private void openCamera() {
        state = State.OPENING; message = "Opening camera"; controls.invalidate();
        producer = new Camera2Producer(activity, preview, new Camera2Producer.Listener() {
            @Override public void onPreviewLive() { state=State.LIVE; message=""; controls.invalidate(); }
            @Override public void onCaptured(CapturedImage image) { showReview(image); }
            @Override public void onFailure(String code) { fail(messageFor(code)); }
            @Override public void onCameraClosed() {
                if (returnHomePending) {
                    returnHomePending = false;
                    motor.returnHome();
                } else if (positionAfterClose != null) {
                    MotorController.Position requested = positionAfterClose;
                    positionAfterClose = null;
                    moveThenOpen(requested);
                }
            }
        });
        producer.open(activePosition);
    }

    private void switchFacing(MotorController.Position requested) {
        if (handoffMode || requested == activePosition || state != State.LIVE || producer == null) return;
        activePosition = requested;
        positionAfterClose = requested;
        state = State.POSITIONING;
        message = requested == MotorController.Position.OUTWARD ? "Turning outward" : "Turning toward you";
        controls.invalidate();
        producer.stopCamera();
    }

    private void capture() { if (state == State.LIVE && producer != null) producer.capture(); }
    private void showReview(CapturedImage image) {
        captured = image;
        reviewBitmap = BitmapFactory.decodeByteArray(image.bytes(), 0, image.bytes().length);
        if (producer != null) producer.stopCamera();
        state = State.REVIEW; message = "Review photo"; controls.invalidate();
    }
    private void retake() { clearReview(); openCamera(); }

    private void send() {
        if (state != State.REVIEW || captured == null || !voice.isAvailable()) { fail("Voice session ended"); return; }
        state=State.SENDING; message="Sending image..."; controls.invalidate();
        try {
            byte[] realtimeImage = RealtimeImageEncoder.encode(captured.bytes());
            if (voice.submitImage(realtimeImage, captured.mimeType(), captured.filename())) cancel();
            else fail("Image could not be sent");
        } catch (IllegalArgumentException error) {
            fail(error.getMessage());
        }
    }

    private void cancel() { stop(); returnToVoice.run(); }
    public void stop() {
        Camera2Producer closingProducer = producer;
        producer=null;
        returnHomePending = true;
        positionAfterClose = null;
        if (closingProducer != null) closingProducer.close();
        else { returnHomePending = false; motor.returnHome(); }
        clearReview();
    }
    private void clearReview() { captured=null; if (reviewBitmap != null) reviewBitmap.recycle(); reviewBitmap=null; }
    private void fail(String value) {
        state=State.ERROR; message=value; controls.invalidate();
        if (producer != null) {
            returnHomePending = true;
            producer.stopCamera();
        } else motor.returnHome();
    }
    private static String messageFor(String code) { return switch(code) { case "preview_unavailable" -> "Preview unavailable"; case "capture_failed" -> "Capture failed"; case "camera_disconnected" -> "Camera disconnected"; default -> "Camera unavailable"; }; }
    @Override public void close() { stop(); }

    private final class Controls extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        Controls(android.content.Context context) { super(context); }
        @Override protected void onDraw(Canvas canvas) {
            canvas.save(); canvas.scale(getWidth()/480f, getHeight()/640f);
            if (state == State.REVIEW && reviewBitmap != null) canvas.drawBitmap(reviewBitmap, null, new android.graphics.RectF(0,0,480,640), paint);
            paint.setColor(0xb0051120); canvas.drawRect(0,0,480,82,paint); canvas.drawRect(0,520,480,640,paint);
            ReSonoTheme.text(canvas,paint,handoffMode ? "HAND TO VOICE" : "CAMERA",24,50,17,ReSonoTheme.MINT,Paint.Align.LEFT,true);
            ReSonoTheme.text(canvas,paint,handoffMode ? "Cancel" : "Back",444,50,17,ReSonoTheme.INK,Paint.Align.RIGHT,false);
            if (state == State.LIVE && handoffMode) drawButton(canvas,240,574,"SNAP",ReSonoTheme.INK);
            else if (state == State.LIVE) {
                drawFacingButton(canvas,125,"Toward you",activePosition==MotorController.Position.INWARD);
                drawFacingButton(canvas,355,"Outward",activePosition==MotorController.Position.OUTWARD);
            }
            else if (state == State.REVIEW) { drawButton(canvas,326,574,"SEND",ReSonoTheme.MINT); ReSonoTheme.text(canvas,paint,"Retake",92,582,18,ReSonoTheme.INK,Paint.Align.CENTER,true); }
            else if (!message.isEmpty()) ReSonoTheme.text(canvas,paint,message,240,580,18,state==State.ERROR?ReSonoTheme.RED:ReSonoTheme.INK,Paint.Align.CENTER,true);
            canvas.restore();
        }
        private void drawButton(Canvas canvas,float x,float y,String label,int color){ paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(3);paint.setColor(color);canvas.drawCircle(x,y,42,paint);ReSonoTheme.text(canvas,paint,label,x,y+6,14,color,Paint.Align.CENTER,true); }
        private void drawFacingButton(Canvas canvas,float x,String label,boolean selected){paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(selected?3:1);paint.setColor(selected?ReSonoTheme.MINT:ReSonoTheme.MUTED);canvas.drawRoundRect(x-92,548,x+92,606,18,18,paint);paint.setStyle(Paint.Style.FILL);ReSonoTheme.text(canvas,paint,label,x,584,15,selected?ReSonoTheme.MINT:ReSonoTheme.INK,Paint.Align.CENTER,true);}
        @Override public boolean onTouchEvent(MotionEvent event){ if(event.getActionMasked()!=MotionEvent.ACTION_UP)return true;float x=event.getX()*480f/Math.max(1,getWidth()),y=event.getY()*640f/Math.max(1,getHeight());if(y<90&&x>350)cancel();else if(!handoffMode&&state==State.LIVE&&y>525){switchFacing(x<240?MotorController.Position.INWARD:MotorController.Position.OUTWARD);}else if(handoffMode&&state==State.LIVE&&y>515)capture();else if(handoffMode&&state==State.REVIEW&&y>515){if(x<180)retake();else send();}return true; }
    }
}
