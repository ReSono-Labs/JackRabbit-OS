# Build Contract 04 — Minimal On-Device Runtime

**Candidate:** `R1-BUILD-CONTRACT-04-v0.1`  
**Grounding:** `GROUNDING-BASELINE-v0.4`, owner decisions through OD-29  
**Delivery plan:** Delivery Slice 3 only  
**Status:** Owner accepted 2026-08-14; Checkpoints 1–5 and all required physical evidence pass on version 9; Slice 3 owner acceptance remains open  
**Predecessor:** Build Contract 03 architecture/reference evidence complete; its failed visual candidate remains prohibited from installation

## Exact success scenario

The clean R1 APK starts one separate `:runtime` process containing an embedded arm64 CPython interpreter. That process opens one real SQLite database, persists and retrieves a migration-owned record, exposes a small authenticated loopback API/event stream to the APK, and serves one paired HTTPS browser status surface on the local network. Killing the process causes a bounded restart. Activating an unhealthy runtime/configuration release automatically returns to the last healthy release.

This contract creates infrastructure, not a product facade. It includes no provider, model, agent, Voice control, Card, plugin, memory, Hermes, External AI, or personal-data screen. Voice remains the required first product page and Cards the second when their real verticals land.

## Packaging finding and selection

Read-only device evidence on 2026-08-14 found:

- connected test device `rabbit_r1`, arm64-v8a, Android 16;
- no system Python interpreter;
- approximately 108 GB available under writable `/data`;
- read-only system partitions and an app-owned writable data boundary.

A disposable `/tmp` proof established that Chaquopy 17 reaches Python dependency resolution with the current Gradle 9.5 / Android Gradle Plugin 9.3 project when Gradle configuration caching is disabled. The proof intentionally did not change this repository or the device.

The same proof found one later Slice 4 issue: donor-pinned `openai-agents==0.18.3` cannot yet resolve through Chaquopy for Python 3.11 because its `openai` dependency requires native `jiter`, for which that index has no Android wheel. Agents SDK is not applicable to this lifecycle-only slice, so it is not substituted or silently omitted from an agent feature. Before Slice 4 implementation, reproducible arm64 Android wheels for the exact native dependency set—at minimum `jiter` and `pydantic-core`—must build from reviewed upstream source and import successfully on the R1. Official Python documentation identifies embedded app distribution and Android wheels as the supported model; current `cibuildwheel` supports Android wheel builds.

The selected Slice 3 shape is:

```text
ReSono HOME APK process
        │ versioned localhost JSON/events
        ▼
Android RuntimeService process (:runtime)
        │ embeds CPython; no system Python assumption
        ▼
runtime/core + SQLite + paired HTTPS management boundary
```

The runtime remains a separately owned `runtime/` codebase even though Android requires its interpreter to ship inside an app package. Android presentation modules never own Python business logic, provider credentials, or SQLite repositories.

## Exact donor references

Read-only donor root:

`/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace`

| Concern | Exact donor reference | Standalone treatment |
|---|---|---|
| Loopback-only token requirement | `app/vault_runtime/local_api/config.py` | Retain the loopback/auth invariant; replace Vault/server configuration. |
| HTTP request/response adapter | `app/vault_runtime/local_api/server.py` | Reuse the small handler shape only; do not port PostgreSQL, platform providers, tunnels, notifications, or External AI. |
| Local API dispatch/auth/health semantics | `app/vault_runtime/local_api/app.py`, especially request dispatch, `/health`, and constant-time bearer validation | Extract only the minimal lifecycle contract into new standalone code. |
| Store interface and health behavior | `app/vault_runtime/local_api/stores.py` | Replace `PostgresVaultLocalApiStore` with one SQLite repository; no compatibility wrapper. |
| Explicit browser origin enforcement | `app/vault_runtime/local_api/config.py`; `app/vault_runtime/local_api/server.py` browser-startup handler | Preserve exact-origin allowlisting and wildcard denial; add pairing sessions and CSRF for the standalone management surface. |
| Diagnostics shape | `app/vault_runtime/edge_connector/diagnostics.py` | Reuse support-safe health/readiness ideas without importing the edge connector. |
| Relevant donor regressions | `tests/unit/test_vault_runtime_local_api.py`; `tests/unit/test_vault_runtime_local_api_config.py`; `tests/unit/test_identity_http_sessions.py` | Port only tests corresponding to retained auth/origin/health/session behavior. |

