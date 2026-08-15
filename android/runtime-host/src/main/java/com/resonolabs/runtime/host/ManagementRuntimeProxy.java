package com.resonolabs.runtime.host;

import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

final class ManagementRuntimeProxy {
    private static final Set<String> ROUTES = Set.of(
            "/v1/management/pair",
            "/v1/management/status",
            "/v1/management/profile",
            "/v1/management/restart",
            "/v1/management/openai",
            "/v1/management/openai/connect",
            "/v1/management/openai/disconnect",
            "/v1/management/openai/models",
            "/v1/management/openai/refresh",
            "/v1/management/openai/access",
            "/v1/management/openai/subscription",
            "/v1/management/openai/subscription/start",
            "/v1/management/openai/subscription/poll",
            "/v1/management/openai/subscription/disconnect",
            "/v1/management/text/turns");
    private final String localApiToken;

    ManagementRuntimeProxy(String localApiToken) {
        this.localApiToken = localApiToken;
    }

    ManagementHttpResponse forward(ManagementHttpRequest request) {
        if (!ROUTES.contains(request.path())) return ManagementHttpResponse.text(404, "Not found.");
        String host = request.header("host");
        if (host == null || host.length() > 255 || !host.matches("[A-Za-z0-9.\\-\\[\\]:]+")) {
            return ManagementHttpResponse.text(400, "Invalid host.");
        }
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(
                    "http://127.0.0.1:8765" + request.path()).openConnection();
            connection.setRequestMethod(request.method());
            connection.setConnectTimeout(1000);
            connection.setReadTimeout(readTimeoutMillis(request.path()));
            connection.setInstanceFollowRedirects(false);
            connection.setRequestProperty("Authorization", "Bearer " + localApiToken);
            connection.setRequestProperty("X-ReSono-Forwarded-Origin", "https://" + host);
            copyRequestHeader(request, connection, "Origin");
            copyRequestHeader(request, connection, "Cookie");
            copyRequestHeader(request, connection, "Content-Type");
            copyRequestHeader(request, connection, "X-CSRF-Token");
            if (request.body().length > 0) {
                connection.setDoOutput(true);
                connection.getOutputStream().write(request.body());
            }
            int status = connection.getResponseCode();
            InputStream source = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
            byte[] body = source == null ? new byte[0] : source.readNBytes(65536);
            Map<String, String> headers = new LinkedHashMap<>();
            String cookie = connection.getHeaderField("Set-Cookie");
            if (cookie != null) headers.put("Set-Cookie", cookie);
            return new ManagementHttpResponse(
                    status,
                    connection.getContentType() == null
                            ? "application/json; charset=utf-8"
                            : connection.getContentType(),
                    Map.copyOf(headers),
                    body);
        } catch (Exception ignored) {
            return ManagementHttpResponse.text(503, "Runtime unavailable.");
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static int readTimeoutMillis(String path) {
        if (path.equals("/v1/management/text/turns")) return 65_000;
        if (path.equals("/v1/management/openai/subscription/start")
                || path.equals("/v1/management/openai/subscription/poll")) return 35_000;
        if (path.equals("/v1/management/openai")
                || path.equals("/v1/management/openai/connect")
                || path.equals("/v1/management/openai/models")
                || path.equals("/v1/management/openai/refresh")
                || path.equals("/v1/management/openai/access")) return 30_000;
        return 3_000;
    }

    private static void copyRequestHeader(
            ManagementHttpRequest request,
            HttpURLConnection connection,
            String name) {
        String value = request.header(name);
        if (value != null) connection.setRequestProperty(name, value);
    }
}
