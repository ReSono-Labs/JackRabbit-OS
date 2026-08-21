package com.resonolabs.feature.creationimport.qr;

import android.app.Activity;
import android.view.TextureView;
import android.widget.FrameLayout;

import com.resonolabs.feature.camera.Camera2Producer;
import com.resonolabs.feature.camera.CapturedImage;
import com.resonolabs.hardware.motor.MotorController;

/** Outward-only capture owner. Every exit returns the rotating camera to privacy. */
public final class CreationQrCaptureView extends FrameLayout implements AutoCloseable {
    public interface Listener {
        void onPositioning();
        void onLive();
        void onCaptured(CapturedImage image);
        void onFailure(String message);
    }

    private final Activity activity;
    private final MotorController motor;
    private final Listener listener;
    private final TextureView preview;
    private Camera2Producer producer;
    private boolean returnHomePending;

    public CreationQrCaptureView(Activity activity, MotorController motor, Listener listener) {
        super(activity); this.activity = activity; this.motor = motor; this.listener = listener;
        preview = new TextureView(activity);
        addView(preview, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT));
    }

    public void start() {
        stopCamera();
        listener.onPositioning();
        motor.moveTo(MotorController.Position.OUTWARD, (state, position) -> activity.runOnUiThread(() -> {
            if (!isShown()) return;
            if (state == MotorController.State.AT_POSITION && position == MotorController.Position.OUTWARD) open();
            else if (state == MotorController.State.FAILED) listener.onFailure("Camera motor failed");
            else if (state == MotorController.State.UNAVAILABLE) listener.onFailure("Camera motor unavailable");
        }));
    }

    private void open() {
        producer = new Camera2Producer(activity, preview, new Camera2Producer.Listener() {
            @Override public void onPreviewLive() { listener.onLive(); }
            @Override public void onCaptured(CapturedImage image) {
                listener.onCaptured(image);
                stopCamera();
            }
            @Override public void onFailure(String code) { listener.onFailure("Camera unavailable"); stopCamera(); }
            @Override public void onCameraClosed() {
                if (returnHomePending) { returnHomePending = false; motor.returnHome(); }
            }
        });
        producer.open(MotorController.Position.OUTWARD);
    }

    public void capture() { if (producer != null) producer.capture(); }

    public void stopCamera() {
        Camera2Producer closing = producer; producer = null; returnHomePending = true;
        if (closing != null) closing.close();
        else { returnHomePending = false; motor.returnHome(); }
    }

    @Override public void close() { stopCamera(); }
}
