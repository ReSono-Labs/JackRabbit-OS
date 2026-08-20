package com.resonolabs.feature.camera;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;

import java.io.ByteArrayOutputStream;

/** Produces a bounded JPEG for one WebRTC Realtime data-channel event. */
final class RealtimeImageEncoder {
    static final int MAX_JPEG_BYTES = 150 * 1024;
    private static final int MAX_DIMENSION = 960;

    private RealtimeImageEncoder() {}

    static byte[] encode(byte[] source) {
        Bitmap decoded = BitmapFactory.decodeByteArray(source, 0, source.length);
        if (decoded == null) throw new IllegalArgumentException("Captured image is invalid.");
        Bitmap scaled = scale(decoded, MAX_DIMENSION);
        if (scaled != decoded) decoded.recycle();
        try {
            for (int quality : new int[]{76, 66, 56, 46, 36}) {
                byte[] value = jpeg(scaled, quality);
                if (value.length <= MAX_JPEG_BYTES) return value;
            }
            Bitmap smaller = scale(scaled, 640);
            if (smaller != scaled) scaled.recycle();
            scaled = smaller;
            byte[] value = jpeg(scaled, 40);
            if (value.length <= MAX_JPEG_BYTES) return value;
            throw new IllegalArgumentException("Captured image is too detailed to send safely.");
        } finally {
            scaled.recycle();
        }
    }

    private static Bitmap scale(Bitmap source, int maximum) {
        int width = source.getWidth(), height = source.getHeight();
        int longest = Math.max(width, height);
        if (longest <= maximum) return source;
        float ratio = maximum / (float) longest;
        return Bitmap.createScaledBitmap(
                source, Math.max(1, Math.round(width * ratio)),
                Math.max(1, Math.round(height * ratio)), true);
    }

    private static byte[] jpeg(Bitmap value, int quality) {
        ByteArrayOutputStream output = new ByteArrayOutputStream(MAX_JPEG_BYTES);
        if (!value.compress(Bitmap.CompressFormat.JPEG, quality, output))
            throw new IllegalArgumentException("Captured image could not be encoded.");
        return output.toByteArray();
    }
}
