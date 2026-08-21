package com.resonolabs.feature.creationimport.qr;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;

import com.google.zxing.BinaryBitmap;
import com.google.zxing.DecodeHintType;
import com.google.zxing.RGBLuminanceSource;
import com.google.zxing.MultiFormatReader;
import com.google.zxing.BarcodeFormat;
import com.google.zxing.common.HybridBinarizer;

import java.util.List;
import java.util.Map;

/** ZXing-backed still-image decoder constrained to QR codes. */
public final class ZxingCreationQrDecoder implements CreationQrDecoder {
    @Override public String decode(byte[] jpeg) throws DecodeFailure {
        Bitmap bitmap = BitmapFactory.decodeByteArray(jpeg, 0, jpeg.length);
        if (bitmap == null) throw new DecodeFailure("Photo could not be read");
        try {
            Bitmap bounded = bounded(bitmap, 1800);
            try {
                String value = attempt(bounded);
                if (value != null) return value;
                for (float fraction : new float[]{0.82f, 0.68f, 0.54f}) {
                    int width = Math.max(1, Math.round(bounded.getWidth() * fraction));
                    int height = Math.max(1, Math.round(bounded.getHeight() * fraction));
                    Bitmap center = Bitmap.createBitmap(bounded,
                            (bounded.getWidth() - width) / 2,
                            (bounded.getHeight() - height) / 2, width, height);
                    try {
                        value = attempt(center);
                        if (value != null) return value;
                    } finally { center.recycle(); }
                }
                throw new DecodeFailure("No Creation QR code found");
            } finally { if (bounded != bitmap) bounded.recycle(); }
        } finally { bitmap.recycle(); }
    }

    private static Bitmap bounded(Bitmap source, int maximum) {
        int largest = Math.max(source.getWidth(), source.getHeight());
        if (largest <= maximum) return source;
        float scale = maximum / (float) largest;
        return Bitmap.createScaledBitmap(source, Math.max(1, Math.round(source.getWidth() * scale)),
                Math.max(1, Math.round(source.getHeight() * scale)), true);
    }

    private static String attempt(Bitmap bitmap) {
        int width = bitmap.getWidth(), height = bitmap.getHeight();
        int[] pixels = new int[width * height];
        bitmap.getPixels(pixels, 0, width, 0, 0, width, height);
        BinaryBitmap source = new BinaryBitmap(new HybridBinarizer(
                new RGBLuminanceSource(width, height, pixels)));
        try {
            String value = new MultiFormatReader().decode(source,
                    Map.of(DecodeHintType.POSSIBLE_FORMATS, List.of(BarcodeFormat.QR_CODE),
                           DecodeHintType.TRY_HARDER, Boolean.TRUE,
                           DecodeHintType.ALSO_INVERTED, Boolean.TRUE)).getText();
            return value == null || value.isBlank() ? null : value.trim();
        } catch (com.google.zxing.NotFoundException error) { return null; }
    }
}
