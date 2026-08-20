# Build Contract 05 — Working OpenAI Voice and Text

**Identity:** `R1-BUILD-CONTRACT-05-v0.1`  
**Grounding:** `GROUNDING-BASELINE-v0.5`  
**Delivery slice:** 4  
**Status:** Frozen and active  
**Latest execution state (2026-08-15):** built successfully from current tree as `android/app/build/outputs/apk/debug/app-debug.apk` (SHA-256 `b90e0929cd739ac8041cf6853d5eb50a4ac8384069df3671edbc9e28ebf3f516`), then copied to `artifacts/android-candidates/ReSonoR1-voice-v0.4.25-openai-tls-hostname-match.apk` as the current working checkpoint. Runtime tests for the provider catalog/model contract continue to pass in this branch.
**Current pass note:** provider/model/access/reasoning selection is standardized in runtime with a catalog-backed contract, then exposed identically to host routes (`/v1/host/openai/...`), paired management UI, and the native HOME settings. `gpt-live-1` is now present in catalog, defaults, and persisted host state. Host-side `/v1/host/openai` checks confirm Realtime model support and successful writes for `gpt-live-1`; management HTTPS certificate export is implemented. Transport-level `gpt-live-1` Realtime proof is owner-deferred.

## Outcome

On the physical R1, a paired user can securely configure OpenAI, select available text and Realtime models, complete one real OpenAI Agents SDK text turn, and complete one real native WebRTC Realtime Voice session. The R1 and browser show the same truthful session state. Both execution paths reach one real MCP tool through one permission boundary.

This is the smallest working product slice. It does not implement later product breadth.

## Included

- Android Keystore-backed OpenAI Platform credential create/status/delete.
- ChatGPT/Codex device-code OAuth adapted from the donor implementation.
- Separate runtime-reported provider, text model, Realtime model, access path, and reasoning selection.
- Multi-provider catalog and provider/connection metadata persisted in SQLite for future provider expansion.
- One OpenAI Agents SDK text runner. No custom agent loop.
- One useful deterministic local MCP tool and explicit allow/deny behavior shared by text and Voice.
- The proven Android `NativeVoicePeer` WebRTC audio/data-channel path.
- Local runtime SDP exchange with OpenAI Realtime and canonical live events.
- Native Voice page first and real browser setup/session controls using the New Browser Voice visual source.

## Excluded

Cards data, camera, memory extraction/vector search, Skills/Plugins lifecycle, Mail/Calendar/Contacts/Reminders, Hermes A2A, OpenClaw, External AI, other providers, arbitrary tools, OS cleanup, and final visual tuning. These remain in the accepted delivery plan.

## Donor freeze

All source projects remain read-only. Copies and adaptations occur only inside this repository.

| Concern | Read-only source | Destination |
|---|---|---|
| Native WebRTC | `project-3d3354dadcad/workspace/app/rabbit_r1/android/app/src/main/java/com/resonolabs/voice/NativeVoicePeer.java` (`b2514277…e35e35c3`) | `android/feature/voice/src/main/java/com/resonolabs/feature/voice/NativeVoicePeer.java` |
| Voice sequencing | `project-3d3354dadcad/workspace/app/rabbit_r1/android/app/src/main/java/com/resonolabs/voice/BrowserVoiceNativeClient.java` (`02b64d…8fc1`) | `android/feature/voice/.../VoiceSessionClient.java` |
| Secure records | preserved `reference/android-voice-platform/app/src/main/java/com/resonolabs/voice/SecureRecordStore.java` (`9b1a042f…f7b9a`) | `android/runtime-host/.../RuntimeCredentialStore.java` |
| Provider contracts | `project-3d3354dadcad/workspace/app/modules/inference_runtime/` (`provider_selection.py`, `selector.py`, `factory.py`, `execution_service.py`, `realtime_service.py`, `realtime_session_builder.py`) | `runtime/resono_runtime/providers/` |
| Subscription OAuth | `project-3d3354dadcad/workspace/app/modules/openai_subscription/` | `runtime/resono_runtime/providers/openai/subscription/` |
| Agents SDK runner | `project-3d3354dadcad/workspace/app/vault_runtime/agent_packages/runners/openai_agents.py` (`3540a35…56454ff`) | `runtime/resono_runtime/agents/runner.py` |
| OpenAI adapters | `project-3d3354dadcad/workspace/app/providers/ai/openai_responses.py` (`27b9f1…cef590`); `openai_realtime.py` (`34576e…3cd9b`) | `runtime/resono_runtime/providers/openai/` |
| Browser Voice | exact files indexed by `docs/NEW_BROWSER_VOICE_VISUAL_SYSTEM.md` | `web/` and `android/core/design`/`android/feature/voice` |

