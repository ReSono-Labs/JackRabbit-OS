package com.resonolabs.runtime.host;

import android.content.Context;

import java.io.IOException;
import java.net.Socket;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

import javax.net.ssl.SSLServerSocket;

final class ManagementHttpsServer implements AutoCloseable {
    static final int PORT = 8443;
    private final ManagementAssetStore assets;
    private final ManagementRuntimeProxy runtime;
    private final ExecutorService acceptor = Executors.newSingleThreadExecutor();
    private final ExecutorService clients = Executors.newFixedThreadPool(4);
    private final AtomicBoolean closed = new AtomicBoolean();
    private SSLServerSocket server;

    ManagementHttpsServer(Context context, String localApiToken) {
        assets = new ManagementAssetStore(context.getAssets());
        runtime = new ManagementRuntimeProxy(localApiToken);
    }

    void start() throws Exception {
        server = new ManagementTlsIdentity().openServerSocket(PORT);
        acceptor.execute(this::accept);
    }

    private void accept() {
        while (!closed.get()) {
            try {
                Socket client = server.accept();
                client.setSoTimeout(5000);
                clients.execute(() -> handle(client));
            } catch (IOException exception) {
                if (!closed.get()) close();
            }
        }
    }

    private void handle(Socket client) {
        try (client) {
            ManagementHttpRequest request = ManagementHttpRequest.read(client.getInputStream());
            ManagementHttpResponse response;
            if (request.path().startsWith("/v1/")) {
                response = runtime.forward(request);
            } else if (!request.method().equals("GET")) {
                response = ManagementHttpResponse.text(405, "Method not allowed.");
            } else {
                response = assets.get(request.path());
            }
            response.write(client.getOutputStream());
        } catch (IOException ignored) {
            // Invalid or disconnected clients receive no diagnostic detail.
        }
    }

    @Override public void close() {
        if (!closed.compareAndSet(false, true)) return;
        try {
            if (server != null) server.close();
        } catch (IOException ignored) {
        }
        acceptor.shutdownNow();
        clients.shutdownNow();
    }
}
