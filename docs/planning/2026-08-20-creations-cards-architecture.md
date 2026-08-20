# R1 Creations and Cards Architecture

**Date:** 2026-08-20  
**Status:** Static import/catalog/Cards code implemented; physical acceptance open. Privileged SDK globals remain outside the static compatibility boundary recorded in Build Contract 07.  
**Governing contract:** `2026-08-20-build-contract-07-extensions-mail.md`, Subphase `07F`.

## Decision

Imported Creations are rendered on the native R1 Cards page. The Cards page is an R1-owned, trusted HTML/CSS/vanilla-JavaScript shell. It renders a dynamic catalog-backed card deck, not imported Creation code. Selecting a Creation card opens the selected artifact in a separate, restricted Creation WebView host.

This separation is required:

```text
Creation Catalog API
        |
        v
R1-owned Cards shell (trusted HTML/CSS/JS)
        |
        | select enabled Creation card
        v
CreationWebViewHost (one selected imported artifact)
        |
        v
R1 compatibility bridge and scoped Creation data
```

An imported artifact never renders inside the Cards deck itself, never controls the deck state, and never receives the management bearer token. The deck remains responsive even when a Creation fails or is removed.

## Current-code finding

Current native navigation is `ProductRootView` with only `VoicePageView` and `SettingsPanelView`. `VoicePageView` draws a non-interactive `Cards` label but has no Cards state, WebView, HTML host, selection logic, or Creation runtime. Therefore HTML cannot be added to an existing Cards page. Build 7 must add a real Cards sibling feature and change `ProductRootView` to own the Voice/Cards page switch.

## Required R1 Cards UX

The owner-provided Cards reference is the intended production interaction and visual direction:

- A dark blue-black shell with restrained borders and pale text.
- Voice and Cards are peer tabs; Cards has the active aqua underline.
- One front card, followed by up to two visible depth cards, forms a compact rolodex deck.
- Each card has an independent accent: aqua `#79f2dd`, yellow `#ffd166`, purple `#c792ff`, red `#ff6b6b`; the rest of the system remains restrained.
- Accent drives only the card stripe, eyebrow, state marker, and selected indicator.
- Card navigation uses upward/downward swipes, wheel events, physical directional input, and previous/next controls through one `move(direction)` state transition.
- The active card follows a finger during a pointer drag; release uses distance or velocity to commit/cancel. CSS transforms, opacity, and perspective animate transitions. The page does not scroll, select text, or permit browser zoom gestures.
- The Cards shell uses a circular catalog index and CSS depth attributes (`active`, `depth-1`, `depth-2`, `hidden`), rather than multiple conflicting navigation states.

The R1-owned Cards shell is a small static bundle:

```text
web/cards/
  index.html
  css/theme.css
  css/cards.css
  js/catalog.js
  js/deck.js
  js/gestures.js
  js/hardware.js
```

`catalog.js` receives only support-safe card projections. `deck.js` owns index/depth state. `gestures.js` converts Pointer Events to deck movement. `hardware.js` converts the native forwarded R1 input events to the same deck movement. JavaScript owns state; CSS owns presentation and animation. This is a real final-subphase product surface, not a preliminary placeholder.

The Cards shell uses the actual R1 page canvas established by the native product UI. A selected legacy Creation runs in its own compatibility viewport; the exact `240x282` creation content viewport is retained only where the imported Creation requires it and is physically scaled/verified within the R1 Cards host. Do not silently stretch or crop a Creation and call it compatible.

## Dynamic catalog and rendering flow

```text
Management import
  -> Creation Catalog stages and validates immutable revision
  -> enable atomically changes active revision and catalog generation
  -> native Cards catalog client sees changed generation
  -> R1-owned Cards shell re-renders card metadata and deck state
  -> user selects Creation card
  -> native CreationWebViewHost loads only that active artifact
```

Import, enable, update, disable, and delete do not require a device reboot. On deletion or active-revision change, the host stops sensor/input delivery, clears the bridge, destroys the old Creation WebView, and returns to the catalog/deck. If live update cannot be safely applied on a target runtime, the catalog reports `restartRequired: true` before activation. An APK/native implementation change remains a normal package update and restart.

## Required Creation SDK compatibility bridge

The read-only Rabbit Creations SDK revision `62ef8b37de9c8ec74499987eeed1f07b9cfaaaf0` is MIT licensed and exposes browser globals rather than a package standard. Build 7 supports all demonstrated globals, but maps each to a narrow named owner:

