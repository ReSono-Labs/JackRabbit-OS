# ReSono Labs R1 Voice — Master Delivery Plan

**Candidate:** `R1-STANDALONE-DELIVERY-PLAN-v0.3`  
**Grounding:** `GROUNDING-BASELINE-v0.5`  
**Status:** Owner accepted 2026-08-14; Delivery Slices 1–3 accepted; Slice 4 is active under Build Contract 05  

> **Owner scope correction, 2026-08-20:** Contacts, Reminders, and External AI are deferred from the first integrated build and may return later as packages. The controlling deferral record is `docs/planning/2026-08-20-first-build-deferrals.md`. The first-party Tasks package is a simple local text/completion capability controlled by `docs/planning/2026-08-20-first-party-tasks-package.md`.
**Supersedes:** Accepted v0.2 after the owner reopened planning for documentation, APK, OS, and sequencing drift  

> This is the only delivery plan. It owns dependency order, delivery slices, tests, evidence, rollback, and exit gates. [GROUNDING-BASELINE.md](../../GROUNDING-BASELINE.md) alone owns product scope and owner decisions. [DONOR_CODE_REFERENCE_MAP.md](../DONOR_CODE_REFERENCE_MAP.md) alone owns donor identities and file locations.

> Mockups are prohibited. Every interface must be connected to the real behavior it presents. No simulated provider, fake endpoint, placeholder product state, facade service, or disconnected screen can satisfy a deliverable.

## Actual project state

- The standalone repository contains the accepted grounding/plan, the byte-verified Android donor reference and donor APK, and locally reproduced reference builds. The version-code-3 reference build disconnects the hosted enrollment branch so the real donor UI can be evaluated on the early image; it is not the clean product APK.
- It contains the exact installed APK rollback artifact, current-device read-only capture, and copied same-device restore/fastboot evidence. The owner accepts current device behavior as working except for the camera; camera work is deferred.
- It contains deterministic early image candidate `R1-EARLY-IMAGE-v0.1`, a guarded active-slot apply/rollback tool, and physical acceptance of that running early image.
- It contains and physically runs a working minimal on-device runtime and real paired HTTPS management website. External AI gateway code and the final release image toolchain do not yet exist.
- The primary donor contains the substantial modular ReSono HOME APK, Android build/install scripts, hardware modules, native WebRTC, Voice UI, Vault/runtime behavior, New Browser Voice, and image/recovery evidence.
- Donor image records contain multiple historical candidates. The selected restore record is tied to the same device, build, installed APK hash, and current slot and is preserved in the standalone baseline as recovery evidence.
- The owner states that the current intended base is the working CipherOS/Rabbit hardware stack, owns the referenced ReSono projects, and authorizes copying into this repository. Donors remain read-only.
- Current ADB identity, HOME, packages, signing, boot-critical partition hashes, rollback APK, and same-device recovery route are recorded. The accepted early image runs on the test R1; physical version 26 is the accepted working HOME/runtime base and is preserved read-only. Version 28 is currently installed and physically proves Display controls plus runtime/management availability; its updated VAD behavior still awaits a live session.
- The community-facing organization repository is a single clean root containing only product source, tests, management UI, public README, and public screenshots. Internal grounding, plans, reviews, donor/reference material, device evidence, and operational records remain local-only. The owner selected free non-commercial use with commercial use requiring written ReSono Labs permission; formal license text and third-party notices remain a Slice 10 gate.
- There is no committed schedule, contributor roster, hosted operator, or release budget. Slices are dependency gates, not dates.

## Planned product outcome

The community release is one recoverable R1 product composed of:

```text
retained Rabbit/Cipher hardware substrate
        + stripped ReSono system image
        + standalone ReSono HOME APK
        + supervised on-device ReSono runtime
        + local New Browser Voice management site
        + later-package External AI integration (deferred from first build)
```

The first integrated release retains the owner-selected core capabilities. Mail proves the personal-data/plugin boundary; Calendar and simple local Tasks remain first-build work. Contacts, Reminders, and External AI are deferred to later packages under the 2026-08-20 owner correction.

## Planning boundaries

### In scope

- All work authorized by `GROUNDING-BASELINE-v0.5`, including the existing APK port, two-stage system-image cleanup, runtime, Voice/text, memory, standards-based extensions, all four personal-data domains, Hermes, New Browser Voice, and External AI/ChatGPT.
- Exact donor-first copying and cleanup inside this repository only.
- Real physical R1 evidence at every APK/image boundary.

