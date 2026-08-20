package com.resonolabs.runtime.host;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;

record ManagementHttpResponse(int status, String contentType, Map<String, String> headers, byte[] body) {
    static ManagementHttpResponse text(int status, String message) {
        return new ManagementHttpResponse(
                status,
                "text/plain; charset=utf-8",
                Map.of(),
                message.getBytes(StandardCharsets.UTF_8));
    }

    static ManagementHttpResponse text(int status, String contentType, String message) {
        return new ManagementHttpResponse(
                status,
                contentType,
                Map.of(),
                message.getBytes(StandardCharsets.UTF_8));
    }

    void write(OutputStream output) throws IOException {
        StringBuilder head = new StringBuilder()
                .append("HTTP/1.1 ").append(status).append(' ').append(reason(status)).append("\r\n")
                .append("Content-Type: ").append(contentType).append("\r\n")
                .append("Content-Length: ").append(body.length).append("\r\n")
                .append("Cache-Control: no-store\r\n")
                .append("X-Content-Type-Options: nosniff\r\n")
                .append("X-Frame-Options: DENY\r\n")
                .append("Referrer-Policy: no-referrer\r\n")
                .append("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'\r\n")
                .append("Connection: close\r\n");
        for (Map.Entry<String, String> header : headers.entrySet()) {
            head.append(header.getKey()).append(": ").append(header.getValue()).append("\r\n");
        }
        head.append("\r\n");
        output.write(head.toString().getBytes(StandardCharsets.US_ASCII));
        output.write(body);
        output.flush();
    }

    private static String reason(int status) {
        return switch (status) {
            case 200 -> "OK";
            case 202 -> "Accepted";
            case 400 -> "Bad Request";
            case 401 -> "Unauthorized";
            case 403 -> "Forbidden";
            case 404 -> "Not Found";
            case 405 -> "Method Not Allowed";
            case 503 -> "Service Unavailable";
            default -> "Response";
        };
    }
}
