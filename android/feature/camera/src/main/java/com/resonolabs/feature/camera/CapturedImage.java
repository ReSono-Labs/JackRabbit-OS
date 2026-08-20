package com.resonolabs.feature.camera;

/** Immutable JPEG captured by Camera2; ownership transfers to the review flow. */
public record CapturedImage(byte[] bytes, String filename, String mimeType) {
    public CapturedImage {
        if (bytes == null || bytes.length == 0) throw new IllegalArgumentException("image bytes required");
        bytes = bytes.clone();
        if (filename == null || filename.isBlank()) throw new IllegalArgumentException("filename required");
        if (!"image/jpeg".equals(mimeType)) throw new IllegalArgumentException("JPEG required");
    }
    @Override public byte[] bytes() { return bytes.clone(); }
}