### Out of scope

- Low-level driver, firmware, kernel, or HAL rewrite.
- OpenClaw implementation, additional model providers, additional External AI clients, local LLMs, marketplace, hosted remote management, or general shell access.
- Any mock product work.

### Donor intake rule

Before copying a coherent component, record its repository, exact revision and dirty-file hashes, source paths, destination paths, retained behavior, omitted behavior, third-party/license disposition, and tests. Copy only into this repository. The owner has authorized copying; public-release licensing and third-party notices remain a release gate.

## Plan Material Decision Gates

### P-MDG-01 — First physical work

- **Question:** Start with schemas/runtime infrastructure, strip the OS immediately, or first reproduce the existing APK and current device baseline?
- **Authority/evidence:** OD-01–OD-03, OD-12, OD-18, OD-25; F-16–F-18; U-07; owner preference to clean the OS early.
- **Alternatives:** Abstract foundation first; destructive OS cleanup first; read-only device capture plus coherent APK reproduction followed by reversible cleanup; blocked without device/recovery access.
- **Selection/function:** Capture the device without mutation, copy and reproduce the existing Android project, prove it on the untouched base, then create the early reversible ReSono image. This makes the OS an immediate product track without removing its working replacements or recovery path first.
- **Counterexample:** A schema suite passes while no APK builds, or Cipher UI is removed before ReSono HOME/settings/hardware replacements work.
- **Dependents:** Slices 1–2 and every later physical claim.
- **Result:** `CONDITIONAL` on U-07.

### P-MDG-02 — Android reference and clean product shape

- **Question:** Keep carving hosted-platform behavior out of the coherent donor copy, rewrite proven hardware/media behavior, or preserve that copy as reference and create one clean product composition using selected proven components?
- **Authority/evidence:** OD-02, OD-18, OD-24; F-01, F-16; Gradle module dependencies and existing tests.
- **Alternatives:** Indefinitely clean the coherent donor tree; rewrite everything; preserve the coherent tree as a proven reference and selectively port its working components into one clean product APK.
- **Selection/function:** The coherent donor copy established the physical reference baseline. Preserve it with provenance, then create one small product Android tree from the ground up. Port the proven WebRTC peer, R1 input/wheel/button/motor adapters, power behavior, and required real views; do not port hosted enrollment, claim, serialization, external Vault relay, or platform startup code. This is one product architecture plus one non-product reference, not two competing implementations.
- **Counterexample:** Product startup still asks ReSono Admin for approval; the reference tree is gradually renamed as the product; or proven WebRTC/hardware behavior is rewritten without evidence.
- **Dependents:** APK build, native UI, Voice, image composition, hardware tests.
- **Result:** `CONTINUE`, subject to the slice import record.

### P-MDG-03 — Image timing

- **Question:** Complete all image removal now, defer all image work, or use early and final image checkpoints?
- **Authority/evidence:** MDG-11; donor image failures around HOME, provisioning, permissions, signing, motor service, and recovery.
- **Alternatives:** One early destructive rebuild; one late rebuild; two-stage reversible image work.
- **Selection/function:** Slice 2 creates a clean engineering ReSono base image with controlled removal and recovery. Slice 10 finalizes signing, complete removal, updates, reset, and release packaging after all replacements exist.
- **Counterexample:** The engineering image cannot boot/recover, or the final product is developed only on an image composition different from release.
- **Dependents:** OS inventory, HOME, runtime, signing, recovery, release.
- **Result:** `CONDITIONAL` on physical evidence.

### P-MDG-04 — Contracts and structure

- **Question:** Define every future schema first or add versioned contracts only with the first real producer and consumer?
- **Authority/evidence:** OD-01–OD-03; protocol requirement that phases prove real outcomes.
- **Alternatives:** Schema-first foundation; undocumented ad hoc messages; contract with its first real vertical path.
- **Selection/function:** Each cross-process contract is introduced in the slice where both real sides use it. A contract fixture cannot count as product evidence.
- **Counterexample:** A canonical event schema exists but the APK/runtime do not exchange it.
- **Dependents:** Runtime control, sessions, providers, MCP, A2A, External AI.
- **Result:** `CONTINUE`.

### P-MDG-05 — Personal-data domains

