package com.resonolabs.runtime.host;

import java.net.Socket;
import java.security.Principal;
import java.security.PrivateKey;
import java.security.cert.X509Certificate;

import javax.net.ssl.SSLEngine;
import javax.net.ssl.X509ExtendedKeyManager;

final class ManagementTlsKeyManager extends X509ExtendedKeyManager {
    private final String alias;
    private final PrivateKey privateKey;
    private final X509Certificate[] certificateChain;

    ManagementTlsKeyManager(
            String alias,
            PrivateKey privateKey,
            X509Certificate[] certificateChain) {
        this.alias = alias;
        this.privateKey = privateKey;
        this.certificateChain = certificateChain.clone();
    }

    @Override public String[] getClientAliases(String keyType, Principal[] issuers) {
        return null;
    }

    @Override public String chooseClientAlias(
            String[] keyTypes,
            Principal[] issuers,
            Socket socket) {
        return null;
    }

    @Override public String[] getServerAliases(String keyType, Principal[] issuers) {
        return supports(keyType) ? new String[]{alias} : null;
    }

    @Override public String chooseServerAlias(
            String keyType,
            Principal[] issuers,
            Socket socket) {
        return supports(keyType) ? alias : null;
    }

    @Override public String chooseEngineServerAlias(
            String keyType,
            Principal[] issuers,
            SSLEngine engine) {
        return supports(keyType) ? alias : null;
    }

    @Override public X509Certificate[] getCertificateChain(String requestedAlias) {
        return alias.equals(requestedAlias) ? certificateChain.clone() : null;
    }

    @Override public PrivateKey getPrivateKey(String requestedAlias) {
        return alias.equals(requestedAlias) ? privateKey : null;
    }

    private static boolean supports(String keyType) {
        return keyType != null && keyType.toUpperCase(java.util.Locale.ROOT).contains("EC");
    }
}
