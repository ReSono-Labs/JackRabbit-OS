# Project Skills / Deployment Notes (JackRabbit)

This file captures the exact local environment pathing and commands used to connect to
the Rabbit R1 and deploy the current project APK. It is intentionally practical so the
next person can resume quickly.

## Scope and directories used

- Working repo root: `/home/christian/Documents/Projects/ReSono-Labs-R1-Voice`
- Android source/build module: `android/`
- On-device runtime/service: `runtime/`
- Management web (served from APK assets): `web/`
- Test suite: `tests/`
- Build artifacts: `artifacts/`
  - `artifacts/local-builds/` (local debug candidates)
  - `artifacts/android-candidates/` (named milestone candidates)
  - `artifacts/accepted-bases/` (accepted rollback/base artifacts)
- External host tools used in this session (outside repo):
  - `/tmp/r1-android-sdk/platform-tools/adb`
  - `/tmp/r1-android-sdk/platform-tools/fastboot`

## Global capability-package structure

Every cohesive capability added from Build Contract 07 onward must have one
explicit, versioned package boundary. Do not register a domain's tools,
schemas, permissions, or UI projections piecemeal from application composition.

Required ownership:

```text
domain/                 canonical data, policy, and use cases
connectors/<domain>/    provider transport and provider capability discovery
tools/<domain>/         one versioned agent-tool package
api/<domain>_routes.py  narrow transport DTOs only
feature/<domain>/       native presentation only, when applicable
```

For every built-in domain tool package:

- Provide one public package object and one `register(ToolCatalog)` entry point.
- Keep the complete public tool names, descriptions, JSON Schemas, effect
  classes, and package version in one contract module.
- Register the complete definition tuple together. The application must not
  select or register individual tools from the package.
- Use one stable `DOMAIN_TOOL_SET` audience resource for Voice/Text/Both
  selection. Do not create separate Voice and Text implementations.
- Keep provider permissions and record editability in domain/service handlers.
  Stable tool vocabulary remains exposed after normal audience filtering; a
  read-only provider returns a precise capability denial for a mutation.
- Require explicit user confirmation for external writes even when the provider
  permits them.
- Do not expose the package in the live Tool Catalog until every advertised
  handler has real implemented behavior. Placeholder or disconnected tools are
  prohibited.
- Keep credentials in the shared device-sealed connection credential owner.
  Packages and connectors must never introduce their own secret store.
- Keep canonical user data in the domain repository. Plugins, Skills,
  Creations, Cards, connectors, and tool packages never own canonical data.

Calendar is the first strict reference implementation at
`runtime/resono_runtime/tools/calendar/`. Apply the same boundary to future
Contacts, Reminders, Files, Tasks, and other multi-surface domains unless an
accepted contract records a concrete reason not to.

## Required assumptions

- `ANDROID_HOME`/SDK and JDK environment are set in your shell for Android tasks.
- This repo is current and `GROUNDING-BASELINE.md` and the active delivery contract are
  already accepted.
- Device is a Rabbit R1 with USB debugging enabled.
- ADB can be allowed by your Linux USB permissions and cable.

## Build command used

From repo root:

```bash
./android/scripts/build_debug.sh
```

Note from this environment: host toolchain can fail at
`Could not initialize native services / libnative-platform.so` on some days.
The verified local recovery sequence is:

```bash
JAVA_HOME=/tmp/r1-jdk17 \
  PATH=/tmp/r1-jdk17/bin:/tmp/r1-android-sdk/platform-tools:$PATH \
  /tmp/gradle-9.5.0/bin/gradle --no-daemon --version

./android/scripts/build_debug.sh > /tmp/resono-build-debug.log 2>&1
tail -n 80 /tmp/resono-build-debug.log
```

The first command verifies/refreshes the pinned Gradle native runtime under the
same JDK as the build script. The second is the authoritative project build;
success ends with `BUILD SUCCESSFUL`, `standalone Android boundaries: OK`, and
`embedded runtime package: OK`. Do not replace the pinned JDK/Gradle paths or
delete Gradle caches blindly.

### Build 7 parser packaging note

Agent Skills uses `PyYAML==6.0.3` in
`android/runtime-host/build.gradle.kts`. Chaquopy's Python 3.13 arm64 index
does not provide `6.0.2`; it provides and installed the verified
`pyyaml-6.0.3-0-cp313-cp313-android_24_arm64_v8a.whl` plus
`chaquopy-libyaml`. Keep this exact pin until a recorded dependency decision
changes it. `android/scripts/check_runtime_package.sh` now asserts both
`yaml/_yaml.so` and the `chaquopy_libyaml` license payload in the built APK.