- **Question:** Implement Mail only, implement all domains at once, or prove the shared boundary with Mail and then complete the other three before release?
- **Authority/evidence:** OD-25; success scenario 17; F-02, F-16.
- **Alternatives:** Mail-only release; one oversized four-domain change; sequential domains on one shared contract.
- **Selection/function:** Mail proves local client, connector, storage, UI, permissions, and Agent Plugin behavior. Calendar, Contacts, and Reminders follow independently through the same public boundary and remain release requirements.
- **Counterexample:** The project calls the community release complete with any of the four domains absent, or builds four separate plugin systems.
- **Dependents:** Slices 6–7, SQLite, web/native UI, extension contract, final release.
- **Result:** `CONTINUE`.

## Delivery slice 1 — Reproduce the physical R1 and APK baseline

**Scenario and owner:** A contributor can build the existing ReSono HOME APK from this standalone repository, install it on the unchanged supported R1 base, and measure the real starting behavior without modifying a donor or claiming standalone operation. Implementation owner: unassigned. Acceptance owner: project owner.

**Entry conditions and dependencies:** Corrected grounding/plan accepted; current device and recovery access available; read-only U-07 capture succeeds; exact donor Android import record approved.

**In scope / out of scope:** Capture current partitions, slots, packages, HOME, signing, grants, recovery, and hardware state; copy the coherent donor Android project and build scripts; reproduce build/install; run the existing hardware/UI/Voice regression surface. No runtime port, feature redesign, package removal, or standalone claim.

**Deliverables:** Frozen current-device/image manifest; copied standalone `android/`; one build command; one install command; physical baseline matrix; rollback/recovery procedure.

**Positive and negative tests:** Clean APK build; package/HOME/signing/rollback capture; physical owner assessment of the existing installed behavior. A redundant replacement install is not required to establish the imported baseline. The known camera failure is recorded and deferred without being called passing.

**Evidence and external approval:** Artifact hashes, import record, build/install transcript, device capture, physical owner confirmation.

**Stop condition and rollback/reversal:** Stop on unavailable recovery, unidentified installed base, signing ambiguity, or hardware regression. Restore the captured base; donors are never changed.

**Exit condition:** The existing APK is reproducibly owned by this repository and its actual physical starting behavior is known, including any recorded defects. **Met 2026-08-14; camera is the one known deferred defect.**

## Delivery slice 2 — Early clean ReSono system image

**Scenario and owner:** The R1 boots through a recoverable engineering image directly into the real ReSono HOME, exposes no normal Cipher product UI, and retains required hardware and Android services. Implementation owner: unassigned. Acceptance owner: project owner.

**Entry conditions and dependencies:** Slice 1 accepted; exact Cipher/Rabbit partition/package inventory; recovery image and flashing procedure proven; each removal classified `KEEP`, `REPLACE`, or `REMOVE`.

**In scope / out of scope:** Preserve boot/vendor/hardware foundation; replace visible HOME/boot/product surfaces; remove optional Cipher packages in controlled groups; retain required providers, PermissionController, NetworkStack, framework services, and an engineering recovery path. No driver/HAL rewrite, irreversible removal, final production signing, updater, or fake replacement UI.

**Deliverables:** Reproducible engineering ReSono image manifest/tooling; embedded real HOME APK; package classification; staged removal logs; recovery procedure.

**Positive and negative tests:** Cold boot, reboot, HOME, settings adapters available, factory-reset behavior understood, all slice-1 hardware tests, missing-service detection, failed flash recovery, and verification that removed Cipher UI/apps are not normally reachable.

**Evidence and external approval:** Partition hashes, build/flash transcript, package inventory before/after, physical hardware matrix, owner acceptance.

**Stop condition and rollback/reversal:** Stop on boot, recovery, signing, permission, setup, motor, or hardware regression. Reflash the exact slice-1 baseline.

**Exit condition:** A clean, reversible engineering ReSono OS baseline exists for all later development. It is not yet the community release image. **Met and owner accepted 2026-08-14 after the reference enrollment overlay was removed.**

## Delivery slice 3 — On-device runtime lifecycle and management connection

**Scenario and owner:** The engineering R1 boots one supervised local runtime, persists a real SQLite record, serves an authenticated local health/event boundary, pairs a browser, and recovers after a forced failure. Implementation owner: unassigned. Acceptance owner: project owner.

**Entry conditions and dependencies:** Slices 1–2 accepted; U-02 packaging proof environment available; exact runtime donor import record.

