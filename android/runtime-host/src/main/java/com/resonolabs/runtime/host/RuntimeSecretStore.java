package com.resonolabs.runtime.host;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.AtomicFile;
import android.util.Base64;

import java.io.File;
import java.io.FileOutputStream;
import java.security.KeyStore;
import java.security.SecureRandom;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

final class RuntimeSecretStore {
    private static final String ANDROID_KEY_STORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "resono.runtime.local-api.v1";
    private static final int IV_BYTES = 12;
    private final Context deviceContext;

    RuntimeSecretStore(Context context) {
        deviceContext = context.createDeviceProtectedStorageContext();
    }

    String loadOrCreateLocalApiToken() throws Exception {
        File directory = new File(deviceContext.getNoBackupFilesDir(), "runtime-secrets");
        if (!directory.isDirectory() && !directory.mkdirs()) {
            throw new IllegalStateException("runtime secret directory unavailable");
        }
        AtomicFile tokenFile = new AtomicFile(new File(directory, "local-api-token.bin"));
        SecretKey key = loadOrCreateKey();
        if (tokenFile.getBaseFile().isFile()) {
            return decrypt(tokenFile, key);
        }

        byte[] random = new byte[32];
        new SecureRandom().nextBytes(random);
        String token = Base64.encodeToString(random, Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        byte[] ciphertext = cipher.doFinal(token.getBytes(java.nio.charset.StandardCharsets.UTF_8));
        byte[] sealed = new byte[cipher.getIV().length + ciphertext.length];
        System.arraycopy(cipher.getIV(), 0, sealed, 0, cipher.getIV().length);
        System.arraycopy(ciphertext, 0, sealed, cipher.getIV().length, ciphertext.length);
        FileOutputStream output = tokenFile.startWrite();
        try {
            output.write(sealed);
            tokenFile.finishWrite(output);
        } catch (Exception exception) {
            tokenFile.failWrite(output);
            throw exception;
        }
        return token;
    }

    String loadLocalApiToken() throws Exception {
        File file = new File(
                new File(deviceContext.getNoBackupFilesDir(), "runtime-secrets"),
                "local-api-token.bin");
        if (!file.isFile()) throw new java.io.FileNotFoundException("runtime token unavailable");
        return decrypt(new AtomicFile(file), loadOrCreateKey());
    }

    private String decrypt(AtomicFile tokenFile, SecretKey key) throws Exception {
        byte[] sealed = tokenFile.readFully();
        if (sealed.length <= IV_BYTES) throw new IllegalStateException("runtime token is invalid");
        byte[] iv = new byte[IV_BYTES];
        byte[] ciphertext = new byte[sealed.length - IV_BYTES];
        System.arraycopy(sealed, 0, iv, 0, iv.length);
        System.arraycopy(sealed, iv.length, ciphertext, 0, ciphertext.length);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, iv));
        return new String(cipher.doFinal(ciphertext), java.nio.charset.StandardCharsets.UTF_8);
    }

    private SecretKey loadOrCreateKey() throws Exception {
        KeyStore store = KeyStore.getInstance(ANDROID_KEY_STORE);
        store.load(null);
        KeyStore.Entry existing = store.getEntry(KEY_ALIAS, null);
        if (existing instanceof KeyStore.SecretKeyEntry secretKeyEntry) {
            return secretKeyEntry.getSecretKey();
        }
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEY_STORE);
        generator.init(new KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setUnlockedDeviceRequired(false)
                .build());
        return generator.generateKey();
    }
}
