package com.resonolabs.runtime.host;

import android.content.res.AssetManager;

import java.io.IOException;
import java.util.Map;

final class ManagementAssetStore {
    private static final Map<String, String> PATHS = Map.of(
            "/", "management/index.html",
            "/design/tokens.css", "design/tokens.css",
            "/design/base.css", "design/base.css",
            "/management/management.css", "management/management.css",
            "/management/app.js", "management/app.js",
            "/management/build07.js", "management/build07.js",
            "/management/background-agent.js", "management/background-agent.js");
    private final AssetManager assets;

    ManagementAssetStore(AssetManager assets) {
        this.assets = assets;
    }

    ManagementHttpResponse get(String path) throws IOException {
        String asset = PATHS.get(path);
        if (asset == null) return ManagementHttpResponse.text(404, "Not found.");
        String contentType = asset.endsWith(".css")
                ? "text/css; charset=utf-8"
                : asset.endsWith(".js")
                ? "text/javascript; charset=utf-8"
                : "text/html; charset=utf-8";
        try (var input = assets.open(asset)) {
            return new ManagementHttpResponse(200, contentType, Map.of(), input.readAllBytes());
        }
    }
}