Before each copy, the complete source hash and destination are appended to `docs/DONOR_CODE_REFERENCE_MAP.md`. Unrelated Vault/Cloud/enrollment code is omitted.

## Dependency checkpoints

1. **Packaging proof.** `PASSED`: reviewed arm64 Android wheels for `jiter==0.16.0`, `pydantic-core==2.41.4`, and `rpds-py==0.25.1` are reproducibly built from hash-pinned upstream source. The package gate verifies Android CPython extension suffixes inside the nested Chaquopy archive. Physical version 15 reports successful imports of all three extensions plus `openai` and `agents`.
2. **Credentials and configuration.** `IMPLEMENTED`: the Keystore bridges, SQLite provider/access/model settings, paired management endpoints, redaction, and real setup UI exist. Credentials are not placed in source, APK assets, SQLite, browser storage, logs, or tests. Physical positive authorization remains part of the later proof checkpoints.
3. **Text and MCP.** `SUBSCRIPTION POSITIVE PASSED; PLATFORM PROOF OWNER-DEFERRED 2026-08-15`: the only text path uses the OpenAI Agents SDK and local MCP server/tool. Physical v26 completed GPT-5.6 Sol, MCP device status, and low-reasoning turns through the persisted subscription connection. The Platform key field and Keystore-backed storage are implemented; independent Platform text/Realtime proof remains required but is deferred until the owner resumes it.
4. **Native Voice.** `REALTIME 2.1 MINI + UPDATED VAD + NATIVE MCP PASSED; LIVE MODEL DEFERRED`: physical v28 reached native WebRTC `LIVE`, exercised the persisted greeting, detected the owner's spoken request with the updated VAD contract, invoked `get_device_status` through local MCP, returned the real runtime result, and settled back to `LIVE`. `gpt-live-1` transport validation is deferred by owner request.
5. **Connected UI.** Replace the temporary HOME with Voice page one. Add only controls backed by the implemented configuration/session APIs. Browser and R1 render real idle/connecting/live/responding/tool/failure state from the canonical event path.
6. **Subscription proof.** `COMPLETION/PERSISTENCE/TEXT/REALTIME MINI PASSED`: physical v26 retained subscription authorization across install/restart, completed text/MCP and Realtime 2.1 Mini without Platform fallback. `gpt-live-1` is now selectable from host/device settings but transport session proof is owner-deferred.
7. **Physical acceptance.** Build a separately versioned APK, preserve version 9 as rollback, install, and run the positive and negative matrix on the R1.

## Required evidence

- Offline tests for credential persistence/redaction/deletion, model validation, session state, MCP grants, API failures, and interrupted transport.
- Android unit/build/boundary/package checks and no donor modification.
- Physical platform-key text and Realtime sessions with redacted identifiers and real transcript/state.
- Physical subscription text and Realtime proofs separately; an unsupported result is reported truthfully and leaves Platform operation intact.
- R1 and browser UI state traces showing the real backend event that caused each visible state.
- Exact candidate APK path, size, SHA-256, installed version, rollback command, and owner acceptance.

## Internal attack and stop rules

- A beautiful screen with no live session fails.
- A successful HTTP completion outside the Agents SDK fails the text requirement.
- A model shown without runtime capability evidence fails.
- A tool call bypassing MCP or permission intersection fails.
- A long-lived credential in Python storage, browser storage, an APK asset, source, or logs stops the build.
- WebSocket audio substituted for the proven mobile WebRTC path fails.
- Platform credentials used during a claimed subscription proof fail.
- Adding later-slice features or a broad provider framework stops the build.
- Native dependency failure is recorded at its checkpoint; it does not authorize reinvention.

## Rollback

