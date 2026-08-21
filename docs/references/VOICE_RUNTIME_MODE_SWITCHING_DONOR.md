# Voice Runtime Mode Switching Donor Reference

**Identity:** `R1-VOICE-MODE-SWITCH-DONOR-REFERENCE-v1.0`  
**Date:** 2026-08-21  
**Status:** Verified donor reference; R1 adaptation is implemented as an unvalidated candidate and physical acceptance remains open  
**Controls:** `GROUNDING-BASELINE-v0.5`, Build Contract 08, absolute donor read-only boundary

## Decision and limits

Build 08 needs one live Voice connection to enter a specialized Goal Intake
interview, submit a typed background goal, and return to Primary Voice. The
current R1 native Java WebRTC path does not run an Agents SDK
`RealtimeSession`, so SDK Realtime Handoff is unavailable without replacing or
substantially bridging the accepted transport.

The donor proves a smaller same-session mechanism that replaces both active
instructions and provider-visible tools. It is not a UI label, prompt-only
convention, second session, or simulated specialist. R1 will adapt this pattern
for `primary` and `goal_intake` modes. A clear delegation request may trigger
Goal Intake semantically; the user need not know the word “mode.”

Counterexample: if R1 changes only a label or prompt, leaves old tools callable,
or opens another Voice session, the adaptation fails. **Material Decision Gate:
`CONTINUE` was accepted. Candidate implementation exists; automated and physical
acceptance remain open.**

## Provenance

Read-only donor:
`/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace`

Revision: `0f3b34223f745920e79d1d9db301f3b639d08393`  
Branch ref: `refs/heads/recovery/restart-from-production`

No donor file was modified or copied.

| Source | SHA-256 | Responsibility |
|---|---|---|
| `app/contracts/internal/runtime_modes.py` | `be259a9be824506044eb3b5c887d4e9668b2cf9f2c405d2f9d2ba0093a3f4e4d` | modes, trusted instructions, validation, tool schema |
| `app/modules/runtime_modes/service.py` | record before copying | enablement, prompt resolution, non-sticky startup |
| `app/modules/inference_runtime/realtime_session_builder.py` | `6486ab16333608436aefac59940a200dde2d7f1d0d3772953b0f81703bbfd4b4` | complete target instruction/tool projection |
| `app/modules/voice_realtime/cloud_tool_coordination.py` | `3d0b897d2e31f9abacb50699429610124e6e892c6b7cde42956e850c8a8151ec` | validation, atomic state, safe update projection |
| `app/modules/voice_realtime/handlers/assistant.py` | `85826d9fa144d5a3e61a47096493bed311a6f183f429a54caa8f0ccbc0d6e624` | browser/Vault update response |
| `app/modules/voice_realtime/realtime_proxy_service.py` | `88da7414fe7e4952b6c13ca58545eba6b54d190561051659c4f40b0b74eafe83` | browser proxy execution and replay |
| `app/modules/device_runtime/realtime_proxy_service.py` | `5db51370b4a2437eccc77750d051b7688585203c066ce1578d75ef6923cc1882` | device proxy forwarding |
| `frontend/src/browser-voice/api.ts` | record before copying | typed update/result contracts |
| `frontend/src/browser-voice/useBrowserVoiceToolBridge.test.tsx` | record before copying | send order and fail-closed client evidence |
| `tests/unit/test_runtime_modes_contract.py` | `8887109dcbac7dcd7c82eacf2611aa1a62e7d3bc6379a29e25ba5e6f11c014c0` | trusted mode contract tests |
| `tests/unit/test_realtime_session_builder.py` | `549ecba70a276545ee409074a02e76c99937a3d18cf22e97a3cef0fe1a03c09f` | per-mode tool projection tests |
| `tests/integration/test_voice_realtime_service.py` | `cc5bb93116661a5c1f7ff371f5a45e5064787abb8f7bd0cfdcc58eb320ae5bb2` | atomic update and idempotency tests |