The current Build Contract 07 native-tab physical candidate is:

`artifacts/local-builds/ReSonoR1-build07-native-tabs-final-20260820T1315.apk`

SHA-256:
`83fcbeab84e045e479905f89bdd8ac0be0c6bee7003d87037680aa848973c91f`

This candidate replaces the rejected WebView scale experiments. Voice and Cards
are tabs under one persistent native `ProductChromeView`; the built-in Creation
catalog is native, and WebView is reserved for an activated imported Creation.
It is physically installed and starts without a fatal exception, but remains a
candidate until owner interaction/visual acceptance.

## ADB connection sequence (verified)

### Important: reuse the running ADB server and allow USB discovery to settle

Do **not** begin every deployment with `adb kill-server`. On this host that can
turn a working R1 transport into a temporary empty device list while `udev` and
ADB rediscover the same USB interface. First query the existing server:

```bash
/tmp/r1-android-sdk/platform-tools/adb devices -l
```

If the Rabbit is physically present but the first query is empty, wait and poll
the same server before restarting anything:

```bash
for attempt in 1 2 3 4 5; do
  /tmp/r1-android-sdk/platform-tools/adb devices -l
  sleep 2
done
```

The verified serial is `919109A5P1600502814D`. On 2026-08-20 the device appeared
on port 5037 after the earlier empty result once USB discovery finished. Servers
also existed on ports 5038, 5039, and 50399, but they had no R1 transport. Do not
guess a different port without querying it explicitly with
`ADB_SERVER_SOCKET=tcp:127.0.0.1:<port>`.

Only use the kill/start sequence below when no usable server exists after the
polling window.

1. Start/restart ADB and verify transport:

```bash
/tmp/r1-android-sdk/platform-tools/adb kill-server
/tmp/r1-android-sdk/platform-tools/adb start-server
/tmp/r1-android-sdk/platform-tools/adb devices -l
```

After every ADB server restart, the user **must physically unplug and reconnect
the R1 before device discovery is retried**. Do not silently poll or proceed to
install immediately after `adb start-server`; tell the user to reconnect the
device, wait for that action, and then run `adb devices -l`. The transport may
remain empty until this physical reconnect occurs.

Expected output should show:

```
List of devices attached
919109A5P1600502814D   device usb:1-1 ...
```

2. Install the APK:

```bash
/tmp/r1-android-sdk/platform-tools/adb install -r -d artifacts/local-builds/ReSonoR1-debug-20260819T133123Z.apk
```

3. Verify installed package and version:

```bash
/tmp/r1-android-sdk/platform-tools/adb shell pm list packages com.resonolabs.voice.engineering
/tmp/r1-android-sdk/platform-tools/adb shell dumpsys package com.resonolabs.voice.engineering | rg -n "versionName|versionCode|userId"
```

Observed values from this run:
- versionName: `0.4.24-openai-settings-controls-debug`
- versionCode: `29`

4. Bring HOME app to front (if needed):

```bash
/tmp/r1-android-sdk/platform-tools/adb shell am start -n com.resonolabs.voice.engineering/com.resonolabs.voice.MainActivity
```

5. Confirm active process:

```bash
/tmp/r1-android-sdk/platform-tools/adb shell pidof com.resonolabs.voice.engineering
```

## Runtime / management verification from host

After install, confirm runtime is serving HTTPS management:

```bash
# find device IP on wlan0 (from device itself)
/tmp/r1-android-sdk/platform-tools/adb shell ip -4 addr show wlan0

# forward device 8443 to host 8443 if you want local access via 127.0.0.1
/tmp/r1-android-sdk/platform-tools/adb forward tcp:8443 tcp:8443
```

Verify management HTTPS route:

```bash
curl -k -m 5 https://127.0.0.1:8443/
curl -k -m 5 https://127.0.0.1:8443/management/certificate.pem
```

Expected:
- `/` returns HTML for the management shell.
- `/management/certificate.pem` returns PEM certificate text (404 is expected for `/management/index.html`
  because the server maps `/` to the index and uses `/management/management.css` + `/management/app.js` assets).

Management API endpoints are protected by the pairing token and are accessed from the UI flow.
Use the web page to pair and then call `/v1/management/status`, etc.

## Useful logs/checks

Grab live and recent app/runtime logs:

```bash
/tmp/r1-android-sdk/platform-tools/adb logcat -c
/tmp/r1-android-sdk/platform-tools/adb logcat -v time | rg "ReSonoRuntime|RuntimeManagement|RuntimeHttpsServer|ReSonoVoice|Management"
```

For immediate status:

```bash
/tmp/r1-android-sdk/platform-tools/adb logcat -d -s ReSonoRuntime RuntimeManagement ManagementHttpsServer ManagementAssetStore RuntimeVoiceClient ReSonoVoice -v time | tail -n 80
```

## Camera motor-service deployment boundary

The Camera/Direct Handoff implementation builds two APKs:

```bash
./android/scripts/build_debug.sh
JAVA_HOME=/tmp/r1-jdk17 \
ANDROID_HOME=/tmp/r1-android-sdk \
ANDROID_SDK_ROOT=/tmp/r1-android-sdk \
PATH=/tmp/r1-jdk17/bin:/tmp/r1-android-sdk/platform-tools:$PATH \
  /tmp/gradle-9.5.0/bin/gradle -p android --no-daemon \
  --no-configuration-cache :system:motor-service:assembleDebug
```

Artifacts:

- HOME: `android/app/build/outputs/apk/debug/app-debug.apk`
- motor service: `android/system/motor-service/build/outputs/apk/debug/motor-service-debug.apk`

On 2026-08-20 both debug-signed APKs installed successfully on serial `919109A5P1600502814D`, but the debug-signed motor service ran as `u:r:untrusted_app:s0` and received `EACCES` opening the motor node. Historical donor evidence proves the working engineering bridge was instead re-signed with CipherOS's matching public AOSP development platform key and then installed normally under `/data/app`; it ran as `u:r:platform_app:s0`. The donor failed to preserve that signed artifact or command, so do not use its current debug APK as evidence.

For this specific `cipher_r1-userdebug 16` device, obtain `platform.pk8` and `platform.x509.pem` from AOSP's official `platform/build/target/product/security` tree, then run:

```bash
android/scripts/sign_motor_service_for_r1.sh /path/to/platform.pk8 /path/to/platform.x509.pem
```

The script fails unless the output certificate digest is exactly `c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8`, matching the installed CipherOS platform package. Install `motor-service-r1-platform.apk`, then confirm `ps -AZ` reports `u:r:platform_app:s0` before testing movement. Never use `setenforce 0`, HOME-owned sysfs writes, broad untrusted-app rules, or manual motor writes. A production image signed with non-public release keys must supply its own narrow platform/system-service identity and policy; the public AOSP development key is valid only for this userdebug engineering baseline.

The first platform-signed deployment produced HOME SHA-256 `539bab64893c363b17b1da2c7b1046eac3ca9447545f4815ebe3938ee06ef3a8` and motor-service SHA-256 `a11147d0e60e889d9044aa6ab323642029a5fc8b8100afe61cb62da5c3923899`. It proved platform access and swipe wiring, but its donor raw-position labels were physically wrong: `180` closed the shutter and `90` faced the user. Do not reinstall that motor artifact. Product-device authority is `0 = OUTWARD`, `90 = INWARD`, `180 = CLOSED`; transitions between exposed directions pass through CLOSED, and every exit/error must return to confirmed `180`.

The final orientation-control deployment is HOME SHA-256 `023112d233cdc26d2253804dd7529c069bd2f3960fdeacc7a9110b2a2729099e` and motor-service SHA-256 `102cea3aa4d853a29d889ad8835feed991482e560b892280608cf86fb68c9c29`, service version `2 / 1.1-r1-physical-map`. OUTWARD requests raw `180` and then opens Camera2 ID `0` directly; do not pre-command `0`, which causes a full sweep through the user-facing position. Camera shutdown waits for Camera2 `onClosed`, then commands HOME raw `180`. The final physical trace showed no preliminary `0/90`, Camera2 disconnect before HOME, and final command state `180`. The UI exposes real `Toward you` and `Outward` controls, defaulting to Outward. Sysfs is command readback, not mechanical-arrival proof.

## Current known-good local references

- Candidate install evidence:  
  `artifacts/local-builds/ReSonoR1-debug-20260819T133123Z.apk`
- Accepted physical baseline (reference):  
  `artifacts/accepted-bases/v26/ReSonoR1-v26-physical-working-base.apk`
- Most recent runtime candidate used for current deployment: version in package output above.

## Notes for future contributors

