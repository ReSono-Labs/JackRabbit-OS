package com.resonolabs.feature.camera;

import android.annotation.SuppressLint;
import android.content.Context;
import android.graphics.ImageFormat;
import android.graphics.Matrix;
import android.graphics.SurfaceTexture;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.hardware.camera2.params.StreamConfigurationMap;
import android.media.Image;
import android.media.ImageReader;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Size;
import android.view.Surface;
import android.view.TextureView;

import com.resonolabs.hardware.motor.MotorController;

import java.nio.ByteBuffer;
import java.util.Arrays;
import java.util.Comparator;

/** Camera2 preview/capture owner. It never moves the motor, navigates, stores, or contacts Voice. */
public final class Camera2Producer implements AutoCloseable {
    public interface Listener {
        void onPreviewLive();
        void onCaptured(CapturedImage image);
        void onFailure(String code);
        void onCameraClosed();
    }

    private final Context context;
    private final TextureView preview;
    private final Listener listener;
    private final Handler main = new Handler(android.os.Looper.getMainLooper());
    private HandlerThread thread;
    private Handler cameraHandler;
    private CameraDevice camera;
    private CameraCaptureSession session;
    private ImageReader reader;
    private Size previewSize;
    private int sensorOrientation;
    private int lensFacing = CameraCharacteristics.LENS_FACING_BACK;
    private boolean closed;
    private boolean closeNotified;

    public Camera2Producer(Context context, TextureView preview, Listener listener) {
        this.context = context.getApplicationContext();
        this.preview = preview;
        this.listener = listener;
    }