Entries marked “record before copying” prohibit copying until their exact hash,
source, destination, retained/omitted behavior, license decision, and tests are
added to `DONOR_CODE_REFERENCE_MAP.md`.

## Ownership model

```text
runtime_modes contract
  -> mode keys, descriptions, trusted prompts, mode_switch schema
RuntimeModesService
  -> account enablement and prompt policy
RealtimeSessionBuilder
  -> complete effective instructions and tool catalog
local tool coordinator
  -> validates and atomically commits currentModeKey
browser/device Realtime proxy
  -> rebuilds and sends provider session.update
Vault descriptor path (donor only)
  -> synchronizes private tool routing before provider activation
```

The UI does not decide capability membership. Provider transport does not own
policy. One canonical builder owns the effective profile.

## Mode contract

The donor declares `assistant`, `business`, `presentation`, and `build`. Each
has a label, description, and distinct instruction block. Build is trusted and
cannot be replaced by account-authored prompt configuration.

The function contract is `mode_switch` -> `mode.switch`, with one required
`modeKey` enum and `additionalProperties: false`. The donor description permits
switching only when explicitly requested. R1 must intentionally replace that
activation policy so Primary may switch when it semantically recognizes a clear
background-delegation request. Ambiguous intent is clarified before switching.

## Startup state and lifetime

`RuntimeModesService.get_mode_state()` checks account enablement but always
starts a new session in Assistant. Its implementation explicitly prohibits a
specialist mode becoming sticky across sessions.

The open session retains `currentModeKey`, `modeSwitchingEnabled`, modalities,
voice, timezone, provider/model/connection identity, and actor/auth context.
Mode is live-session state, not a durable personality/default change.

## Canonical rebuild

`RealtimeSessionBuilder.build_workspace_request()` reconstructs the target
request from authoritative sources. Depending on mode, it composes base
instructions, runtime guidance, account/time context, mode instructions,
Signals, delegation guidance, Agent Hub guidance, memory, learning, and the
complete target tool catalog.

| Capability | Assistant | Business | Presentation | Build |
|---|---:|---:|---:|---:|
| mode switch | yes | yes | yes | yes |
| Mail | yes | yes | no | no |
| Calendar | yes | yes | no | no |
| Contacts | yes | yes | yes | no |
| search/fetch | yes | yes | yes | no |
| memory lookup when enabled | yes | yes | yes | no |
| workspace package | no | yes | yes | no |
| document editor | no | yes | yes | no |
| presentation controls | no | limited | full in Browser Voice | no |
| general delegation | yes | yes | yes | no |
| Agent Foundry specialist tools | no | no | no | yes |

Build replaces the ordinary catalog with mode control plus its specialist
Foundry tools. It excludes active Signals, domain tools, general delegation,
memory guidance, direct search, and workspace tools. This proves a real
instruction-and-capability boundary.

## Complete live switch sequence

```text
1. Model emits mode_switch(modeKey).
2. Runtime resolves it from the current session tool index.
3. Host validates JSON and allowed key.
4. Host verifies mode enablement and live session ownership.
5. Host locks the session record.
6. Host commits currentModeKey atomically.
7. Host returns a deterministic completed tool result.
8. Host rebuilds the complete target RealtimeSessionRequest.
9. Provider adapter builds the ordinary session.update.
10. Mode projection retains only type, instructions, tools, tool_choice.
11. Missing tools becomes tools: [] so old tools cannot leak.
12. Proxy sends session.update on the existing provider connection.
13. Proxy sends function_call_output for the original provider call ID.
14. Response continues under the new rules and tools.
15. Client/runtime publishes activeModeKey only after the update path succeeds.
```

WebRTC, audio ownership, provider session, and conversation history remain
alive. Model, voice, VAD, audio formats, credentials, and transport are not
changed opportunistically.

## Send ordering and provider acknowledgement

Browser and device proxies serialize provider writes with a send lock. The
`session.update` is sent before the function-call output so continuation sees
the target profile. The donor's proxy startup path waits for
`session.updated`; timeout, provider error, or unexpected acknowledgement is an
explicit failure.