The installed version-9 APK remains untouched at `artifacts/android-candidates/ReSonoR1-runtime-v0.3.4-rollback-fix.apk`. Each new physical candidate uses a new version and hash. A failed provider feature is disabled without changing the proven runtime lifecycle, cellular service, or management transport.

## Exit

The contract exits only when the real physical vertical passes and the owner accepts it. Tests or mock screens alone cannot close it.

## Current verified evidence — 2026-08-14

- Implemented Keystore-backed OpenAI Platform credentials, SQLite provider/model selection, live model discovery, the paired management controls, and loopback-only SDP creation.
- Ported the proven native WebRTC peer and connected the real Realtime data channel to the native Voice page.
- Implemented one stable MCP `2025-11-25` Streamable HTTP boundary with initialization, session/version checks, `tools/list`, one granted `get_device_status` tool, denied unknown tools, and Realtime function-result return.
- Passed 21 Python runtime tests plus the Android build, module-boundary check, and embedded-runtime package check.
- Installed version code 13 (`0.4.3-voice-debug`) on the physical R1. The native renderer now uses the Browser Voice hierarchy and exact state names: idle, connecting, live, responding, and error. Idle and credential-missing error were physically captured from real application behavior; no simulated state screen was added.
- Preserved candidate `artifacts/android-candidates/ReSonoR1-voice-v0.4.3-browser-voice.apk`, 34,538,760 bytes, SHA-256 `1f206e257941a2ac26558f303d8c45e3051e4b3def4d982a99b007298471f99d`.
- Preserved the superseded physical v12 UI checkpoint separately at `artifacts/android-candidates/ReSonoR1-voice-v0.4.2-browser-states.apk`, SHA-256 `7d21200151e69ddae7068721eca93bb74f822f6cdd16b0db3f397061aadbc46c`.
- Preserved the failed version 14 packaging checkpoint at `artifacts/android-candidates/ReSonoR1-voice-v0.4.4-agents-runtime.apk`, SHA-256 `f4028a0c3e72eed17a7b70281ba57902f53e3f3d0f844afc0a51f1866cbe4114`; physical health correctly reported `not_ready` because the first wheel build used the wrong native extension suffix.
- Repacked those reviewed wheels with the Android CPython suffix, added a nested-archive package gate and reproducible wheel script, and passed 22 runtime tests plus the complete Android build.
- Installed physical version 15 (`0.4.5-agents-import-debug`). Paired HTTPS status returned `ready` for `jiter`, `pydantic_core`, `rpds`, `openai`, and `agents`. Redacted evidence is stored at `artifacts/evidence/build-contract-05/r1-v15-agent-runtime-health.json`.
- Preserved the exact version 15 APK at `artifacts/android-candidates/ReSonoR1-voice-v0.4.5-agents-import.apk`, 48,046,380 bytes, SHA-256 `44f7198a1073a879663b34a601b3d274ff188c719d376a3c33be60c9efcc4cdf`.
- Adapted the donor Agents SDK runner into `runtime/resono_runtime/agents/runner.py`: the only model-driven text path calls `Runner.run`, uses the selected model and Keystore credential, connects to the existing local Streamable HTTP MCP server with an explicit one-tool allowlist, and disables provider-sensitive tracing. The paired management website now has a real text-turn control backed by that endpoint. Offline tests and build checks pass; a credential-backed physical text result remains required.
- Passed 24 runtime tests and all Android checks, installed version 16 (`0.4.6-agents-text-debug`), and proved the real paired text endpoint denies an unconfigured request with HTTP 409 `credential_unavailable`. Evidence: `artifacts/evidence/build-contract-05/r1-v16-text-negative.json`.
- Preserved `artifacts/android-candidates/ReSonoR1-voice-v0.4.6-agents-text.apk`, 48,046,760 bytes, SHA-256 `104516d08f7727306af391411be5d9bba189667a2c78138391343f78b9c4694a`.
- Adapted the proven ChatGPT/Codex device-authorization flow into `runtime/resono_runtime/providers/openai/subscription.py`, with a separate Android Keystore-sealed subscription record, refresh/disconnect, one Platform-or-Subscription access selector, bounded subscription text/Realtime models, real management controls, and no hosted ReSono dependency. Pending device-auth state is intentionally memory-only; restarting the runtime requires starting authorization again.
- Preserved version 17 (`artifacts/android-candidates/ReSonoR1-voice-v0.4.7-subscription-oauth.apk`, SHA-256 `749d1f304476b3bd46b4cb6a926a250e9059980f0fa07c88d2016da4a5f47ef5`) as the truthful short-proxy-timeout failure and version 18 (`artifacts/android-candidates/ReSonoR1-voice-v0.4.8-subscription-timeout.apk`, SHA-256 `bd3a95e00351380720ca75ec23807693247c4c4fe8b7bf3882c65d18fc49f883`) as the truthful Android `urllib`/provider-edge transport failure.
- Reused the donor's proven `httpx` transport style and installed version 19. The physical R1 now returns HTTP 200 `auth_pending`, the exact OpenAI device verification URL, a user code, a five-second poll interval, and a truthful `auth_pending` poll before owner authorization. No secret values are retained in evidence.
- Removed host-generated duplicate bytecode from the Android dependency staging path before every build. The clean candidate is `artifacts/android-candidates/ReSonoR1-voice-v0.4.9-subscription-httpx-clean.apk`, 48,740,076 bytes, SHA-256 `37aa7792ccf398230131582fd5d44c88fcea330eb895cdf3990be4a0a0ca84dd`. Twenty-seven Python 3.13 runtime tests, JavaScript syntax, Android build/boundary, and nested package checks pass. Redacted physical evidence: `artifacts/evidence/build-contract-05/r1-v19-subscription-start-pending.json`.
- Corrected connection ownership after review found that the model form's generic disconnect action always targeted Platform access. Platform and ChatGPT now have explicit independent controls; removing the selected connection automatically selects the remaining connected path, while removing an unselected connection preserves the active path. Twenty-nine Python 3.13 runtime tests pass.
- Installed physical version 20 (`0.4.10-connection-ownership-debug`), confirmed runtime `ready`, served the corrected real same-LAN management interface, and repeated the real subscription start/pending flow without exposing secrets. Candidate: `artifacts/android-candidates/ReSonoR1-voice-v0.4.10-connection-ownership.apk`, 48,048,116 bytes, SHA-256 `0f95ab98bd57c9fcb6556dc840b6d48d485a8e3ababde11af89838418d85b636`. Evidence: `artifacts/evidence/build-contract-05/r1-v20-connection-ownership.json`.
- Corrected the native Voice state reducer against the exact Browser Voice event source: speech-stopped and response creation are `responding`; transcript completion does not prematurely return to `live`; `response.done` returns to `live`; and tool/follow-up work stays `responding` until the follow-up completes. Three focused Android unit tests cover these rules.
- Installed physical version 21 (`0.4.11-browser-voice-states-debug`) and re-proved real idle, missing-credential error, runtime loopback, and same-LAN management readiness. Candidate: `artifacts/android-candidates/ReSonoR1-voice-v0.4.11-browser-voice-states.apk`, 48,048,116 bytes, SHA-256 `847bc22262ee420a149039f548c92a5f7c2ba1da70c50f30f1f7f2dc457606fc`. Evidence: `artifacts/evidence/build-contract-05/r1-v21-browser-voice-state-correction.json`. Live responding/tool/response-done still requires a credential-backed physical session and is not claimed.
- Prevented overlapping device-authorization poll loops from the real management page. Version 22 serves the guarded OAuth control over same-LAN HTTPS on the physical R1. Candidate: `artifacts/android-candidates/ReSonoR1-voice-v0.4.12-oauth-ui-guard.apk`, 48,048,176 bytes, SHA-256 `151c93e220da447b9d8a022a3090faed9fbde770067d945872a11434c8c747bd`. Evidence: `artifacts/evidence/build-contract-05/r1-v22-oauth-ui-guard.json`.
- Corrected the paired HTTPS timeout boundary for real Platform model discovery and access selection: only provider-backed configuration routes receive a bounded 30 seconds; ordinary local management remains at three seconds, device authorization at 35 seconds, and Agents SDK text at 65 seconds. Installed version 23 is runtime-ready and serves same-LAN management. Candidate: `artifacts/android-candidates/ReSonoR1-voice-v0.4.13-provider-timeouts.apk`, 48,048,176 bytes, SHA-256 `a1a7f1643cf81a5c4a870d2b464e49b2557eab04ca5ae6859c5a68e2db1493ce`. Evidence: `artifacts/evidence/build-contract-05/r1-v23-provider-timeouts.json`. Actual Platform latency remains part of the credential-backed proof.
- Corrected subscription text request semantics from the exact donor Responses adapter: Platform text continues through Agents SDK `Runner.run`; ChatGPT/Codex text uses Agents SDK `Runner.run_streamed` with `ModelSettings(store=False)` against the Codex backend, while retaining the same local MCP server and tool grant. Installed version 24 is runtime/management ready with the corrected runner packaged. Candidate: `artifacts/android-candidates/ReSonoR1-voice-v0.4.14-codex-streaming.apk`, 48,048,168 bytes, SHA-256 `0b8b10ee341233bb2fc1fdfe0c074b389f9502cb057a66ee58912b4c89e07e8e`. Evidence: `artifacts/evidence/build-contract-05/r1-v24-codex-streaming.json`. Real subscription text/MCP remains open.

