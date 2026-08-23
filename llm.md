# JackRabbit Coding Context for LLMs

## Purpose

This document gives a coding assistant the minimum complete context needed to work safely and effectively on JackRabbit.

JackRabbit is a standalone, Voice-first software platform for the Rabbit R1. The Android application replaces the normal HOME experience, hosts an embedded Python runtime, provides native OpenAI Realtime Voice over WebRTC, displays Cards, and serves a same-LAN management website from the device.

The project is source-available for noncommercial use under the license in `LICENSE`.

## Product composition

The complete application has three required source areas:

```text
android/   Native Rabbit R1 application, UI, hardware integration, WebRTC, and APK packaging
runtime/   Embedded Python runtime, agents, tools, domains, storage, extensions, and APIs
web/       Management website embedded into and served by the APK
```

These are not separate products. The Android build packages all three into one APK.

The physical product also uses Android logical partition images:

```text
system.img       Contains the JackRabbit APK and retained system applications
vendor.img       Contains retained R1 hardware integration and the first-boot lock-screen overlay
product.img      Retained product configuration
system_ext.img   Retained Android system extensions
boot/vbmeta      Retained boot and verified-boot inputs
```

Normal application changes affect the APK and therefore only require rebuilding `system.img`. Do not rebuild unchanged logical images merely to create a new release set.

## Architecture

```text
Rabbit R1 hardware and retained Cipher device services
                         |
                 JackRabbit Android HOME
              +----------+-----------+
              |          |           |
          Native UI   WebRTC Voice   Device controls
              |
        Embedded Python runtime
     +--------+----------+----------------+
     |        |          |                |
Agents SDK   MCP     Domain services   HTTPS management
                     Mail/Calendar/
                     Tasks/Memory
```

### Android ownership

- `android/app/` composes the installable HOME application.
- `android/core/` contains small reusable device/design/input/power contracts.
- `android/feature/` owns individual native product features.
- `android/runtime-host/` embeds Python, bridges Android-owned credentials, and serves runtime/management traffic.
- `android/system/motor-service/` contains the retained motor integration package.

Keep feature ownership explicit. Do not create catch-all `utils`, `helpers`, `common`, or general manager modules.

### Runtime ownership

- `runtime/resono_runtime/application.py` is the composition root.
- `providers/` owns OpenAI Platform and ChatGPT/Codex access.
- `agents/` owns shared Agents SDK execution infrastructure.
- `background_agent/` owns delegated goal execution.
- `realtime/` owns Voice modes and session behavior.
- `tools/` owns the canonical tool catalog and built-in tool packages.
- `mcp/` owns MCP connections, lifecycle, discovery, and tool adaptation.
- `domains/` owns canonical Mail, Calendar, and Tasks behavior and data.
- `skills/`, `plugins/`, and `creations/` own their separate extension lifecycles.
- `storage/` owns SQLite migrations and repositories.
- `api/` owns narrow HTTP transports over implemented runtime behavior.

### Management website ownership

- `web/management/` contains the same-LAN management interface.
- The site configures the device. It is not a desktop replacement for R1 features.
- Mail content and Calendar content are not displayed in management.
- Management assets are embedded into the APK during the Android build.

## Important product rules

### OpenAI access is global and mutually exclusive

The user selects one active OpenAI access method for the whole platform:

- OpenAI Platform API key; or
- ChatGPT/Codex device OAuth.

Every agent and OpenAI-backed service follows the active access path through the canonical provider resolver.

Rules:

- Platform cannot be activated while OAuth is connected.
- The user must disconnect OAuth before activating Platform access.
- Completing OAuth makes subscription access active.
- If a Platform key remains stored, disconnecting OAuth may return the platform to that available connection.
- Never create separate credential-selection logic inside an agent, tool, memory component, or search component.
- OAuth token storage, refresh, streaming behavior, and Android Keystore ownership must remain centralized.

The management OAuth flow must retain the `authSessionId` returned by the start endpoint, send it with every poll request, and recognize `status: "completed"` or `runtime.connected` as completion.

### Agent execution

- Use the OpenAI Agents SDK for applicable text/background agents.
- Do not introduce a parallel custom agent loop.
- Voice uses native WebRTC for live audio. Do not route high-rate audio through Python or MCP.
- Tools enter one canonical Tool Catalog.
- Agent audience routing determines whether a tool is supplied to Voice, Background Agent, or both.
- System-only agents do not receive user Skills or Plugins.
- Background Agent runs own isolated event loops, clients, MCP sessions, execution contexts, and temporary workspaces.
- Do not share an async HTTP client or event loop across isolated Background Agent runs.