- If `adb devices` is empty but USB cable is present:
  - Re-seat cable/port, confirm device has developer mode + USB debugging enabled.
  - Re-run kill-server/start-server and wait 2-3 seconds.
  - Ensure host user is in `plugdev` and `/dev/bus/usb/*/*` is readable.
  - Run `lsusb`; the R1 used here appears as `0e8d:201c MediaTek Inc. rabbit r1`.
  - Check the interface with `lsusb -v -d 0e8d:201c`; it must report
    `iInterface ... ADB Interface`.
  - Check the current `/dev/bus/usb/<bus>/<device>` node. The working ownership
    is `root:plugdev` with group read/write, and user `christian` is in
    `plugdev`.
  - If `lsusb -v -d 0e8d:201c` shows `ADB Interface` but ADB remains empty,
    restart host USB discovery with `sudo systemctl restart udev`, then repeat
    the polling sequence above. Run the `sudo` command in the user's terminal;
    an automated non-interactive shell cannot supply the sudo password. Replug
    only if polling still does not restore the transport. This exact recovery
    restored serial `919109A5P1600502814D` on 2026-08-20.
- Do not rely on `/management/index.html` for route testing. Use `/` for page entry.
- Keep host toolchain stable (`adb`, SDK, JDK) to avoid environment-dependent build blockers.

## Build Contract 07 management UI deployment

The management overhaul is source-owned by:

```text
web/management/index.html
web/management/management.css
web/management/app.js
web/management/build07.js
web/design/tokens.css
web/design/base.css
```

`android/scripts/build_debug.sh` copies these sources into runtime-host assets.
`ManagementAssetStore` must explicitly map every served asset; on 2026-08-20 the
new `/management/build07.js` route was added and verified from the physical R1.

If Gradle reports `Failed to load native library 'libnative-platform.so'`, keep
the repository untouched and use a fresh temporary Gradle home:

```bash
GRADLE_USER_HOME=/tmp/resono-gradle-ui-overhaul ./android/scripts/build_debug.sh
```

The successful build ends with 196 tasks plus:

```text
BUILD SUCCESSFUL
standalone Android boundaries: OK
embedded runtime package: OK
```

The focused Build 07 host contract command is:

```bash
PYTHONPATH=runtime uv run \
  --with PyYAML --with jsonschema --with pytest -- \
  python -m pytest \
  tests/runtime/test_skill_routes.py \
  tests/runtime/test_build07_api_auth.py \
  tests/runtime/test_connection_routes.py \
  tests/runtime/test_mail_contract.py \
  tests/runtime/test_plugin_archives.py \
  tests/runtime/test_plugin_lifecycle.py \
  tests/runtime/test_mcp_connections.py \
  tests/runtime/test_mcp_lifecycle.py \
  tests/runtime/test_creations.py \
  tests/runtime/test_tool_catalog.py
```

Expected result from 2026-08-20: `22 passed`.

Install the just-built APK without restarting a working ADB daemon:

```bash
/tmp/r1-android-sdk/platform-tools/adb install -r -d \
  android/app/build/outputs/apk/debug/app-debug.apk
/tmp/r1-android-sdk/platform-tools/adb shell am start -n \
  com.resonolabs.voice.engineering/com.resonolabs.voice.MainActivity
```

Physical deployment evidence from 2026-08-20:

- serial: `919109A5P1600502814D`
- package: `com.resonolabs.voice.engineering`
- installed version: code `29`, name `0.4.24-openai-settings-controls-debug`
- process after launch: running
- device Wi-Fi management address: `https://192.168.1.196:8443/`
- forwarded management root: HTTP 200
- forwarded `/management/build07.js`: HTTP 200

The address is DHCP-dependent; always read `wlan0` again for a later deployment.
HTTP 200 proves serving and packaging, not owner visual or interaction acceptance.

After `am force-stop` and restart, HTTPS may briefly fail its TLS handshake while
the embedded runtime starts. Wait five seconds and retry before diagnosing or
reinstalling. The 2026-08-20 corrected flat management UI installed successfully;
after the startup delay both `/` and `/management/management.css` returned HTTP
200 from the physical R1.

## WebView provider recovery for Cards / Creations

The stripped R1 image retains the AOSP package `com.android.webview`. Android can
occasionally report that package as valid and enabled while selecting no current
provider, which makes constructing the Cards WebView crash HOME with
`MissingWebViewPackageException`.

Inspect and repair the provider selection with:

```bash
/tmp/r1-android-sdk/platform-tools/adb shell dumpsys webviewupdate
/tmp/r1-android-sdk/platform-tools/adb shell cmd webviewupdate set-webview-implementation com.android.webview
/tmp/r1-android-sdk/platform-tools/adb shell dumpsys webviewupdate
```

The repaired state must report `Current WebView package` as
`com.android.webview`, `Any WebView package installed: true`, and completed
relro initialization. This is a system-image prerequisite for real Cards and
imported Creation HTML; do not add a fake application fallback.

## Database location and inspection

The runtime database is stored in **device-protected storage** (not `/data/data/`):

```
/data/user_de/0/com.resonolabs.voice.engineering/files/runtime/data/resono.sqlite3
```

To inspect the database:

```bash
# List all tables
/tmp/r1-android-sdk/platform-tools/adb shell "sqlite3 /data/user_de/0/com.resonolabs.voice.engineering/files/runtime/data/resono.sqlite3 'SELECT name FROM sqlite_master WHERE type=\"table\" ORDER BY name;'"

# Check migration version
/tmp/r1-android-sdk/platform-tools/adb shell "sqlite3 /data/user_de/0/com.resonolabs.voice.engineering/files/runtime/data/resono.sqlite3 'SELECT * FROM schema_migrations;'"

# Check transcript/metrics counts
/tmp/r1-android-sdk/platform-tools/adb shell "sqlite3 /data/user_de/0/com.resonolabs.voice.engineering/files/runtime/data/resono.sqlite3 'SELECT COUNT(*) FROM session_transcript_entries; SELECT COUNT(*) FROM session_summaries; SELECT COUNT(*) FROM memory_records; SELECT COUNT(*) FROM memory_embeddings;'"

# View recent transcripts
/tmp/r1-android-sdk/platform-tools/adb shell "sqlite3 /data/user_de/0/com.resonolabs.voice.engineering/files/runtime/data/resono.sqlite3 'SELECT session_id, role, event_type, created_at FROM session_transcript_entries ORDER BY created_at DESC LIMIT 10;'"
```

For table/column names, check local SQL build files:
- Schema: `runtime/resono_runtime/storage/database.py`
- Tables: `session_transcript_entries`, `session_summaries`, `memory_records`, `memory_embeddings`

## Build Contract 06 — sessions & memory (operational notes)

Governing doc: `docs/planning/2026-08-16-build-contract-06-sessions-memory.md`
(includes the 2026-08-20 addendum with the finalize-chain repair details).

### Shared provider credential via OAuth (important for all future builds)

There is **one credential decision for the whole runtime**, and it supports the
ChatGPT **subscription OAuth token** as a first-class credential — agents and
embeddings ride the same token:

- Resolver: `runtime/resono_runtime/providers/openai/access.py`
  (`openai_provider_access`) — the configured access path decides:
  `subscription` → OAuth access token + Codex base URL
  (`https://chatgpt.com/backend-api/codex`); `platform` → Keystore Platform key.
- **Every consumer must use it** — text runner, memory review agent, embeddings,
  and any future agent. Do not inline credential logic in a new agent or feature.
- Embeddings call `api.openai.com/v1/embeddings` with the resolved token
  (subscription token works; owner-confirmed). Without a usable credential,
  memory paths degrade honestly (no fake vectors); agents raise 409.
- Memory-side adapter: `runtime/resono_runtime/memory/embedding_access.py`.

### Session → memory flow (what "working" means)

1. Native voice captures user/assistant transcripts during the session.
2. On **any** session end (stop, provider/peer failure, view teardown),
   `VoicePageView.dispatchPendingFinalize()` posts entries to
   `http://127.0.0.1:8765/v1/voice/sessions/finalize`.
3. The runtime appends entries, then runs the Agents SDK review +
   embeddings **synchronously** (expect tens of seconds; the native client
   waits 65s).
4. Result: `session_summaries` row, `memory_records` rows, and
   `memory_embeddings` vectors (summary + each memory) with session provenance.
5. Next session start injects recent memories + previous summary into the
   Realtime instructions; `memory_lookup` is the voice model's mid-session tool.

Verify with the DB count query in "Database location and inspection" above —
a healthy finalized session makes all four tables non-zero. Wait ~90s after
session end before judging.

### Memory debugging logs

```bash
/tmp/r1-android-sdk/platform-tools/adb logcat -v time | rg "VoicePageView|RuntimeVoiceClient|ReSonoRuntime"
```