Physical version 26 is preserved read-only at `artifacts/accepted-bases/v26/ReSonoR1-v26-physical-working-base.apk`, 48,131,864 bytes, SHA-256 `a91f2577d59da393b85695d5a7b4f4aab293bf190b712ec0be08d51eef0a1202`. It proves subscription completion/persistence, GPT-5.6 Sol Agents SDK text, MCP device status, low reasoning, persisted profile, and Realtime 2.1 Mini live WebRTC. Evidence: `artifacts/evidence/build-contract-05/r1-v26-working-base-and-v27-offline-candidate.json`.

Version 27 remains the preserved offline-only donor-exact Realtime package. Version 28 carries that same Realtime/VAD contract plus owner-requested Display controls. It is installed from `artifacts/android-candidates/ReSonoR1-voice-v0.4.18-display-controls.apk`, 48,101,837 bytes, SHA-256 `3732b425721abc8fde5ef1af1f8aaa8a625fed26df0d6c465688686ff4c6c343`. Its first physical checkpoint confirmed brightness `98 -> 124`, restoration to `98`, the active HOME window's `KEEP_SCREEN_ON` flag, foreground runtime operation, and HTTP 200 same-LAN management delivery; the later session checkpoint below proves its live VAD behavior.

Physical v28 then completed the live Realtime/VAD/MCP checkpoint. Native WebRTC reached ICE `CONNECTED`/`COMPLETED`, opened `oai-events`, started physical microphone and speaker paths, rendered the personalized greeting, detected the owner's spoken request, showed truthful `LIVE -> RESPONDING -> LIVE` state, called `get_device_status` through authenticated local MCP, and returned the real `resono-runtime`/contract-version-1 result. Explicit stop returned to idle while HOME and the foreground runtime remained healthy. Redacted evidence: `artifacts/evidence/build-contract-05/r1-v28-realtime-vad-mcp.json` and its four hashed screenshots.
- 2026-08-15 provider-contract continuation: built the current tree's debug APK, copied it as `ReSonoR1-voice-v0.4.19-openai-model-contract.apk`, and ran host/route/build verification for the provider contract path.