### Data and tools

- Domains own canonical user data.
- Plugins, Skills, Creations, Cards, connectors, and tools do not own canonical domain data.
- Mail exposes no delete, trash, expunge, or purge tool.
- Mail send requires an exact single-use confirmation bound to the draft and approval utterance.
- Calendar provider capabilities determine whether create, update, or delete is allowed.
- Tasks are simple text tasks with completion state and no dates or reminders.

### Extensions

- Skills use the Agent Skills `SKILL.md` format.
- Plugins use the Agent Plugins `plugin.json` format and may include Skills and MCP definitions.
- MCP remains the standard model-facing tool boundary.
- Creations are separately bounded static Card packages.
- Imports require preflight, explicit replacement warning, enable/disable, deletion, quarantine, and recovery behavior.
- Do not invent a proprietary replacement for an applicable industry standard.

## Development requirements

Reference toolchain:

- Linux
- JDK 17
- Android SDK API 36
- Android Build Tools 36.0.0
- Android platform tools (`adb` and `fastboot`)
- Gradle 9.5 or the project-compatible Gradle environment
- Python environment support through `uv` for host runtime tests

Create `android/local.properties` with the local Android SDK path. Never commit this file.

The reference workstation has used these temporary tool paths:

```text
/tmp/r1-jdk17
/tmp/gradle-9.5.0
/tmp/r1-android-sdk/platform-tools/adb
/tmp/r1-android-sdk/platform-tools/fastboot
```

These paths are examples, not repository requirements. Use equivalent local paths when necessary.

## Build the APK

From the repository root:

```bash
./android/scripts/build_debug.sh
```

A successful authoritative build ends with:

```text
BUILD SUCCESSFUL
standalone Android boundaries: OK
embedded runtime package: OK
```

The APK is written to:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

If Gradle fails to initialize `libnative-platform.so`, initialize the pinned Gradle/JDK combination and rerun the project build:

```bash
JAVA_HOME=/tmp/r1-jdk17 \
PATH=/tmp/r1-jdk17/bin:/tmp/r1-android-sdk/platform-tools:$PATH \
/tmp/gradle-9.5.0/bin/gradle --no-daemon --version

./android/scripts/build_debug.sh
```

Do not delete Gradle caches blindly and do not replace the verified toolchain while diagnosing an unrelated application failure.

## Runtime test environment

The repository may not contain a root `.venv`. Use an isolated `uv` environment for focused Python tests:

```bash
PYTHONPATH=runtime uv run \
  --with pydantic==2.12.2 \
  --with openai-agents==0.18.3 \
  --with PyYAML \
  --with jsonschema \
  --with pytest \
  -- python -m pytest -q <focused-test-files>
```

Some route tests also require `httpx`.

Check management JavaScript syntax with:

```bash
node --check web/management/app.js
```

Run focused tests for the changed responsibility. Do not treat a passing unrelated suite as evidence for the affected behavior.

## Versioning

The canonical application version is stored in:

```text
android/app-version.properties
```

Rules:

- Increment `VERSION_CODE` for every new installable APK.
- Keep the current product identity in `VERSION_NAME` unless the owner changes it.
- Current release family: `Carrot1`.
- Debug builds append `-debug` automatically.
- Never overwrite the only accepted rollback artifact with a new build.

## ADB connection and deployment

### Discover the active ADB server first

Do not begin by killing ADB. Multiple local ADB servers may exist, and restarting a working server can temporarily remove the R1 transport.

Query the normal server:

```bash
adb devices -l
```

If this workstation uses explicit servers, query known ports individually:

```bash
ADB_SERVER_SOCKET=tcp:127.0.0.1:5037 adb devices -l
ADB_SERVER_SOCKET=tcp:127.0.0.1:5038 adb devices -l
ADB_SERVER_SOCKET=tcp:127.0.0.1:5039 adb devices -l
ADB_SERVER_SOCKET=tcp:127.0.0.1:50399 adb devices -l
```

Use the server that actually lists the Rabbit R1. Do not guess a port after finding a working transport.

If the device is physically connected but absent, poll the same server briefly before restarting it:

```bash
for attempt in 1 2 3 4 5; do
  adb devices -l
  sleep 2
done
```

Only restart ADB when no server sees the device. After an ADB server restart, the R1 may need to be physically unplugged and reconnected before discovery works again.

### Install the APK

```bash
adb install -r -d android/app/build/outputs/apk/debug/app-debug.apk
```

Start JackRabbit HOME:

```bash
adb shell am start -n \
  com.resonolabs.voice.engineering/com.resonolabs.voice.MainActivity
```

