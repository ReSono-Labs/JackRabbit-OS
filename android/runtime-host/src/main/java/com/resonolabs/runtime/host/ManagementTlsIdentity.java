package com.resonolabs.runtime.host;

import static java.nio.charset.StandardCharsets.UTF_8;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.LinkAddress;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;

import java.math.BigInteger;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.util.Base64;
import java.util.Calendar;

import javax.net.ssl.KeyManager;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLServerSocket;
import javax.security.auth.x500.X500Principal;

final class ManagementTlsIdentity {
    private static final String ANDROID_KEY_STORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "resono.management.tls.v2";
    private static final String CERTIFICATE_BEGIN = "-----BEGIN CERTIFICATE-----";
    private static final String CERTIFICATE_END = "-----END CERTIFICATE-----";
    private static final String DEFAULT_HOSTNAME = "ReSono R1";

    private final Context context;

    ManagementTlsIdentity(Context context) {
        this.context = context.getApplicationContext();
    }

    SSLServerSocket openServerSocket(int port) throws Exception {
        KeyStore store = KeyStore.getInstance(ANDROID_KEY_STORE);
        store.load(null);
        String certificateHost = preferredCertificateHost();
        ensureIdentityMatchesHost(store, certificateHost);

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

    String exportedCertificatePem() {
        try {
            KeyStore store = KeyStore.getInstance(ANDROID_KEY_STORE);
            store.load(null);
            Certificate[] chain = store.getCertificateChain(KEY_ALIAS);
            if (chain == null || chain.length == 0) {
                return "";
            }
            StringBuilder output = new StringBuilder();
            for (Certificate item : chain) {
                if (!(item instanceof X509Certificate certificate)) {
                    continue;
                }
                String encoded = Base64.getMimeEncoder(64, "\n".getBytes(UTF_8))
                        .encodeToString(certificate.getEncoded());
                output.append(CERTIFICATE_BEGIN).append('\n')
                        .append(encoded)
                        .append('\n')
                        .append(CERTIFICATE_END)
                        .append('\n');
            }
            return output.toString();
        } catch (Exception error) {
            return "";
        }
    }

    private String preferredCertificateHost() {
        ConnectivityManager connectivity = context.getSystemService(ConnectivityManager.class);
        if (connectivity == null) {
            return DEFAULT_HOSTNAME;
        }
        Network network = connectivity.getActiveNetwork();
        NetworkCapabilities capabilities = network == null
                ? null
                : connectivity.getNetworkCapabilities(network);
        boolean localNetwork = capabilities != null
                && (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
                || capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET));
        if (!localNetwork) {
            return DEFAULT_HOSTNAME;
        }
        LinkProperties links = network == null ? null : connectivity.getLinkProperties(network);
        if (links == null) {
            return DEFAULT_HOSTNAME;
        }
        InetAddress fallback = null;
        for (LinkAddress link : links.getLinkAddresses()) {
            InetAddress address = link.getAddress();
            if (address.isLoopbackAddress() || address.isLinkLocalAddress()) {
                continue;
            }
            if (address instanceof Inet4Address) {
                return address.getHostAddress();
            }
            fallback = address;
        }
        return fallback == null ? DEFAULT_HOSTNAME : fallback.getHostAddress();
    }

    private void ensureIdentityMatchesHost(KeyStore store, String expectedHost) throws Exception {
        boolean shouldCreate = true;
        if (store.containsAlias(KEY_ALIAS)) {
            Certificate[] storedChain = store.getCertificateChain(KEY_ALIAS);
            if (storedChain != null && storedChain.length > 0 && storedChain[0] instanceof X509Certificate current) {
                String commonName = certificateCommonName(current);
                if (expectedHost.equals(commonName)) {
                    shouldCreate = false;
                }
            }
        }
        if (!shouldCreate) {
            return;
        }
        if (store.containsAlias(KEY_ALIAS)) {
            store.deleteEntry(KEY_ALIAS);
        }
        createIdentity(expectedHost);
    }

    private String certificateCommonName(X509Certificate certificate) {
        String subject = certificate.getSubjectX500Principal().getName();
        for (String token : subject.split(",")) {
            String segment = token.trim();
            if (segment.startsWith("CN=")) {
                return segment.substring(3);
            }
        }
        return "";
    }

    private void createIdentity(String certificateHost) throws Exception {
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
                .setCertificateSubject(new X500Principal("CN=" + certificateHost))
                .setCertificateSerialNumber(BigInteger.ONE)
                .setCertificateNotBefore(start.getTime())
                .setCertificateNotAfter(end.getTime())
                .setUserAuthenticationRequired(false)
                .build());
        generator.generateKeyPair();
    }
}