    /** Caller may invoke only after MotorController reports AT_POSITION for this position. */
    @SuppressLint("MissingPermission")
    public void open(MotorController.Position position) {
        if (closed || !preview.isAvailable()) { fail("preview_unavailable"); return; }
        stopCamera();
        closeNotified = false;
        thread = new HandlerThread("resono-camera2");
        thread.start();
        cameraHandler = new Handler(thread.getLooper());
        try {
            CameraManager manager = context.getSystemService(CameraManager.class);
            if (manager == null) throw new CameraAccessException(CameraAccessException.CAMERA_ERROR);
            int requested = position == MotorController.Position.INWARD
                    ? CameraCharacteristics.LENS_FACING_FRONT : CameraCharacteristics.LENS_FACING_BACK;
            String id = chooseCamera(manager, requested);
            CameraCharacteristics characteristics = manager.getCameraCharacteristics(id);
            lensFacing = value(characteristics.get(CameraCharacteristics.LENS_FACING), requested);
            sensorOrientation = value(characteristics.get(CameraCharacteristics.SENSOR_ORIENTATION), 0);
            StreamConfigurationMap map = characteristics.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP);
            if (map == null) throw new CameraAccessException(CameraAccessException.CAMERA_ERROR);
            previewSize = choosePreviewSize(map.getOutputSizes(SurfaceTexture.class), preview.getWidth(), preview.getHeight(), rotationRequired());
            Size capture = chooseCaptureSize(map.getOutputSizes(ImageFormat.JPEG));
            reader = ImageReader.newInstance(capture.getWidth(), capture.getHeight(), ImageFormat.JPEG, 2);
            reader.setOnImageAvailableListener(this::readCapturedImage, cameraHandler);
            configureTransform();
            manager.openCamera(id, stateCallback, cameraHandler);
        } catch (Exception error) { fail("camera_unavailable"); }
    }

    public void capture() {
        if (closed || camera == null || session == null || reader == null) return;
        try {
            CaptureRequest.Builder request = camera.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE);
            request.addTarget(reader.getSurface());
            request.set(CaptureRequest.JPEG_ORIENTATION, sensorOrientation);
            session.capture(request.build(), new CameraCaptureSession.CaptureCallback() {}, cameraHandler);
        } catch (CameraAccessException error) { fail("capture_failed"); }
    }

    private final CameraDevice.StateCallback stateCallback = new CameraDevice.StateCallback() {
        @Override public void onOpened(CameraDevice value) { if (closed) value.close(); else { camera = value; createSession(); } }
        @Override public void onDisconnected(CameraDevice value) { value.close(); fail("camera_disconnected"); }
        @Override public void onError(CameraDevice value, int error) { value.close(); fail("camera_unavailable"); }
        @Override public void onClosed(CameraDevice value) { notifyCameraClosed(); }
    };

    private void createSession() {
        try {
            SurfaceTexture texture = preview.getSurfaceTexture();
            if (texture == null || previewSize == null || camera == null || reader == null) { fail("preview_unavailable"); return; }
            texture.setDefaultBufferSize(previewSize.getWidth(), previewSize.getHeight());
            Surface surface = new Surface(texture);
            CaptureRequest.Builder request = camera.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
            request.addTarget(surface);
            camera.createCaptureSession(Arrays.asList(surface, reader.getSurface()), new CameraCaptureSession.StateCallback() {
                @Override public void onConfigured(CameraCaptureSession value) {
                    if (closed || camera == null) { value.close(); return; }
                    session = value;
                    try { value.setRepeatingRequest(request.build(), null, cameraHandler); main.post(listener::onPreviewLive); }
                    catch (CameraAccessException error) { fail("preview_failed"); }
                }
                @Override public void onConfigureFailed(CameraCaptureSession value) { fail("preview_failed"); }
            }, cameraHandler);
        } catch (CameraAccessException error) { fail("preview_failed"); }
    }

    private void readCapturedImage(ImageReader source) {
        try (Image image = source.acquireNextImage()) {
            if (image == null) return;
            ByteBuffer buffer = image.getPlanes()[0].getBuffer();
            byte[] bytes = new byte[buffer.remaining()]; buffer.get(bytes);
            CapturedImage captured = new CapturedImage(bytes, "IMG_" + System.currentTimeMillis() + ".jpg", "image/jpeg");
            main.post(() -> listener.onCaptured(captured));
        } catch (Exception error) { fail("capture_failed"); }
    }

    private void configureTransform() {
        main.post(() -> {
            if (previewSize == null || preview.getWidth() == 0 || preview.getHeight() == 0) return;
            float width = preview.getWidth(), height = preview.getHeight();
            int display = displayDegrees(); boolean rotate = relativeRotation(sensorOrientation, display, lensFacing) % 180 != 0;
            float scaleX = rotate ? width / previewSize.getHeight() : width / previewSize.getWidth();
            float scaleY = rotate ? height / previewSize.getWidth() : height / previewSize.getHeight();
            float fill = Math.max(scaleX, scaleY); Matrix matrix = new Matrix();
            matrix.setScale(fill / scaleX, fill / scaleY, width / 2f, height / 2f);
            matrix.postRotate(-display, width / 2f, height / 2f);
            preview.setTransform(matrix);
        });
    }

    private boolean rotationRequired() { return relativeRotation(sensorOrientation, displayDegrees(), lensFacing) % 180 != 0; }
    private int displayDegrees() { return switch (preview.getDisplay() == null ? Surface.ROTATION_0 : preview.getDisplay().getRotation()) { case Surface.ROTATION_90 -> 90; case Surface.ROTATION_180 -> 180; case Surface.ROTATION_270 -> 270; default -> 0; }; }
    static int relativeRotation(int sensor, int display, int facing) { int sign = facing == CameraCharacteristics.LENS_FACING_FRONT ? 1 : -1; return (sensor - display * sign + 360) % 360; }
    private static int value(Integer value, int fallback) { return value == null ? fallback : value; }
    private static String chooseCamera(CameraManager manager, int facing) throws CameraAccessException { String fallback = null; for (String id : manager.getCameraIdList()) { if (fallback == null) fallback = id; if (value(manager.getCameraCharacteristics(id).get(CameraCharacteristics.LENS_FACING), -1) == facing) return id; } if (fallback == null) throw new CameraAccessException(CameraAccessException.CAMERA_ERROR); return fallback; }
    private static Size choosePreviewSize(Size[] values, int width, int height, boolean rotate) { if (values == null || values.length == 0) return new Size(640,480); double target = width <= 0 || height <= 0 ? .75 : (double)width/height; return Arrays.stream(values).filter(v -> v.getWidth() <= 1920 && v.getHeight() <= 1080).min(Comparator.comparingDouble(v -> Math.abs((rotate ? (double)v.getHeight()/v.getWidth() : (double)v.getWidth()/v.getHeight()) - target))).orElse(values[0]); }
    private static Size chooseCaptureSize(Size[] values) { if (values == null || values.length == 0) return new Size(1280,720); return Arrays.stream(values).filter(v -> (long)v.getWidth()*v.getHeight() <= 8_000_000L).max(Comparator.comparingLong(v -> (long)v.getWidth()*v.getHeight())).orElse(values[0]); }
    private void fail(String code) { main.post(() -> listener.onFailure(code)); stopCamera(); }
    public void stopCamera() {
        CameraDevice closingCamera = camera;
        if (session != null) session.close();
        if (closingCamera != null) closingCamera.close();
        if (reader != null) reader.close();
        session=null; camera=null; reader=null;
        if (thread != null) thread.quitSafely();
        thread=null; cameraHandler=null;
        if (closingCamera == null) notifyCameraClosed();
        else main.postDelayed(this::notifyCameraClosed, 1_500L);
    }
    private void notifyCameraClosed() {
        if (closeNotified) return;
        closeNotified = true;
        listener.onCameraClosed();
    }
    @Override public void close() { if (!closed) { closed=true; stopCamera(); } }
}