Verify the installed version:

```bash
adb shell dumpsys package com.resonolabs.voice.engineering \
  | rg 'versionCode|versionName'
```

Verify the process:

```bash
adb shell pidof com.resonolabs.voice.engineering
```

The historical package `com.resonolabs.r1` is obsolete. Do not use it.

## Runtime and management verification

Expected listeners:

```text
127.0.0.1:8765   Embedded runtime
*:8443           Same-LAN HTTPS management
```

Check on the device:

```bash
adb shell 'ss -ltn | grep -E ":(8765|8443)"'
```

For host verification, forward management HTTPS:

```bash
adb forward tcp:18443 tcp:8443
curl -k -I https://127.0.0.1:18443/
```

The management root should return HTTP 200. Management APIs remain protected by the pairing session, origin checks, and CSRF token.

The browser may cache embedded JavaScript across APK upgrades. Refresh an already-open management page after deployment before diagnosing a supposedly unchanged UI bug.

## Common failures and proven causes

### Management says runtime unavailable after a clean image flash

Database migrations must run before code that inserts the Background Agent `RULES.md` workspace record. Constructor-time database writes can fail on clean userdata because the required tables do not exist yet.

### OAuth code is accepted but management never updates

Confirm that the browser:

1. Stores `authSessionId` returned by `/subscription/start`.
2. Sends that ID to every `/subscription/poll` request.
3. Recognizes the completion response shape.
4. Reloads subscription and provider status after completion.

Do not rewrite token storage or refresh logic until this browser-to-runtime polling contract is verified.

### Background Agent reports `Event loop is closed`

Each run must own and close its own event loop, OpenAI client, HTTP client, MCP session, execution context, and temporary workspace. Do not reuse a process-global async client across per-run loops.

### Subscription Responses returns `stream must be set to true`

ChatGPT/Codex subscription execution requires the subscription-compatible streamed Agents SDK path. Platform execution and subscription execution use the same agent contract but different provider transport requirements.

### Model rejects `reasoning.effort`

Reasoning settings must match the model selected for the active global access path. Do not attach reasoning parameters to a non-reasoning model. Platform should prefer `gpt-5.6-sol` when the provider reports it and no valid saved selection exists.

### Background web search times out or returns a connection error

MCP Streamable HTTP has separate connection and client-session timeouts. Propagate the remaining run window to both. Do not rely on a short default client-session timeout for a real search request.

### Build cannot find Java through `apksigner`

Set `JAVA_HOME` to JDK 17 and prepend `$JAVA_HOME/bin` to `PATH` before invoking Android build tools.

### ADB suddenly shows no device

Check every already-running ADB server before restarting anything. If a restart is unavoidable, physically reconnect the R1 afterward.

## Installer image updates

Generated APKs and logical images are not stored in Git history.

For a normal APK/runtime/web correction:

1. Build and physically test the APK.
2. Increment the application version.
3. Rebuild only `system.img` from the verified base.
4. Byte-compare the APK extracted from the new image with the tested APK.
5. Run read-only `e2fsck` against the resulting image.
6. Publish the image hash and manifest to the installer developer.

The local system-only builder is:

```text
image/scripts/build_installer_system_update.sh
```

The image workspace is intentionally local and excluded from the public Git repository. Do not commit `.img`, `.apk`, `.zip`, `.bin`, signing keys, or device credentials.

## Repository hygiene

The public repository intentionally tracks only:

```text
android/
runtime/
web/
images/
README.md
BUILDING.md
USER-GUIDE.md
LICENSE
llm.md
.gitignore
```

Internal planning, tests, installer work in progress, architecture graph output, device logs, donor repositories, downloaded firmware, accepted binary evidence, and generated images remain local until deliberately prepared for publication.

Never modify a donor repository. Copy approved donor behavior into this repository only after recording provenance and retained/omitted behavior in the project's local engineering records.

## Safe coding workflow

1. Identify the single owner of the behavior being changed.
2. Read the relevant source and public contract before editing.
3. Preserve accepted behavior outside the requested scope.
4. Make the smallest modular correction.
5. Run focused validation for the affected responsibility.
6. Build the authoritative APK when an installable change is requested.
7. Increment the version before deployment.
8. Discover the active ADB transport without restarting it unnecessarily.
9. Deploy and verify runtime, management, and the affected real behavior.
10. Commit source and public documentation, never generated device images or secrets.

Do not add mock interfaces, fake data, disconnected controls, placeholder endpoints, or simulated product states. A visible feature must be wired to its real implementation.