**In scope / out of scope:** Minimal runtime package, SQLite, identity/credential boundary, local API/events, browser pairing, health, logs, restart, last-known-good rollback. No provider, memory agent, plugin, Hermes, or External AI feature facade.

**Deliverables:** Real runtime package and supervisor; first migration; authenticated health/event contract used by APK and real management status page; install/run/recovery protocol.

**Positive and negative tests:** Boot startup, persistence, paired access, process kill/recovery, corrupt update rollback, wrong token/origin/CSRF denial, unavailable database failure, unpaired browser denial.

**Evidence and external approval:** Physical logs, stored record, APK/runtime event exchange, paired browser result, recovery transcript.

**Stop condition and rollback/reversal:** Restore the last working runtime and retain the slice-2 image.

**Exit condition:** The R1 has a stable self-contained execution/storage base with no external Vault dependency for lifecycle management.

**Current evidence:** Build Contract 04 Checkpoints 1–5 pass with 14 runtime tests plus Android build/boundary/package verification. On the physical R1, installed version 9 proves embedded interpreter/import health, SQLite persistence, authenticated loopback readiness, Keystore HTTPS, USB-forwarded one-time pairing/status/restart and denials, isolated process-kill recovery, and recovery from a deliberately truncated active-release pointer. Direct same-LAN testing from `192.168.1.170` to the R1 at `192.168.1.196:8443` then proved the native displayed address, HTTPS page, unpaired denial, one-time pairing, authenticated ready status, and consumed-code denial without ADB forwarding. Cellular remained active and unadvertised. The exact installed APK is `artifacts/android-candidates/ReSonoR1-runtime-v0.3.4-rollback-fix.apk`, SHA-256 `183c2932d706bc84813b9f569039f0f160b84f4ec5755efe74e645ade193dac5`. Technical exit evidence and owner acceptance pass.

## Delivery slice 4 — Working OpenAI text and Realtime Voice

**Scenario and owner:** A user connects either ChatGPT/Codex subscription or OpenAI Platform access, selects runtime-reported text and Realtime models, completes a real Agents SDK text turn and real native R1 Voice session, and sees truthful state. Implementation owner: unassigned. Acceptance owner: project owner.

**Entry conditions and dependencies:** Slice 3 accepted; exact provider/subscription/Voice donor imports; OpenAI test access; U-01 validation path.

**In scope / out of scope:** Device-code OAuth, encrypted token storage/refresh/disconnect, Platform credential path, provider capabilities, model selection, one Agents SDK factory/runner, shared permission-filtered MCP tools/context, native WebRTC, canonical live events, real web/native setup and session controls. No additional providers or custom agent loop.

**Deliverables:** Real provider adapters; Agents SDK text path; native Voice path; real model selector and setup UI; shared MCP tool path; credentials and session tests.

**Positive and negative tests:** Both auth paths; text and required Realtime sessions; runtime-reported models only; text/Voice use the same granted MCP tool and deny an ungranted tool; expiration, revocation, unsupported model, interrupted media, provider denial, and disconnect fail truthfully.

**Evidence and external approval:** Physical session capture, redacted provider identifiers, SDK trace, UI tied to live events, owner acceptance of U-01.

**Stop condition and rollback/reversal:** Disable only the failing access path; never silently substitute Platform access for unproved subscription Realtime.

**Exit condition:** Grounding scenarios 2–7 and 14 pass on the R1.

## Delivery slice 5 — Sessions, memory, and Agents SDK review

**Scenario and owner:** A real completed Voice session is stored locally, reviewed through the single Agents SDK runner, and produces provenance-linked memory that can be retrieved and deleted correctly. Implementation owner: unassigned. Acceptance owner: project owner.

**Entry conditions and dependencies:** Slice 4 accepted; bounded U-04 vector choice proven.

**In scope / out of scope:** Session/transcript persistence, summaries, review agent, relational/lexical/vector retrieval, provenance, deletion, reindex, retries. No separate ChatGPT memory store, hash fallback presented as semantic search, or wholesale Vault memory port.

**Deliverables:** SQLite repositories/migrations; Agents SDK reviewer; embedding/index adapter; memory API and real inspection/deletion UI.

**Positive and negative tests:** Transcript-to-memory provenance, retrieval, idempotent finalization, deletion/index cleanup, unavailable embeddings, malformed extraction, cross-user denial, stale-index recovery.

**Evidence and external approval:** Real session trace and retrieval/deletion proof.

