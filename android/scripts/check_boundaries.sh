#!/usr/bin/env bash
set -euo pipefail

PRODUCT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCAN_ROOTS=("$PRODUCT_ROOT/app/src/main" "$PRODUCT_ROOT/core" "$PRODUCT_ROOT/feature" "$PRODUCT_ROOT/runtime-host" "$PRODUCT_ROOT/../runtime" "$PRODUCT_ROOT/../web")
PROHIBITED='AndroidEnrollment|EnrollmentCoordinator|ProvisioningHttpClient|PlatformPairingClient|DeviceRuntimeCoordinator|BootstrapConfig|VaultControl|VaultVoice|EdgeSync|voice\.resonolabs\.com|feature:claim|core:edge-sync'
FUTURE_RUNTIME='psycopg|postgres|pgvector|Hermes|A2A|ExternalAI|External AI'

if rg -n "$PROHIBITED" "${SCAN_ROOTS[@]}" "$PRODUCT_ROOT/settings.gradle.kts"; then
    echo "prohibited hosted-platform dependency found" >&2
    exit 1
fi

if rg -ni "$FUTURE_RUNTIME" "$PRODUCT_ROOT/runtime-host/src" "$PRODUCT_ROOT/../runtime/resono_runtime" "$PRODUCT_ROOT/../web/management"; then
    echo "future-slice runtime dependency found" >&2
    exit 1
fi

RUNTIME_MANIFEST="$PRODUCT_ROOT/runtime-host/src/main/AndroidManifest.xml"
if [[ "$(rg -oF 'android:process=":runtime"' "$RUNTIME_MANIFEST" | wc -l)" -ne 1 ]]; then
    echo "runtime manifest must declare exactly one :runtime process" >&2
    exit 1
fi
if ! rg -q 'android:exported="false"' "$RUNTIME_MANIFEST"; then
    echo "runtime service must remain non-exported" >&2
    exit 1
fi
if ! rg -q 'android:foregroundServiceType="specialUse"' "$RUNTIME_MANIFEST" \
        || ! rg -q 'android.permission.FOREGROUND_SERVICE_SPECIAL_USE' "$RUNTIME_MANIFEST"; then
    echo "runtime service must remain an explicit special-use foreground service" >&2
    exit 1
fi

RUNTIME_SERVICE="$PRODUCT_ROOT/runtime-host/src/main/java/com/resonolabs/runtime/host/RuntimeService.java"
if ! rg -q 'startForegroundService' "$RUNTIME_SERVICE" \
        || ! rg -q 'startForeground\(NOTIFICATION_ID' "$RUNTIME_SERVICE" \
        || ! rg -q 'START_STICKY' "$RUNTIME_SERVICE"; then
    echo "runtime service must start and remain foreground/sticky" >&2
    exit 1
fi

NETWORK_POLICY="$PRODUCT_ROOT/app/src/main/res/xml/network_security_config.xml"
if ! rg -q '<base-config cleartextTrafficPermitted="false"' "$NETWORK_POLICY" \
        || ! rg -q '>127\.0\.0\.1</domain>' "$NETWORK_POLICY"; then
    echo "network policy must deny general cleartext and allow only the private loopback boundary" >&2
    exit 1
fi

MANAGEMENT_CLIENT="$PRODUCT_ROOT/runtime-host/src/main/java/com/resonolabs/runtime/host/RuntimeManagementClient.java"
if ! rg -q 'TRANSPORT_WIFI' "$MANAGEMENT_CLIENT" \
        || ! rg -q 'TRANSPORT_ETHERNET' "$MANAGEMENT_CLIENT" \
        || rg -q 'TRANSPORT_CELLULAR' "$MANAGEMENT_CLIENT"; then
    echo "management address discovery must advertise only Wi-Fi or Ethernet" >&2
    exit 1
fi

TLS_IDENTITY="$PRODUCT_ROOT/runtime-host/src/main/java/com/resonolabs/runtime/host/ManagementTlsIdentity.java"
if ! rg -q 'DIGEST_NONE' "$TLS_IDENTITY" \
        || ! rg -q 'DIGEST_SHA384' "$TLS_IDENTITY" \
        || ! rg -q 'DIGEST_SHA512' "$TLS_IDENTITY"; then
    echo "Keystore TLS identity is missing required TLS signature digest modes" >&2
    exit 1
fi
if ! rg -q 'ManagementTlsKeyManager\(KEY_ALIAS' "$TLS_IDENTITY"; then
    echo "management TLS must select its exact Keystore alias" >&2
    exit 1
fi

if rg --files "$PRODUCT_ROOT/runtime-host/src" "$PRODUCT_ROOT/../runtime/resono_runtime" \
        | rg '/(utils?|helpers?|common|managers?)(\.|/)'; then
    echo "catch-all runtime module found" >&2
    exit 1
fi

echo "standalone Android boundaries: OK"