| SDK global/event | R1 owner and required behavior | Boundary |
|---|---|---|
| `PluginMessageHandler.postMessage` | `CreationMessageBridge` parses bounded JSON with `message`, `useLLM`, `wantsR1Response`, and `wantsJournalEntry`; it uses the one existing OpenAI Agents SDK execution path with a Creation-scoped, no-personal-data tool projection. Response arrives at `window.onPluginMessage`. | No direct credential, Mail, Memory, MCP, Skill, or raw runtime access. Per-Creation rate/token/output limits and user-visible failure results are mandatory. |
| `window.onPluginMessage` | `CreationResponseBridge` delivers a bounded object containing the R1-generated `pluginId`, `message`, and optional `data`. | Imported code cannot spoof another Creation ID or inject a response into a different host. |
| `wantsR1Response` | `CreationResponseSpeaker` speaks only the response produced for that same Creation request through the R1 speaker. | No arbitrary TTS bridge; no concurrent Voice/Creation speaker collision; audio focus and stop/teardown are owned by Android. |
| `wantsJournalEntry` | `CreationJournal` writes an explicitly requested, provenance-marked Creation interaction record. | It is not silently promoted to Voice memory or exposed to the Voice agent until a separate memory policy grants that behavior. |
| `closeWebView.postMessage` | `CreationWebViewHost.closeSelected()` returns to the Cards deck. | It closes only the current Creation; it cannot exit HOME or control Android navigation. |
| `TouchEventHandler.postMessage` | `CreationTouchRelay` validates bounded coordinates and dispatches only within the active Creation viewport. | No OS-wide input injection, settings navigation, Voice control, or touch outside the Creation bounds. |
| `window.creationStorage.plain` | `CreationStorageRepository` stores base64 input under the current `creationId` namespace. | Enforced key/value/count/size quota; no cross-Creation reads. |
| `window.creationStorage.secure` | `CreationSecureStorage` uses a Creation-scoped Android Keystore ciphertext envelope. | Plaintext is never returned to management APIs, logs, package files, or another Creation. |
| `window.creationSensors.accelerometer` | `CreationSensorRelay` owns Android SensorManager subscription, availability, bounded frequency, and callback delivery. | Only active foreground Creation receives samples; subscription stops on blur/close/delete. |
| `scrollUp`, `scrollDown`, `sideClick`, `longPressStart`, `longPressEnd` | `CreationInputRelay` turns the active Cards-owned hardware input into DOM events for the active Creation. | Input is not shared with Voice and does not escape the active Creation focus. |

The compatibility bridge is available only in the selected Creation WebView. The trusted Cards shell itself does not receive these globals. The bridge is injected only after the native host verifies the exact active local asset origin; external navigation, file/content access, mixed content, service workers, and arbitrary JavaScript interfaces are disabled.

## Final-subphase implementation order

1. Add Creation Catalog records, immutable artifact storage, archive validation, enable/disable/delete, and native Cards projection.
2. Add `:feature:cards`, change `ProductRootView` to real Voice/Cards navigation, and implement the R1-owned deck shell against live catalog data.
3. Add `CreationWebViewHost` with dynamic catalog-generation reload and static Creation rendering.
4. Add every SDK bridge owner above, one capability at a time, with exact scoped failure behavior.
5. Add the web Creation Catalog only after native import/render/delete works. Its functions are import, inspect, enable, disable, and delete; it never embeds a Creation.
6. Run the single final Build 7 acceptance pass, including no-reboot lifecycle proof, card deck input/motion evidence, Creation bridge isolation, delete cleanup, and the exact SDK compatibility fixture.

## Acceptance failures

- A Cards page that draws static example cards rather than catalog-backed real Creation entries fails.
- An imported Creation that needs a reboot when its catalog generation can reload fails.
- Any Creation global that exposes Android context, raw network, local files, credentials, Mail, Memory, MCP, or another Creation fails.
- A `PluginMessageHandler` request that starts a second agent loop or inherits personal-data tools fails.
- A Creation can inject input outside its own viewport, keep a sensor active after close, or receive hardware input while Voice owns focus fails.
- A web Creation Catalog that embeds/runs Creation code fails.
- A visual implementation that drops the specified dark rolodex, accent system, depth transition, or unified finger/wheel navigation without owner approval fails.