Look for `session finalized` / `session finalize failed` (Android) and
`voice.session.finalize` / `voice.session.finalize_failed` /
`memory.review.started|completed|failed` (runtime). Failures are logged with
reasons; the finalize routes return a logged 500 `finalize_failed` on
unexpected errors instead of dropping the connection.

### Module ownership (keep the structure)

- Endpoints/routes: `runtime/resono_runtime/api/routes.py` (transport stays in
  `api/http_server.py`).
- Credential decision: `providers/openai/access.py` (see above).
- Agent execution: `agents/sdk_runner.py` (one Agents SDK path for all agents).
- Memory pipeline: `memory/pipeline.py`; retrieval: `memory/retrieval.py`;
  session-start context: `memory/session_context.py`.

### Tests

```bash
PYTHONPATH=runtime python3 -m unittest discover -s tests/runtime
```

Known environment failure on this host: `test_runtime_environment` expects
Python 3.13 (host provides 3.11) — unrelated to product behavior.

## Build Contract 07 — focused subphase testing
### Built-in Calendar contract

Run the focused Calendar host contract with:

```bash
PYTHONPATH=runtime python3 -m unittest tests.runtime.test_calendar_contract
```

It covers migration 28, the transactional two-connection limit,
upcoming-only projection, read-only capability denial, and complete uniform
Calendar tool-package registration. Connector tests must use fakes and must
never target a user's real calendar.

Calendar presentation is owned by `:feature:calendar`, entered through the
built-in Calendar item in `:feature:cards`, and reads only
`/v1/calendar/upcoming`. Management owns connection setup/status only through
`/v1/management/calendar/accounts`; it must never render event content.

Build Contract 07 is owner-gated by subphase. Run only the focused test group
for the active subphase before updating its evidence record and requesting
approval for the next one. Do not substitute repeated full repository, Android,
or device runs for those focused checks.

### Built-in Tasks contract

Run the focused Tasks host contract with:

```bash
PYTHONPATH=runtime python3 -m unittest tests.runtime.test_tasks_contract
```

It covers the text-only Tasks schema and complete uniform Tasks tool
package registration. Tasks has no due date, schedule, reminder, notification,
connection, or management-page behavior. Its Card is owned by `:feature:tasks`,
is entered through `:feature:cards`, and reads only `/v1/tasks/active`.

### Rabbit Creation QR host checks

Rabbit QR imports use decoded descriptor JSON and the same Creation lifecycle;
the runtime does not decode QR image pixels. Run:

```bash
PYTHONPATH=runtime uv run \
  --with pydantic==2.12.2 \
  --with openai-agents==0.18.3 \
  --with pyyaml \
  python -m unittest \
  tests.runtime.test_creations \
  tests.runtime.test_build07_api_auth
```

The plain system Python command is no longer sufficient because the canonical
runtime agent and Skill imports require Pydantic, the OpenAI Agents SDK, and
PyYAML even when the focused test is exercising Creation/API boundaries.

Expected 2026-08-20 host result: `Ran 4 tests ... OK`. Physical acceptance must
still prove a real Rabbit QR descriptor, linked HTTPS rendering, persistence,
dynamic Cards refresh, deletion, and origin-storage cleanup.

Host-only Rabbit QR candidate (not installed):

`artifacts/local-builds/ReSonoR1-build07-rabbit-qr-host-20260820T1345.apk`

SHA-256:
`86c6e1ee588e01d78aa2ef295ee256611c47b6191b9fa8a7deb79a7137c2614b`

### 07A tool catalog and migration foundation

From repository root:

```bash
PYTHONPATH=runtime python3 -m unittest \
  tests.runtime.test_build07_api_auth \
  tests.runtime.test_connection_routes \
  tests.runtime.test_tool_catalog \
  tests.runtime.test_mcp_server \
  tests.runtime.test_openai_realtime_session \
  tests.runtime.test_runtime_lifecycle \
  tests.runtime.test_agents_sdk_runner
```

Expected 2026-08-20 result: `Ran 16 tests ... OK`.

This workspace may not have `.venv/bin/pytest`, and the system Python may not
have a `pytest` module. Use the standard-library command above; do not install
test dependencies merely to run this focused group. A full Android/package/device
acceptance run belongs only to Build 7 final subphase `07F`.

### 07F final implementation evidence

Run the focused Build 07 owners:

```bash
PYTHONPATH=runtime python3 -m unittest \
  tests.runtime.test_import_recovery \
  tests.runtime.test_tool_catalog \
  tests.runtime.test_mail_contract \
  tests.runtime.test_mcp_client \
  tests.runtime.test_mcp_lifecycle \
  tests.runtime.test_creations \
  tests.runtime.test_plugin_lifecycle \
  tests.runtime.test_skill_lifecycle \
  tests.runtime.test_web_search
```