**Stop condition and rollback/reversal:** Disable semantic ranking and restore the prior runtime/schema without claiming degraded fallback as success.

**Exit condition:** Grounding scenario 8 passes.

**Status (2026-08-19):** Build Contract 06 is now implemented through transcript capture and session-finalize wiring for Voice (server-minted session ids + `/v1/voice/sessions/finalize`), reviewed through one Agents SDK memory-review runner, and persisted through canonical SQLite session/memory schemas. Provider embeddings are real `text-embedding-3-small`, cosine retrieval runs over stored vectors, and management inspection/finalization/search/delete/reindex routes are live. The `memory_lookup` Realtime function tool is wired to the Voice path only (not the text runner), and startup memory context is injected at voice session creation. Offline tests now include a dedicated finalize-endpoint regression (`tests/runtime/test_runtime_http_finalize.py`) and `tests/runtime/test_memory_sessions.py` (30 tests total). The next open physical gate remains owner validation of credential-backed memory review + retrieval; the latest offline candidate in this workspace remains the tracked rollback candidate. 

## Delivery slice 6 — Standard extensions and real Mail

**Scenario and owner:** A user creates or installs standard Skills and Plugins, connects a real email account to the local Mail client, grants limited agent access, uses Mail through a real agent flow, and rolls back a failed editable change. Implementation owner: unassigned. Acceptance owner: project owner.

**Entry conditions and dependencies:** Slices 4–5 accepted; Agent Skills and Agent Plugins specifications frozen; exact Mail donor import.

**In scope / out of scope:** Standard validation/install/enable/disable/remove; one shared CLI/web lifecycle; permission intersection; trusted/user separation; editable agents/prompts/config; local Mail store/client and IMAP/SMTP connector; Mail Agent Plugin; quarantine/recovery. No ReSono package format, marketplace, unrestricted shell, or trusted-core browser editing.

**Deliverables:** Standard loaders/validators; editable workspace; real Mail client/connector/plugin; real creation and management UI; logs and rollback.

**Positive and negative tests:** Valid Skill-only, MCP-only, and combined packages; missing optional components accepted; real sync/read/approved action; disabling plugin preserves Mail data; excessive permissions, traversal, embedded secret, malformed component, or failed activation denied/quarantined before protected use.

**Evidence and external approval:** Standards validation, real mail flow, permission trace, removal and rollback proof.

**Stop condition and rollback/reversal:** Quarantine the package and restore the last plugin/runtime registry.

**Exit condition:** Grounding scenarios 9, 10, and 12 pass through one public extension boundary.

## Delivery slice 7 — Calendar, Contacts, and Reminders

**Scenario and owner:** A user manages real local Calendar, Contacts, and Reminders data, connects supported external accounts where applicable, and grants agents only the standard plugin capabilities explicitly approved. Implementation owner: unassigned. Acceptance owner: project owner.

**Entry conditions and dependencies:** Slice 6 accepted; exact donor imports per domain; the Mail-proven storage/connector/plugin boundary remains adequate.

**In scope / out of scope:** Local Calendar, Contacts, Reminders clients/domains; ICS/CalDAV and applicable contact sync connectors; local reminder scheduling/delivery; standard first-party agent plugins; real web/native UI. No separate plugin framework or every Vault personal-data feature.

**Deliverables:** Domain repositories/migrations; connectors; first-party plugins/skills/MCP tools; working management and R1 surfaces.

**Positive and negative tests:** Create/read/update/delete and sync for supported flows; offline behavior; duplicate/conflict handling; permission denial; disabling agent access preserves local data; cross-domain and cross-account isolation.

**Evidence and external approval:** Real local and connected-domain traces, permission and data-preservation proof, owner usability acceptance.

**Stop condition and rollback/reversal:** Disable the affected connector/plugin and restore prior domain migration/runtime while preserving recoverable user data.

**Exit condition:** Grounding scenario 17 passes; no accepted personal-data domain remains merely documented.

## Delivery slice 8 — Hermes A2A and unified product experience

**Scenario and owner:** During a real Voice session, the user delegates to one configured Hermes A2A peer, sees real task state, handles clarification/cancellation, and receives the result through the same polished New Browser Voice experience on web and R1. Implementation owner: unassigned. Acceptance owner: project owner and Hermes operator.

**Entry conditions and dependencies:** Slices 4 and 6 accepted; configured Hermes and strict A2A interoperability proof; every existing UI already uses real behavior.

