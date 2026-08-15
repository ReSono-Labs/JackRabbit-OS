package com.resonolabs.runtime.host;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Keystore-sealed provider credentials. Ciphertext is device-protected; plaintext is never persisted. */
final class RuntimeCredentialStore {
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "resono.runtime.credentials.v1";
    private static final String PLATFORM_RECORD = "openai_platform_key";
    private static final String SUBSCRIPTION_RECORD = "openai_subscription_tokens";
    private static final String VERSION = "v1";
    private static final int IV_BYTES = 12;
    private final SharedPreferences records;

    RuntimeCredentialStore(Context context) {
        Context deviceContext = context.createDeviceProtectedStorageContext();
        records = deviceContext.getSharedPreferences("runtime-provider-credentials", Context.MODE_PRIVATE);
    }

    synchronized boolean hasOpenAiPlatformKey() {
        return records.contains(PLATFORM_RECORD);
    }

    synchronized void putOpenAiPlatformKey(String value) throws GeneralSecurityException {
        String keyValue = value == null ? "" : value.trim();
        if (!keyValue.startsWith("sk-") || keyValue.length() < 20 || keyValue.length() > 512) {
            throw new IllegalArgumentException("OpenAI API key format is invalid");
        }
        putRecord(PLATFORM_RECORD, keyValue);
    }

    synchronized String getOpenAiPlatformKey() throws GeneralSecurityException {
        return getRecord(PLATFORM_RECORD);
    }

    synchronized void deleteOpenAiPlatformKey() throws GeneralSecurityException {
        deleteRecord(PLATFORM_RECORD);
    }

    synchronized boolean hasOpenAiSubscriptionTokens() {
        return records.contains(SUBSCRIPTION_RECORD);
    }

    synchronized void putOpenAiSubscriptionTokens(String value) throws GeneralSecurityException {
        String payload = value == null ? "" : value.trim();
        if (!payload.startsWith("{") || payload.length() < 10 || payload.length() > 65536) {
            throw new IllegalArgumentException("OpenAI subscription token record is invalid");
        }
        putRecord(SUBSCRIPTION_RECORD, payload);
    }

    synchronized String getOpenAiSubscriptionTokens() throws GeneralSecurityException {
        return getRecord(SUBSCRIPTION_RECORD);
    }

    synchronized void deleteOpenAiSubscriptionTokens() throws GeneralSecurityException {
        deleteRecord(SUBSCRIPTION_RECORD);
    }

    private void putRecord(String record, String value) throws GeneralSecurityException {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key());
        cipher.updateAAD(record.getBytes(StandardCharsets.UTF_8));
        byte[] encrypted = cipher.doFinal(value.getBytes(StandardCharsets.UTF_8));
        String sealed = VERSION + "."
                + Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP) + "."
                + Base64.encodeToString(encrypted, Base64.NO_WRAP);
        if (!records.edit().putString(record, sealed).commit()) {
            throw new GeneralSecurityException("credential persistence failed");
        }
    }

    private String getRecord(String record) throws GeneralSecurityException {
        String sealed = records.getString(record, null);
        if (sealed == null) return null;
        String[] pieces = sealed.split("\\.", -1);
        if (pieces.length != 3 || !VERSION.equals(pieces[0])) {
            throw new GeneralSecurityException("credential record is invalid");
        }
        byte[] iv;
        byte[] encrypted;
        try {
            iv = Base64.decode(pieces[1], Base64.NO_WRAP);
            encrypted = Base64.decode(pieces[2], Base64.NO_WRAP);
        } catch (IllegalArgumentException exception) {
            throw new GeneralSecurityException("credential encoding is invalid", exception);
        }
        if (iv.length != IV_BYTES || encrypted.length < 16) {
            throw new GeneralSecurityException("credential record length is invalid");
        }
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128, iv));
        cipher.updateAAD(record.getBytes(StandardCharsets.UTF_8));
        return new String(cipher.doFinal(encrypted), StandardCharsets.UTF_8);
    }

    private void deleteRecord(String record) throws GeneralSecurityException {
        if (!records.edit().remove(record).commit()) {
            throw new GeneralSecurityException("credential deletion failed");
        }
    }

    private SecretKey key() throws GeneralSecurityException {
        try {
            KeyStore store = KeyStore.getInstance(KEYSTORE);
            store.load(null);
            KeyStore.Entry existing = store.getEntry(KEY_ALIAS, null);
            if (existing instanceof KeyStore.SecretKeyEntry entry) return entry.getSecretKey();
            KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE);
            generator.init(new KeyGenParameterSpec.Builder(
                    KEY_ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setKeySize(256)
                    .setUnlockedDeviceRequired(false)
                    .build());
            return generator.generateKey();
        } catch (Exception exception) {
            if (exception instanceof GeneralSecurityException security) throw security;
            throw new GeneralSecurityException("credential key is unavailable", exception);
        }
    }
}