Recorded 2026-08-20 audited result: `Ran 26 tests ... OK`.

Run the whole runtime suite once:

```bash
PYTHONPATH=runtime python3 -m unittest discover -s tests/runtime -p 'test_*.py'
```

Recorded host result: 112 tests, 111 passing. The sole failure is
`test_runtime_environment`: host `python3` is 3.11 while the product requires
Python 3.13. Do not weaken that assertion. The Android package check validates
the embedded Python 3.13 runtime.

Build the APK:

```bash
./android/scripts/build_debug.sh
```

If Gradle reports `libnative-platform.so`, run the pinned recovery once, then
rerun the build:

```bash
JAVA_HOME=/tmp/r1-jdk17 \
  PATH=/tmp/r1-jdk17/bin:/tmp/r1-android-sdk/platform-tools:$PATH \
  /tmp/gradle-9.5.0/bin/gradle --no-daemon --version

./android/scripts/build_debug.sh
```

Success must include `BUILD SUCCESSFUL`, `standalone Android boundaries: OK`,
and `embedded runtime package: OK`. The recorded candidate is
`artifacts/local-builds/ReSonoR1-build07-final-audit2-20260820T180000Z.apk`, SHA-256
`f26407acc926be0a3c1842f6033d49ad529f7b3ecfdcf8864f96ae5dcbcfe5b2`.
Build evidence does not replace the physical acceptance in Build Contract 07.

## Build Contract 08 - Background Agent focused testing

The repository may not have a root `.venv`. Use the pinned ephemeral test
environment and include transitive dependencies required by the runtime route
graph:

```bash
PYTHONPATH=runtime uv run --with jsonschema --with pytest -- \
  python -m pytest -q \
  tests/runtime/test_background_agent_contract.py \
  tests/runtime/test_background_agent_observability.py \
  tests/runtime/test_background_agent_execution.py \
  tests/runtime/test_background_agent_service.py \
  tests/runtime/test_background_agent_global_tools.py \
  tests/runtime/test_agents_sdk_runner.py \
  tests/runtime/test_background_completion_delivery.py

PYTHONPATH=runtime uv run --with PyYAML --with jsonschema --with pytest --with httpx -- \
  python -m pytest -q \
  tests/runtime/test_build07_api_auth.py \
  tests/runtime/test_runtime_lifecycle.py \
  tests/runtime/test_agents_sdk_runner.py \
  tests/runtime/test_mcp_server.py \
  tests/runtime/test_openai_realtime_session.py

node --check web/management/background-agent.js
```

Recorded 2026-08-21 result: 12 tests passed in the Background Agent contract,
observability, recipes, service, and tool group; 14 tests and 20 subtests passed
in the management/runtime/SDK integration group; JavaScript syntax passed.
The Android build also passed with 299 actionable tasks, standalone boundaries
OK, and embedded runtime packaging OK. The resulting
`android/app/build/outputs/apk/debug/app-debug.apk` has SHA-256
`726084841ded4a3cb0f7351ed88d31f86ca37470aa62abcc5dff7b4516e26c40`.
At the initial host checkpoint no device was visible to ADB. The later final
deployment evidence below supersedes that transport state. Host tests alone do
not accept live provider execution, Voice delegation, or physical R1 behavior.

### Build 08 final deployment corrections

The final deployed candidate is
`android/app/build/outputs/apk/debug/app-debug.apk`, SHA-256
`38273f53a6a5a0252610e724b1cb5239de606b16994a8baa7126cc240c61f23a`.
It fixes three package/startup boundaries discovered only during physical
deployment: the workspace package circular import, omission of
`background-agent.js` from Android assets, and omission of
`/v1/management/background-agent` plus its nested routes from the Java HTTPS
proxy allowlist. The package check now requires the Agent script.

Final device evidence on serial `919109A5P1600502814D`:

- runtime process ready;
- `127.0.0.1:8765` listening;
- management HTTPS `8443` listening;
- `/management/background-agent.js` returns HTTP 200 and passes `node --check`;
- unauthenticated `/v1/management/background-agent` returns the expected 403
  `browser_session_denied`, proving the HTTPS proxy reaches the Python route;
- Primary Voice workspace contract passes: durable workspace list/read and
  named run-workspace list/read are available, while write and publish are
  denied.