No donor file is modified. No donor package is copied wholesale.

## Repository destinations

```text
android/runtime-host/          # Android service, Keystore bridge, process lifecycle
runtime/
├── core/                      # trusted runtime entry, release health, API/events
├── api/                       # versioned loopback and management contracts
├── storage/                   # SQLite connection, migration 0001, repositories
├── security/                  # pairing/session/CSRF policy; no secret logging
└── tests/
web/
├── design/                    # smallest copied Browser Voice tokens/components
└── management/               # real pair + runtime status only
scripts/runtime/               # build, package, validate, install, recovery
```

Every copied donor-derived file or asset receives an exact source path and SHA-256 in the existing donor reference map/provenance record. No new planning authority is created outside this contract.

### Code organization rules

- One responsibility has one obvious owning module; there are no parallel implementations.
- Dependency direction is `Android host -> versioned runtime contract -> runtime service -> repository/security adapters`. Storage and transport never import presentation code.
- Public modules expose the smallest typed/versioned contract needed by a real caller. Internal implementation details remain internal.
- Names describe product behavior. Generic `utils`, `helpers`, `common`, `manager`, or catch-all service modules are prohibited unless a narrowly documented single responsibility genuinely requires the name.
- Configuration has one schema and one loader. Health, pairing, session, release, and database state each have one canonical owner.
- Files stay small enough to review; a file that accumulates unrelated lifecycle, HTTP, security, and storage behavior must be split before acceptance.
- Every top-level code area has a short README covering purpose, dependency direction, run/test commands, and where the next related change belongs.
- Tests mirror the production module structure and assert public behavior; no test-only production branches or duplicated fixtures that conceal contract drift.
- Copied donor code is reduced by deliberate extraction, with provenance retained. Obsolete Vault naming and compatibility shims do not enter the standalone core.
- A contributor should locate the owner of a runtime, storage, API, security, Android-host, or web change from the repository tree without reading the historical donor.

## Dependency-ordered checkpoints

1. **Interpreter-only packaging proof**
   - Package Python 3.13 for arm64-v8a in `android/runtime-host`.
   - Disable Gradle configuration caching only for the incompatible Python tasks/build.
   - Import standard-library `sqlite3`, `ssl`, `asyncio`, and `http.server` on the physical R1.
   - Do not install Agents SDK or future dependencies in this checkpoint.

2. **One runtime process and database**
   - Add one `RuntimeService` in `:runtime`, started explicitly by HOME and at boot under the accepted privileged package policy.
   - Create migration `0001` and one lifecycle-record repository using Python SQLite.
   - Keep trusted runtime releases, editable workspace, and data in separate app-owned directories.

3. **One versioned local boundary**
   - Bind the private API to `127.0.0.1` only.
   - Require a Keystore-protected bearer secret and constant-time comparison.
   - Implement only `/v1/health`, `/v1/events`, and the migration-owned proof record needed by this contract.
   - The APK consumes the real health/event boundary; it never infers readiness from elapsed time.

4. **Paired browser status**
   - Display a real short-lived pairing code from the R1 settings flow.
   - Serve HTTPS using a device key protected by Android Keystore.
   - After pairing, issue a short-lived, host-only browser session; require exact Origin and CSRF proof for mutations.
   - The only web content is the real New Browser Voice-styled pairing and runtime status/restart surface.

5. **Supervision and rollback**
   - Bounded restart after a forced process kill.
   - Atomic activation of versioned runtime/configuration state.
   - Health timeout returns to the last-known-good state and records a support-safe reason.
   - Preserve the accepted image and reference APK rollback paths.