**In scope / out of scope:** One Hermes connection; Agent Card; required A2A version/message/stream/task/cancel behavior; Voice function/output; normalized state; completion of coherent web/native navigation, tokens, icons, accessibility, wheel/touch/button behavior. No OpenClaw implementation, general router, late replacement UI, or mock state.

**Deliverables:** Standards-compliant A2A client; Hermes settings; real Voice integration; hardened web/native design components and tests.

**Positive and negative tests:** Real discovery/delegation/clarification/cancel/result; incompatible version, invalid card, denied token, disconnect, timeout, malformed result, and loop attempt; equivalent real state across web/native; accessibility and physical input.

**Evidence and external approval:** Real Agent Card/task IDs/stream, physical R1 interaction evidence, owner and Hermes-operator acceptance.

**Stop condition and rollback/reversal:** Disable Hermes and its grants; local Voice continues. Revert affected UI without changing runtime data.

**Exit condition:** Grounding scenarios 11 and 16 pass without proprietary Hermes behavior.

## Delivery slice 9 — External AI HTTPS MCP and ChatGPT

**Scenario and owner:** A user configures a public HTTPS MCP deployment, connects ChatGPT through MCP OAuth, retrieves a real Voice-created outbox item, and explicitly saves selected ChatGPT context into canonical R1 memory. Implementation owner: unassigned. Acceptance owner: project owner and public-service operator.

**Entry conditions and dependencies:** Slices 3, 5, 6, and 8 accepted; exact External AI/outbox/tunnel donor imports; ChatGPT test access; hosted exit additionally requires U-06.

**In scope / out of scope:** Provider-neutral local outbox and per-connection delivery; local MCP authorization; outbound device bridge; self-hostable `external-ai-gateway/`; MCP OAuth; `connectors/chatgpt/`; configurable URLs and permissions; explicit memory capture/search. No subscription auth/media in gateway, second outbox/vector store, other client, Link, or hosted management.

**Deliverables:** Real local services/migrations; HTTPS Streamable HTTP MCP/OAuth gateway; ChatGPT package; real configuration UI; hosted/self-host protocols.

**Positive and negative tests:** Real OAuth/MCP/list/call/ack/capture/retrieval; per-connection isolation; revoked scope, wrong resource/device, replay, duplicate, offline R1, timeout, oversized payload, restart, and endpoint change.

**Evidence and external approval:** Public metadata, real ChatGPT results, R1 provenance/vector proof, clean self-host transcript.

**Stop condition and rollback/reversal:** Revoke/disconnect External AI and restore prior runtime/gateway; local product continues.

**Exit condition:** Grounding scenarios 13 and 15 pass; public service holds no canonical personal data.

## Delivery slice 10 — Final system image and community release

**Scenario and owner:** A community user installs, updates, resets, and recovers one signed ReSono package/image that boots directly into the complete product, retains required R1 hardware, and exposes no Cipher product UI. Implementation owner: unassigned. Acceptance owner: project owner.

**Entry conditions and dependencies:** Slices 1–9 accepted; U-03 final package removal proven; signing/recovery access; formal non-commercial license text and third-party notices; release operator.

**In scope / out of scope:** Final package removal; removal/replacement of the visible Cipher pull-down shade, app drawer, Launcher/Quickstep presentation, Settings UI, setup/product UI, themes/updater, and remaining user-facing applications; retention or replacement of only required invisible Android contracts; ReSono local first-run/settings behavior without hosted enrollment; APK/runtime embedding, signing, update, rollback, reset, source/release documentation, and full physical regression. No driver/HAL rewrite or extra feature.

**Deliverables:** Reproducible signed image/package; artifact hashes; install/update/reset/recovery protocols; source provenance/license record; full acceptance report.

**Positive and negative tests:** Clean install and upgrade; boot; factory reset; failed update rollback; removed Cipher surfaces remain absent; all hardware; all grounding scenarios 1–17; clean contributor build where redistribution permits.

**Evidence and external approval:** Reproducible build log, hashes, complete physical matrix, end-to-end report, license approval, owner release acceptance.

**Stop condition and rollback/reversal:** Restore the known-good engineering image on any hardware, recovery, signing, rights, or product-flow failure.

**Exit condition:** The owner accepts the actual community release. Structural tests alone cannot satisfy this slice.

## Requirement traceability