- 2026-08-15 provider-contract pass: added runtime provider catalog/repository, provider access path switching, host and native settings parity for model/reasoning/provider selection, and added one-shot tests (`tests.runtime.test_openai_provider`, `tests.runtime.test_provider_catalog`). Android build verification required explicit JDK/SDK env override and now passes; runtime contract tests are passing.

- 2026-08-15 provider-contract continuation: added `gpt-live-1` into catalog/fallback defaults and selection validation; host routes now include provider and access update endpoints and runtime-backed UI reflection; debug build copied to `ReSonoR1-voice-v0.4.19-openai-model-contract.apk` and installed on-device with `versionCode=28`.
- 2026-08-15: Management HTTPS resilience update completed; built and copied as `artifacts/android-candidates/ReSonoR1-voice-v0.4.21-management-https-resilience.apk` to make the server tolerate transient I/O and keep same-LAN management reachable over time.
- 2026-08-15 TLS hostname-match fix pass: built and installed `artifacts/android-candidates/ReSonoR1-voice-v0.4.25-openai-tls-hostname-match.apk` (SHA-256 `b90e0929cd739ac8041cf6853d5eb50a4ac8384069df3671edbc9e28ebf3f516`) and verified cert-host alignment on-device at `192.168.1.196:8443`.
- Evidence: `artifacts/evidence/build-contract-05/r1-v25-tls-host-match.json`.