## Functional invariants

| ID | Required invariant | Required failure/counterexample |
|---|---|---|
| BC4-I01 | Exactly one runtime product process. | Multiple Python workers, microservices, Docker, PostgreSQL, or a second orchestration stack fails review. |
| BC4-I02 | Runtime is standalone. | Any startup dependency on external Vault, ReSono Admin, claim, platform pairing, or hosted management fails. |
| BC4-I03 | SQLite is canonical for this slice. | PostgreSQL compatibility code, dual writes, or an in-memory success path fails. |
| BC4-I04 | Browser access is paired and scoped. | Wildcard Origin, reusable pairing code, browser-held device bearer token, missing CSRF, or plaintext secret logs fails. |
| BC4-I05 | Health is truthful. | UI animation, process existence, or HTTP 200 without database/migration readiness reports ready. |
| BC4-I06 | Core and workspace remain separate. | Browser editing overwrites trusted core, credentials appear in workspace, or failed activation destroys the last good state. |
| BC4-I07 | No future feature facade. | Provider/model/Voice/Cards/agent/plugin/memory controls appear before real implementations. |
| BC4-I08 | Donors remain read-only. | Any external project status/hash changes because of this work. |
| BC4-I09 | Clean structure is preserved. | Runtime business logic enters `MainActivity`, settings views, or an unowned utility collection. |
| BC4-I10 | Agents SDK risk is explicit. | Slice 4 starts before its exact native dependencies build and import on the physical R1, or a custom agent loop is substituted. |
| BC4-I11 | The codebase is understandable by construction. | Duplicate owners, circular dependencies, catch-all modules, scattered configuration, unexplained abstractions, or files mixing unrelated layers fail review even if tests pass. |

## Tests and evidence

Positive evidence:

- deterministic arm64 APK/runtime build from a clean cache;
- physical imports of Python 3.13 standard modules;
- migration/restart persistence;
- authenticated APK health and ordered event receipt;
- successful one-time browser pairing over HTTPS;
- real status/restart actions;
- forced process-kill recovery;
- failed release/config activation and automatic rollback.

Negative evidence:

- missing/wrong bearer denied;
- unpaired browser denied;
- reused/expired pairing code denied;
- wrong Origin and CSRF denied;
- unavailable/corrupt database reports not-ready;
- unknown route denied;
- secrets absent from logs and support-safe responses;
- prohibited hosted/Vault/PostgreSQL/provider strings and imports absent.
- architecture/boundary checks prove dependency direction, single ownership, and absence of catch-all modules or duplicate configuration loaders.

## Stop and rollback

Stop on interpreter import failure, unexplained native crash, database ambiguity, browser exposure without pairing/TLS, false health, restart loop, loss of last-known-good state, donor mutation, or pressure to add a future feature.

Before physical installation, preserve and verify the current reference and clean APK artifacts. Physical mutation requires the owner’s immediate approval for the exact APK. Rollback reinstalls the accepted reference APK or accepted Slice 2 image; runtime data created only for this contract may be cleared because the test device contains no user data, but deletion must still be explicit and recorded.

## Exit and next gate

Exit requires all five checkpoints, physical evidence, rollback proof, and owner acceptance. The next contract is Delivery Slice 4: real OpenAI access, Agents SDK text, native WebRTC Voice, model selection, and the actual Voice-first Browser Voice UI. Cards remains second and is exposed only when its real local domain source lands.

## Offline implementation evidence — 2026-08-14