The explicit empty tools array is mandatory because omission preserves the old
provider tool set.

## Cloud, device, and Vault variants

Cloud/browser and device proxies share the coordinated execution and canonical
rebuild pattern. Vault additionally rebuilds an opaque runtime descriptor with
active mode, tool names/specs/descriptors, and private routing hints. The
browser must synchronize that descriptor before accepting the new provider
catalog. Descriptor rejection fails closed: no provider update and no local
active-mode change. Vault-only metadata is stripped from the provider payload.

Standalone R1 has no Vault dependency. Adapt atomic state, canonical rebuild,
mutable-field projection, serialized send, acknowledgement, replay, and
fail-closed behavior; omit Vault routing and cloud platform machinery.

## Idempotency and consistency

The provider call ID is mandatory. Replaying the same ID with equivalent
arguments returns duplicate-safe output. Reusing it with different arguments
is rejected. If database state committed but provider send failed, replay
rebuilds and resends the idempotent target update, closing the durable-state /
provider-state split window.

Ownership checks bind changes to the account, workspace, browser/device actor,
auth session, open Voice session, provider, and executable transport state.

## Failure behavior

The donor explicitly rejects malformed/non-object arguments, missing or
unsupported mode keys, disabled switching, missing/closed/foreign sessions,
unsupported transport/provider state, invalid updates, acknowledgement timeout
or provider error, conflicting call-ID reuse, unavailable tools, and Vault
descriptor rejection. Failures are tool errors, never false success.

For R1, failed goal submission must remain in Goal Intake and preserve the
interview. Failed provider update must not claim the target mode is active.

## Test evidence and its limit

Donor tests cover trusted Build instructions, allowed keys, mode-specific tool
membership, restricted Build tools, real `session.update`, returned active
mode, duplicate replay, conflicting replay rejection, descriptor fail-closed,
provider metadata stripping, and update/output sequencing. These tests prove
donor behavior only, not R1 implementation or physical acceptance.

## R1 Goal Intake contract

R1 uses `primary` and `goal_intake`:

- Primary owns ordinary conversation and authorized Voice tools.
- Goal Intake owns adaptive interview instructions, typed `goal_submit`, only
  strictly necessary goal clarification/status operations, and mode return.
- Goal Intake receives no Mail, Calendar, Tasks, workspace mutation, Web
  Search, or general tools unless a later explicit contract proves necessity.
- Entry occurs when Primary identifies clear delegation intent.
- Goal Intake preserves the original request verbatim and asks only questions
  that materially affect outcome, evidence, completion, authority, exclusions,
  sources, artifacts, or stop conditions.
- It avoids rigid field-by-field interviews, recaps the interpreted goal,
  submits once through the existing delegation port, and never runs the goal.
- It returns to Primary only after confirmed submission, explicit cancellation,
  or explicit exit. Failed submission or pending clarification stays in Goal
  Intake.
- Return restores the complete Primary profile on the same session. It does not
  wait for background completion.

## R1 ownership and acceptance

The Tool Catalog remains the executable registry; the audience router remains
the Voice eligibility filter; a focused Voice profile builder owns instruction
and tool projection; the existing provider/controller and native data-channel
owners send the update; the delegation port submits; `background_agent/`
executes. Do not copy donor modules wholesale or create a catch-all manager.

Required positive proof: ordinary requests stay Primary; clear delegation
switches once; WebRTC and history survive; instructions and tools both change;
Primary tools are absent in Goal Intake; one typed goal is submitted; success
returns to Primary; background execution survives Voice disconnect; new
sessions start Primary; replay is safe.

Required negative proof: label/prompt-only switching fails; empty target tools
clear prior tools; failed submission stays in intake; failed update is not
reported active; Goal Intake cannot call Primary tools; foreign sessions are
rejected; specialist state never persists.

The current R1 tree contains the candidate adaptation described above. This
reference does not claim a test, build, deployment, or physical pass.
