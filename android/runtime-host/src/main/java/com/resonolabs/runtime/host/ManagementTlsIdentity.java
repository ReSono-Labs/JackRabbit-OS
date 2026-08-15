package com.resonolabs.runtime.host;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;

import java.math.BigInteger;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.util.Calendar;

import javax.net.ssl.KeyManager;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLServerSocket;
import javax.security.auth.x500.X500Principal;

final class ManagementTlsIdentity {
    private static final String ANDROID_KEY_STORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "resono.management.tls.v2";

    SSLServerSocket openServerSocket(int port) throws Exception {
        KeyStore store = KeyStore.getInstance(ANDROID_KEY_STORE);
        store.load(null);
        if (!store.containsAlias(KEY_ALIAS)) createIdentity();

        PrivateKey privateKey = (PrivateKey) store.getKey(KEY_ALIAS, null);
        Certificate[] storedChain = store.getCertificateChain(KEY_ALIAS);
        if (privateKey == null || storedChain == null || storedChain.length == 0) {
            throw new IllegalStateException("management TLS identity unavailable");
        }
        X509Certificate[] chain = new X509Certificate[storedChain.length];
        for (int index = 0; index < storedChain.length; index++) {
            chain[index] = (X509Certificate) storedChain[index];
        }
        SSLContext context = SSLContext.getInstance("TLS");
        context.init(
                new KeyManager[]{new ManagementTlsKeyManager(KEY_ALIAS, privateKey, chain)},
                null,
                null);
        SSLServerSocket socket = (SSLServerSocket) context.getServerSocketFactory()
                .createServerSocket(port);
        socket.setReuseAddress(true);
        socket.setNeedClientAuth(false);
        return socket;
    }

    private void createIdentity() throws Exception {
        Calendar start = Calendar.getInstance();
        start.add(Calendar.DAY_OF_YEAR, -1);
        Calendar end = Calendar.getInstance();
        end.add(Calendar.YEAR, 10);
        KeyPairGenerator generator = KeyPairGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_EC,
                ANDROID_KEY_STORE);
        generator.initialize(new KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
                .setDigests(
                        KeyProperties.DIGEST_NONE,
                        KeyProperties.DIGEST_SHA256,
                        KeyProperties.DIGEST_SHA384,
                        KeyProperties.DIGEST_SHA512)
                .setCertificateSubject(new X500Principal("CN=ReSono R1"))
                .setCertificateSerialNumber(BigInteger.ONE)
                .setCertificateNotBefore(start.getTime())
                .setCertificateNotAfter(end.getTime())
                .setUserAuthenticationRequired(false)
                .build());
        generator.generateKeyPair();
    }
}