Refresh an already-open management browser after installing this candidate so
it loads the newly packaged Agent script. A paired browser should populate
settings and tools; Save is handled in JavaScript and remains on
`#background-agent`.

### Build 08 Agents SDK runtime correction

The Background Agent has one execution loop: OpenAI Agents SDK `Agent` and
`Runner`. Do not restore `background_agent/run_loop.py`, a reviewer/repair loop,
arbitrary JSON result parsing, or host-side completion reinterpretation.
Compatibility recipe values all map to the same typed SDK execution.

Run the focused correction gate with the actual Agents SDK dependency:

```bash
PYTHONPATH=runtime uv run \
  --with openai-agents==0.18.3 \
  --with PyYAML \
  --with jsonschema \
  --with pytest \
  -- python -m pytest \
  tests/runtime/test_background_agent_execution.py \
  tests/runtime/test_background_agent_observability.py \
  tests/runtime/test_background_agent_service.py \
  tests/runtime/test_background_agent_contract.py \
  tests/runtime/test_background_agent_global_tools.py \
  tests/runtime/test_agents_sdk_runner.py \
  tests/runtime/test_background_completion_delivery.py

node --check web/management/background-agent.js
```

Recorded 2026-08-21 correction result: 19 Python tests passed and JavaScript
syntax passed. Run Logs are projections of durable lifecycle/model/tool events.
Reasoning Logs contain provider-returned reasoning summaries and explicit typed
agent evidence only; never synthesize or expose private chain-of-thought.

Corrected deployed artifact:

```text
android/app/build/outputs/apk/debug/app-debug.apk
SHA-256 e0ecafa19f270b94fb2223bb2d31d9459c4724904e9c9c024cfd922f9781a7ff
package com.resonolabs.voice.engineering
activity com.resonolabs.voice.MainActivity
```

Recorded physical startup evidence on `919109A5P1600502814D`: install succeeded,
PID `13800` owns the running app, runtime port `8765` and management port `8443`
listen, and the inspected startup log has no matching fatal runtime error. Do
not use the obsolete package name `com.resonolabs.r1` when launching this build.

Physical run `e26aba74634f96e48f7f8d29` failed after active tool use with `Event
loop is closed`. It failed after about 74 seconds, not at the 300-second runtime
limit. A later request proved subscription streaming is mandatory with HTTP 400
`stream must be set to true`. The final contract uses `Runner.run_streamed` for
subscription, `Runner.run` for Platform, a fresh `AsyncExecutionRuntime` per
Background Agent goal, reasoning `summary="auto"`, and
`RunHooks.on_llm_end`. Do not reuse one factory-wide loop across goal MCP
sessions or defer model observation until final completion. Recorded correction
gate: 20 tests passed.

Deployed correction APK SHA-256:
`d5bbe6025070fb9badb87464fc34cb3f144cb98375afc6fe4bd2fe10ce1c8645`.
Recorded device evidence: install succeeded, PID `16638`, runtime ready, and
ports `8765` and `8443` listening. Historical runs cannot gain reasoning
summaries retroactively; validate with a new reasoning-enabled goal.

Final subscription-compatible deployment SHA-256:
`a486c31a8c8e8c53c0b400eaa8b9f22ba96f066332d0c557eed84d5e8ebc2e0b`.
Recorded device evidence: install succeeded, PID `17435`, runtime ready, and
ports `8765` and `8443` listening.

### Background Agent constraint audit

Do not rely on `MCPServerStreamableHttp` defaults. Its HTTP `timeout` and
`client_session_timeout_seconds` are separate; the latter defaults to five
seconds and caused abandoned web-search requests, provider `Connection error`,
late tool completions, and broken pipes. Background runs must propagate the
remaining configured run window to both fields.

Normal run workspaces use the visible total workspace-size setting as their
effective quota. Do not reintroduce hidden 128-file or 8 MB-per-file sublimits.
Path confinement, symlink rejection, and atomic writes remain security rules.

Reasoning Logs receive safe entries in the run-list projection. Polling must
compare the response signature, preserve expanded run IDs, and avoid replacing
the DOM when nothing changed. Recorded audit gate: 24 Python tests and
management JavaScript syntax passed.

Deployed reviewed constraint/UI candidate SHA-256:
`08be0d29ba474411a02992b36c4445a14b3684e913e08b63a995e7c319e39e7f`.
Recorded device evidence: install succeeded, PID `20916`, runtime ready, and
ports `8765` and `8443` listening.
