package com.resonolabs.runtime.host;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

import org.junit.Test;

public final class ManagementHttpRequestTest {
    @Test
    public void deleteRequestReachesManagementProxy() throws Exception {
        ManagementHttpRequest request = read(
                "DELETE /v1/management/creations/weather-app HTTP/1.1\r\n"
                        + "Host: 192.168.1.196:8443\r\n"
                        + "X-CSRF-Token: token\r\n\r\n");

        assertEquals("DELETE", request.method());
        assertEquals("/v1/management/creations/weather-app", request.path());
    }

    @Test
    public void unsupportedMutationMethodRemainsRejected() {
        assertThrows(IOException.class, () -> read(
                "PATCH /v1/management/creations/weather-app HTTP/1.1\r\n"
                        + "Host: 192.168.1.196:8443\r\n\r\n"));
    }

    private static ManagementHttpRequest read(String request) throws IOException {
        return ManagementHttpRequest.read(new ByteArrayInputStream(
                request.getBytes(StandardCharsets.US_ASCII)));
    }
}