## Active open gates (Build Contract 05)

1. **`gpt-live-1` transport support (Build side):** owner-deferred and out of current contract order. It remains implemented in config/selection only, and will not gate this Build Contract while deferred.
2. **Open gate:** `normal-browser TLS trust` stability should remain continuously usable across foreground/background management sessions (owner has already confirmed platform text/realtime behavior). Gate is informational; do not gate later slices on this status unless it regresses.

### 2026-08-15 progress update

7/15 gates status:

- Gate 1 remains owner-deferred and not in the contract sequence.
- Gate 2 is active only as a stability watch: normal-browser TLS trust continuity should remain available when testing management and runtime callbacks.

### 2026-08-19 workspace validation update

- `runtime/resono_runtime/storage/provider_catalog.py`, runtime controller/provider endpoints, and management UI/native settings form a complete openai provider/model/access/reasoning contract in-tree.
- Runtime verification done in this workspace:
  - `./android/scripts/check_boundaries.sh`: passed
  - `./android/scripts/check_runtime_package.sh`: passed
  - `PYTHONPATH=runtime python3 -m unittest tests.runtime.test_provider_catalog tests.runtime.test_openai_provider tests.runtime.test_management_pairing tests.runtime.test_memory_sessions tests.runtime.test_openai_realtime_session tests.runtime.test_runtime_environment`
    - pass count: all pass except Python-version assertion in `test_required_standard_library_modules_import`, which expects 3.13.
  - `PYTHONPATH=runtime python3 -m unittest tests.runtime.test_memory_sessions tests.runtime.test_mcp_server tests.runtime.test_agents_sdk_runner tests.runtime.test_openai_subscription`: all 26 pass.
- `gpt-live-1` model selection remains implemented and accepted by controller/management contracts.
- `gpt-live-1` transport and Platform end-to-end physical validation remain owner-deferred.
- Build was completed with `./android/scripts/build_debug.sh`, then preserved as local evidence:
  - `artifacts/local-builds/ReSonoR1-debug-20260819T133123Z.apk`
  - `artifacts/local-builds/ReSonoR1-debug-20260819T133123Z.apk.sha256`
- Management trust remains aligned in the same-LAN browser path used previously (`/management/certificate.pem`) and is now part of the current in-tree candidate.
- `adb` deployment was retried in-session; native host socket policy prevented daemon startup in this environment (`Operation not permitted` on smartsocket bind). No new on-device install could be completed from this shell.

### 2026-08-19 next-step condition

- No remaining BC05 scope changes are pending from code review.
- Next build action is the contract handoff: confirm whether BC05 is complete with deferred `gpt-live-1` transport and TLS continuity by owner acceptance, or open BC06 only after that acceptance.

### 2026-08-15 TLS trust validation pass

- Performed direct TLS validation on the active device at `192.168.1.196:8443`.
- `openssl s_client` confirms endpoint reachability and live cert retrieval.
- The prior mismatch (`ReSono R1` vs `192.168.1.196`) was traced to certificate subject mismatch.
- This build now regenerates the TLS identity with the active local LAN certificate subject, and trust verification is now passing for `192.168.1.196` when using the exported `/management/certificate.pem`.

Status as of 2026-08-15:
- The contract remains active.
- Platform support remains implemented and deferred, not removed.
- On-device host-route evidence now includes `gpt-live-1` in active Realtime model list and successful host-side model selection through `/v1/host/openai/models`.
- Later slices remain closed until open gates above are completed.

Notes:
- Android build and on-device install were completed in this pass using `/tmp/r1-android-sdk/platform-tools/adb`.

Owner confirmed Platform text/Realtime execution is working. `gpt-live-1` remains deferred by design. This means the contract can advance to Slice 5 while keeping a watch on TLS trust continuity for the current management environment. Later slices remain closed until they are opened by the active phase boundary.