| Grounding success | Primary slice | Required evidence |
|---|---:|---|
| 1 — Boot and hardware | 1, 2, 10 | Physical baseline and release hardware matrices |
| 2 — Pair and setup | 3, 4, 8 | Real paired flow and usability proof |
| 3 — Subscription or Platform credential | 4 | Real connect/refresh/disconnect |
| 4 — Text/Realtime model choice | 4 | Runtime-reported selection and denial |
| 5 — Realtime Voice | 4 | Physical R1 sessions on required access paths |
| 6 — Agents SDK text | 4 | SDK trace and real result |
| 7 — Truthful live state | 4, 8 | Event-to-real-renderer proof |
| 8 — Session memory | 5 | Transcript-to-memory provenance/retrieval |
| 9 — Agent Skill | 6 | Standard create/install/use/remove |
| 10 — Agent Plugin | 6 | Standard lifecycle and permission proof |
| 11 — Hermes A2A | 8 | Real discovery/task/stream/result |
| 12 — Editable recovery | 3, 6 | Failed activation and last-known-good rollback |
| 13 — External AI outbox/capture | 9 | Voice-to-ChatGPT-to-memory result |
| 14 — Subscription device OAuth | 4 | Device-code polling/storage/refresh/disconnect |
| 15 — Public HTTPS MCP | 9 | Hosted and self-host OAuth/MCP proof |
| 16 — Shared visual product | 4, 6–9 | Real web/native state and physical UI evidence |
| 17 — Mail/Calendar/Contacts/Reminders | 6–7 | Real local/connected domains and plugin permissions |

## Open gates and stops

| Gate | Blocks | Resolver |
|---|---|---|
| Corrected grounding/plan acceptance | All implementation | Phase 02 review and project owner |
| U-07 current device/recovery evidence | Resolved for Slices 1–2 | Same-device read-only capture, rollback APK, restore/fastboot evidence, and project owner |
| U-02 runtime packaging | Slice 3 and later runtime work | Physical packaging proof |
| U-01 subscription Realtime | Slice 4 exit | Real R1 provider proof |
| U-04 vector choice | Slice 5 | Bounded local candidate proof |
| Frozen extension standards | Slice 6 | Current specifications and conformance evidence |
| Hermes strict A2A interoperability | Slice 8 | Configured Hermes plus independent protocol proof |
| U-06 public hostname/operator | Slice 9 hosted exit | Project owner/operator |
| U-03 final removable packages | Slice 10 | Controlled image tests |
| Formal non-commercial license text/notices/operator | Slice 10 | Project owner and release operator |

## Failure criteria

Return `BLOCKED/REOPEN` if any accepted feature disappears, a supporting reference becomes a second authority, the existing APK is replaced without donor evidence, OS removal precedes recovery/replacement proof, a phase exits on structural evidence alone, a UI is disconnected, a standard is replaced, or donor/external files are modified.

## Next authorized action

Continue only `R1-BUILD-CONTRACT-05-v0.1`. Physical version 26 proves persisted subscription authorization, GPT-5.6 Sol Agents SDK text, local MCP device status, reasoning selection, personalized greeting, and Realtime 2.1 Mini live WebRTC. Its exact APK remains the immutable working base. Installed version 28 additionally proves the primary Voice device's exact Realtime/VAD profile, native Voice MCP invocation and tool-backed response, brightness controls, foreground runtime/management availability, and no timeout dimming while ReSono is visible. Owner has confirmed Platform text and Platform Realtime are working in this environment; key field and Keystore-backed storage remain implemented for continuity.

The most recent execution pass did a clean build, install, and TLS identity verification pass.

The next executable checkpoints are:
1. normal-browser TLS trust (runtime certificate identity now uses active local LAN host/IP; rebuild/deploy validation pass required).
2. Move to Slice 5 (sessions + memory + Agents SDK review) after confirming normal-browser TLS trust remains stable in this environment.
3. `gpt-live-1` remains owner-deferred and is explicitly out of this contract slice until explicitly re-opened.

Now advance to Slice 5 (sessions + memory + Agents SDK review) while keeping all other slices closed. Preserve version 9 as runtime rollback and version 26 as the accepted working product base; version 28 is the current installed candidate. TLS trust is owner-closed and no longer gates progression.

The immediate next execution step is: complete the physical credential-backed memory review + retrieval proof for Build Contract 06 (record a candidate APK with redacted identifiers), then proceed to Slice 6. `gpt-live-1` remains owner-deferred and does not gate progression.
