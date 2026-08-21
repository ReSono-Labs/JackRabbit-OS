package com.resonolabs.feature.creationimport.qr;

/** Decodes one captured JPEG; it never validates or installs a Creation. */
public interface CreationQrDecoder {
    String decode(byte[] jpeg) throws DecodeFailure;

    final class DecodeFailure extends Exception {
        public DecodeFailure(String message) { super(message); }
    }
}
