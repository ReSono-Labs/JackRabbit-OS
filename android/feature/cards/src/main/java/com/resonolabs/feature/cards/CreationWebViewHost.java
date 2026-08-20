package com.resonolabs.feature.cards;

import android.app.Activity;
import android.net.Uri;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import org.json.JSONObject;

import com.resonolabs.runtime.host.CreationCatalogClient;
import com.resonolabs.ui.input.UiInputIntent;

import java.io.ByteArrayInputStream;

final class CreationWebViewHost extends WebView {
    private final CreationCatalogClient client;
    private final Runnable close;

    CreationWebViewHost(Activity activity, CreationCatalogClient client, JSONObject item, Runnable close) {
        super(activity);
        this.client = client;
        this.close = close;
        WebSettings settings = getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        String sourceType = item.optString("sourceType", "local_archive");
        boolean linked = "rabbit_qr_link".equals(sourceType);
        String entry = linked ? item.optString("entryUrl", "") : item.optString("entryAsset", "");
        Uri linkedOrigin = linked ? Uri.parse(entry) : null;
        setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (linked) return safeLinked(uri) ? null : denied();
                if (!"https".equals(uri.getScheme()) || !"resono.local".equals(uri.getHost())) return denied();
                try {
                    CreationCatalogClient.Asset asset = client.asset(activity, uri.getEncodedPath());
                    return new WebResourceResponse(asset.contentType(), null, new ByteArrayInputStream(asset.body()));
                } catch (Exception ignored) {
                    return denied();
                }
            }

            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (linked) return !safeLinked(uri) || linkedOrigin == null || !linkedOrigin.getHost().equalsIgnoreCase(uri.getHost());
                return !"https".equals(uri.getScheme()) || !"resono.local".equals(uri.getHost());
            }
        });
        loadUrl(linked ? entry : "https://resono.local" + entry);
    }

    boolean onInput(UiInputIntent input) {
        if (input == UiInputIntent.BACK) {
            close.run();
            return true;
        }
        String event = switch (input) {
            case PREVIOUS -> "scrollUp";
            case NEXT -> "scrollDown";
            case ACTIVATE -> "sideClick";
            case BACK -> "";
        };
        evaluateJavascript("window.dispatchEvent(new Event('" + event + "'))", null);
        return true;
    }

    private static WebResourceResponse denied() {
        return new WebResourceResponse("text/plain", "UTF-8", 403, "Blocked", java.util.Map.of(), new ByteArrayInputStream(new byte[0]));
    }

    private static boolean safeLinked(Uri uri) {
        if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null) return false;
        String host = uri.getHost().toLowerCase(java.util.Locale.ROOT);
        if (host.equals("localhost") || host.endsWith(".localhost") || host.endsWith(".local")) return false;
        try {
            java.net.InetAddress address = java.net.InetAddress.getByName(host);
            return !address.isAnyLocalAddress() && !address.isLoopbackAddress()
                    && !address.isLinkLocalAddress() && !address.isSiteLocalAddress()
                    && !address.isMulticastAddress();
        } catch (Exception ignored) {
            return false;
        }
    }
}
