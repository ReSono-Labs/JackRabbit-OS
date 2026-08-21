package com.resonolabs.runtime.host;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

record ManagementHttpRequest(String method, String path, Map<String, String> headers, byte[] body) {
    private static final int MAX_LINE = 4096;
    private static final int MAX_HEADERS = 50;
    private static final int MAX_BODY = 4096;

    static ManagementHttpRequest read(InputStream source) throws IOException {
        BufferedInputStream input = new BufferedInputStream(source);
        String requestLine = readLine(input);
        String[] requestParts = requestLine.split(" ", 3);
        if (requestParts.length != 3 || !requestParts[2].startsWith("HTTP/1.")) {
            throw new IOException("invalid request line");
        }
        String method = requestParts[0];
        if (!method.equals("GET") && !method.equals("POST") && !method.equals("DELETE")) {
            throw new IOException("unsupported method");
        }
        String path = requestParts[1].split("\\?", 2)[0];
        if (!path.startsWith("/") || path.contains("..")) throw new IOException("invalid path");

        Map<String, String> headers = new LinkedHashMap<>();
        for (int count = 0; count < MAX_HEADERS; count++) {
            String line = readLine(input);
            if (line.isEmpty()) break;
            int separator = line.indexOf(':');
            if (separator <= 0) throw new IOException("invalid header");
            headers.put(
                    line.substring(0, separator).trim().toLowerCase(Locale.ROOT),
                    line.substring(separator + 1).trim());
            if (count == MAX_HEADERS - 1) throw new IOException("too many headers");
        }

        int contentLength;
        try {
            contentLength = Integer.parseInt(headers.getOrDefault("content-length", "0"));
        } catch (NumberFormatException exception) {
            throw new IOException("invalid content length");
        }
        if (contentLength < 0 || contentLength > MAX_BODY) throw new IOException("body too large");
        return new ManagementHttpRequest(method, path, Map.copyOf(headers), input.readNBytes(contentLength));
    }

    String header(String name) {
        return headers.get(name.toLowerCase(Locale.ROOT));
    }

    private static String readLine(InputStream input) throws IOException {
        ByteArrayOutputStream line = new ByteArrayOutputStream();
        boolean carriageReturn = false;
        while (line.size() <= MAX_LINE) {
            int value = input.read();
            if (value < 0) throw new IOException("unexpected end of request");
            if (carriageReturn && value == '\n') {
                byte[] bytes = line.toByteArray();
                return new String(bytes, 0, Math.max(0, bytes.length - 1), StandardCharsets.US_ASCII);
            }
            line.write(value);
            carriageReturn = value == '\r';
        }
        throw new IOException("request line too long");
    }
}