- One arm64-only APK embeds CPython 3.13, SQLite, TLS libraries, and the standalone `runtime/` package in one `:runtime` process.
- SQLite migration/lifecycle persistence, authenticated health, lifecycle retrieval, ordered events, loopback-only binding, and corrupt-database not-ready behavior pass host tests.
- One-time pairing, exact HTTPS Origin binding, host-only secure browser session, CSRF-protected restart, expiry, and denial cases pass host tests.
- The R1 settings module consumes the real local pairing endpoint; the packaged management page consumes the real paired status/restart endpoints. No future feature controls exist.
- Android owns a device-generated Keystore TLS identity and a bounded four-client HTTPS adapter. Python remains the single owner of pairing/session/CSRF state.
- Atomic active/last-good runtime-configuration pointers pass healthy activation, rejected activation rollback, interrupted activation recovery, and path-escape tests.
- Android startup supervision permits normal sticky recovery but stops sticky restart after three startup failures within five minutes.
- Fourteen Python tests, the Android unit-test task, standalone dependency/source checks, JavaScript syntax check, and embedded APK content checks pass. The added regression covers a truncated active-release pointer.
- Version-code-5 physical startup proved HOME selection, exactly one `:runtime` process, embedded native library loading, database/directories, and Keystore HTTPS startup. Its HOME health request failed because Android denied private cleartext loopback; version 5 is retained as failure evidence.
- The version-code-6 correction permits cleartext only to `127.0.0.1`/`localhost`, keeps general cleartext denied, and reports required Python standard-library import evidence through truthful health.
- Version-code-6 physical startup fixed HOME health and rendered the real pairing page. Its TLS handshake failed because the Keystore EC key omitted digest modes Android Conscrypt requested; it also advertised the active cellular address while Wi-Fi was down.
- Version 7 created a new Keystore identity permitting the required TLS digest modes and restricted address advertising to Wi-Fi/Ethernet. Physical testing showed address selection was corrected, but the default key manager still selected the old TLS alias.
- Version 8 selected the exact new Keystore alias. Physical testing then proved HOME/runtime readiness, required Python/OpenSSL/SQLite imports, HTTPS 200 through USB forwarding, one-time pairing, authenticated status, unpaired/wrong-Origin/wrong-CSRF denial, real restart, process-kill recovery, and SQLite lifecycle persistence. The active cellular interface remained enabled while the UI correctly displayed `Connect R1 to Wi-Fi` instead of advertising it.
- The first physical rollback attempt was stopped safely after its device-side write truncated only `active.json`; `last-good.json` was immediately restored before any runtime kill. That exposed a real recovery gap for malformed pointers.
- Version 9 catches malformed/truncated active-pointer reads and atomically restores the intact last-good pointer. The exact installed artifact is `artifacts/android-candidates/ReSonoR1-runtime-v0.3.4-rollback-fix.apk`, 21,806,951 bytes, SHA-256 `183c2932d706bc84813b9f569039f0f160b84f4ec5755efe74e645ade193dac5`.
- Physical version-9 proof deliberately truncated only `active.json`, verified `last-good.json` remained intact, and killed only runtime PID 11975. Android restarted the runtime as PID 12146 while HOME remained PID 11954; both pointers recovered to `embedded-0.3.0`, activation status became `rolled_back`, listeners on `127.0.0.1:8765` and `*:8443` returned, the SQLite start counter advanced from 7 to 8, and the real HTTPS management page returned 200 through USB forwarding.

- After the R1 joined Wi-Fi, its native Management page truthfully displayed `https://192.168.1.196:8443`. A same-LAN host at `192.168.1.170` reached that address directly without ADB forwarding: the real page returned HTTPS 200, unpaired status returned 403, one-time pairing returned 200, authenticated status returned 200 with fully ready runtime/database/release/Python evidence, and reuse of the consumed code returned 403.
- Cellular remained independently active at `10.0.201.40` throughout the Wi-Fi proof and was not advertised as a management address.

All Build Contract 04 technical exit evidence now passes. Slice 3 remains open only for explicit owner acceptance; Slice 4 has not begun.

## Owner acceptance gate

Acceptance authorizes offline implementation and disposable packaging tests for Checkpoints 1–4. It does not authorize installing an APK, changing the test device, modifying the system image, or beginning Slice 4. Those actions keep their separate gates.

**Result:** `CONTINUE` — offline implementation accepted by the owner with “continue” on 2026-08-14. The owner separately approved each installed physical correction through version 9. Final Slice 3 acceptance remains open.
