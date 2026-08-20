# R1 Direct Handoff Contract

**Identity:** `R1-DIRECT-HANDOFF-v0.1`
**Status:** Owner-directed design and implementation contract; implementation remains gated by the active build sequence and Camera gates C1-C4
**Authority:** Owner direction on 2026-08-20; `GROUNDING-BASELINE-v0.5` OD-03, OD-18, OD-22, OD-28, and the R1 Camera Recovery Contract

## Implementation record

The first non-visual foundation is implemented in the standalone repository:

- `runtime/resono_runtime/handoff/` owns bounded JPEG/PNG/WebP validation, session-bound storage, OpenAI Responses inspection through the selected Platform/subscription access path, grounded provider text, and inspection caching.
- `runtime/resono_runtime/api/handoff_routes.py` exposes the bearer-authenticated loopback host endpoint `/v1/host/direct-handoffs/inspect`.
- migration v26 owns the direct-handoff inspection records and cache index.
- `android/runtime-host/.../RuntimeHandoffClient.java` owns the native upload/inspection request.
- `android/feature/voice/.../VoiceSessionHandoff.java` is the narrow current-session port; `VoicePageView` remains the only Realtime event sender and response-in-flight owner.
- The response-in-flight flag is reset at both session start and stop so one session cannot suppress another session's response.

No visible control, Camera capture, or simulated image source has been added. The next connected implementation unit is the real Camera producer and review state that supplies this completed boundary.

The connected native flow is now implemented: `Hand to Voice` appears only while the current Voice session is available; it opens the full-screen motor-confirmed Camera page; capture freezes a real JPEG; capture alone sends nothing; review exposes `Send`, `Retake`, and `Cancel`; Send calls the authenticated runtime inspection endpoint and passes its grounded result to the existing Voice-owned Realtime boundary. Cancel, failure, and successful submission return the motor toward privacy and preserve the existing Voice owner.

## Product decision

Direct Handoff is an action on the current Voice conversation. It is not the Camera application and must not be represented by a camera icon.

The native Voice page receives one secondary action at its bottom edge:

```text
[ image-frame + inward arrow/wave icon ]  Hand to Voice
```

The production icon is a simple Browser Voice-style line icon combining an image frame with an inward arrow or short Voice waveform. A standalone camera glyph is reserved for camera capture, and a standalone hand glyph is rejected because it can read as accessibility, help, or gesture instruction. The visible label is always `Hand to Voice`; no icon-only release is permitted on the 480x640 device.

The full-screen Camera remains a separate root page reached by horizontal swipe. Direct Handoff never changes that navigation:

```text
Main root page                       Camera root page
  Voice tab                            full-screen preview
    Hand to Voice                      capture / Creation QR analysis
  Cards tab
```

## User flow

### From Voice

1. The action is enabled only while the real Voice state is `live` or `responding` and the Realtime data channel is open.
2. Tapping `Hand to Voice` moves directly to the existing full-screen Camera root page in explicit handoff-capture mode. There is no source-selection sheet, new Activity, or CipherOS dialog. The current Voice session continues uninterrupted.
3. Before capture, Camera shows its live preview and one clear shutter control. `Cancel` returns to Voice without storing or sending an image.
4. Pressing the shutter freezes the real captured frame for review. Nothing uploads, inspects, or enters Voice at capture time.
5. In review state, the shutter control becomes the primary `Send to Voice` action. `Retake` discards that frame and restores live preview; `Cancel` discards it, returns Camera to privacy, and returns to Voice. An optional note may accompany the image without obscuring the preview.
6. Only pressing `Send to Voice` stores the reviewed image through the runtime workspace boundary, requests the `direct_handoff` inspection profile, and shows `Reading image...` while that real request runs.
7. The inspection is injected into the same open Realtime conversation and the UI returns to Voice in `responding` state.
8. The assistant reviews the supplied image context aloud in that same session. Any consequential action still follows the owning tool's confirmation rules.

### Cancellation and failure

- `Cancel` discards the uncommitted capture, returns Camera to privacy, and returns to the same Voice session.
- A failed upload or inspection leaves Voice connected, retains the captured preview for retry, and reports a specific ReSono in-page error.
- If the Voice session closes before confirmation, sending is disabled and the sheet says `Voice session ended`. The image is not injected into another or later session.
- If the data channel closes after inspection but before injection, the operation fails visibly. It must not create a replacement Voice session automatically.
- A successful handoff clears the transient capture after runtime persistence and transcript metadata succeed according to the final runtime contract.

## Exact donor behavior retained

Read-only donor root:

`/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace`

| Concern | Exact donor source | Retained behavior |
|---|---|---|
| Browser orchestration | `frontend/src/browser-voice/BrowserVoiceApp.tsx`, especially `handleDirectHandoff()` | Require the active authenticated session, current Realtime session ID, and open current data channel; upload/inspect first; inject one user item; request one response; record transcript metadata. |
| Handoff text contract | `frontend/src/browser-voice/browserVoiceUtils.ts` | Session-scoped upload directory, safe filename, explicit statement that server inspection is visual context, original filename/file key, optional note, inspection markdown, and contact-confirmation warning. |
| Browser controls | `frontend/src/browser-voice/BrowserVoicePanels.tsx` | Optional note, image selection/paste/drop concepts, disabled-until-live behavior, progress and error states. Desktop-only input mechanisms are not copied to the R1. |
| Browser API calls | `frontend/src/browser-voice/api.ts` | Authenticated workspace upload followed by `/me/workspace-files/inspect` with profile `direct_handoff` and optional question. |
| Inspection endpoint | `app/modules/workspace_files/router.py` | Authenticated actor and routed workspace authority. |
| Inspection implementation | `app/modules/workspace_files/inspection_service.py` | Supported image validation, high-detail OpenAI Responses image input, grounded profile instructions, question-aware/content-aware cache, bounded inspection markdown, and suggested filename extraction. |

The donor sends no raw image over the Realtime data channel. It sends the image to a separate Responses inspection request, then injects the grounded result into the existing Realtime conversation as:

```json
{
  "type": "conversation.item.create",
  "item": {
    "type": "message",
    "role": "user",
    "content": [{"type": "input_text", "text": "<grounded handoff context>"}]
  }
}
```

It then sends exactly one `{"type":"response.create"}` when no provider response is already in flight.

## Standalone ownership and destination map

No donor file is copied until its exact source revision/hash, license decision, destination, retained behavior, omitted behavior, and focused tests are recorded in `docs/DONOR_CODE_REFERENCE_MAP.md`.

```text
android/feature/camera/
  owns Camera2, motor-confirmed capture, preview, transient captured frame
            |
            v
android/feature/handoff/
  owns capture review state and runtime upload/inspection coordination
            |
            +---------------------> android/runtime-host/
            |                         owns authenticated local HTTP calls
            v
android/feature/voice/
  owns current session ID, response-in-flight state, transcript, RTCDataChannel
            |
            v
runtime/resono_runtime/handoff/
  owns image limits, workspace persistence, inspection prompt/profile/cache
            |
            v
existing OpenAI Responses provider boundary
```

Required public boundaries:

- `feature:voice` exposes a narrowly named `VoiceSessionHandoff` interface. It reports whether the current session can accept a handoff and submits already-inspected provider text plus user-visible transcript text and file identity.
- `VoicePageView` remains the only owner of the Realtime session ID, `NativeVoicePeer`, response-in-flight state, and transcript entries.
- `feature:handoff` depends on the Voice handoff interface and runtime-host API, not on `VoicePageView` internals or `NativeVoicePeer`.
- `feature:camera` returns a captured-image reference to the handoff coordinator. It does not call OpenAI or send Realtime events.
- `runtime-host` adds explicit handoff upload and inspection methods. It does not contain prompts, UI state, Camera2, or Realtime event construction.
- `runtime/resono_runtime/handoff/` is one small domain package, not a generic file manager or catch-all service. It owns the standalone bounded image contract and calls the existing provider abstraction.
- `ProductRootView` coordinates navigation and hands interfaces to features. It does not own image bytes, inspection logic, or provider events.

## Current-code connection points

- `android/feature/voice/.../VoicePageView.java` already owns `sessionId`, `NativeVoicePeer`, transcript recording, and the real state reducer.
- `android/feature/voice/.../NativeVoicePeer.java#sendRealtimeEvent` already sends arbitrary JSON through the current open Realtime data channel and returns false when unavailable.
- `android/runtime-host/.../RuntimeVoiceClient.java` already owns authenticated runtime HTTP and current Voice-session requests; its handoff additions must remain explicit methods rather than a generic request helper exposed to features.
- `android/app/.../ProductRootView.java` currently keeps the `VoicePageView` instance alive when switching to Cards. The Camera pager must preserve the same instance rather than rebuilding it.
- The standalone runtime currently has no workspace-image inspection endpoint. That is a real missing dependency; Android handoff UI cannot land before it exists.

## Runtime contract

The standalone implementation may simplify donor platform/vault machinery but must retain its security properties:

1. Accept JPEG, PNG, and WebP only in the first implementation; reject MIME/extension/signature mismatch.
2. Enforce one documented byte limit before persistence and before provider encoding. The donor's 24 MiB ceiling is a reference, not automatically accepted for the smaller R1.
3. Generate the storage key on the runtime from the authenticated Voice session ID and a random suffix. Do not trust an arbitrary Android filesystem destination.
4. Verify that the Voice session is current and owned by the local device before inspection.
5. Use the configured OpenAI Responses model through the existing provider boundary with high-detail image input.
6. Cache only by content hash, inspection contract version, model key, and normalized optional question.
7. Return bounded inspection markdown, canonical file ID/key, original display name, and optional suggested filename.
8. Never expose provider credentials or raw filesystem paths to Android.
9. Record the handoff file identity and `directHandoff=true` with the user transcript entry.
10. Apply the same deletion/retention policy to the image and inspection; this contract must be fixed before release rather than leaving permanent unbounded captures.

## Voice injection contract

The Voice owner performs one atomic logical operation:

1. Recheck that the same session ID remains active and the data channel is open.
2. Append the concise user-visible entry (`<note>\n[Image handoff: <name>]`) to the local transcript.
3. Send one `conversation.item.create` with one `input_text` containing the grounded inspection envelope.
4. If no response is in flight, mark it in flight and send one `response.create`.
5. Move the native state to `responding`.
6. Persist transcript/file metadata through the existing session finalization path.

The handoff coordinator never sends provider events itself. This prevents a second Realtime owner and preserves ordering with ordinary speech and tool outputs.

## UI state contract

| State | Visible treatment |
|---|---|
| Voice idle/connecting/error | `Hand to Voice` unavailable; concise reason available on focus/tap. |
| Voice live/responding | Secondary action available. |
| Entering handoff | Move directly from Voice to full-screen Camera in handoff mode; no source picker or system product dialog. |
| Capturing | Live full-screen Camera with shutter and Cancel; Voice continues audibly. |
| Reviewing | Frozen real frame; shutter becomes `Send to Voice`; Retake and Cancel remain available; optional note does not obscure the frame. |
| Uploading | `Saving image...`; destructive navigation disabled, Cancel behavior explicitly defined by implementation. |
| Inspecting | `Reading image...`; Voice remains connected. |
| Injecting | `Adding to this conversation...`; bound to the captured session identity. |
| Responding | Return to Voice and use its canonical `responding` state. |
| Failed | Keep review frame for retry; specific failure; no fake success or automatic new session. |

## Tests and physical acceptance

Focused automated tests must prove:

- disabled action without a live/open current Voice session;
- MIME, signature, size, empty-content, and malformed-response rejection;
- session-scoped storage and rejection of a stale/different session;
- inspection envelope is grounded, bounded, and includes file identity and optional note;
- exactly one user conversation item and at most one response request;
- no `response.create` while another provider response is in flight;
- transcript displays the concise handoff rather than hidden provider context;
- failure before injection produces no conversation item;
- Voice owner remains singular; Camera and handoff modules cannot access `NativeVoicePeer` directly;
- cancellation, retry, retention, and cleanup behavior.

Physical R1 acceptance must prove:

1. Start one real Voice session and record its session identity.
2. Open `Hand to Voice`, capture a real correctly oriented Camera2 frame, and keep two-way audio live.
3. Verify capture alone sends nothing; use Retake once, capture again, then press `Send to Voice` and hear the same Voice session accurately discuss its contents.
4. Verify the session identity did not change and no second WebRTC connection opened.
5. Exercise Retake, Cancel, denied permission, provider failure, data-channel loss, and stale-session rejection.
6. Return the motor to confirmed privacy and verify no camera or temporary capture remains active after exit.

## Entry and sequencing gates

Documentation does not authorize a disconnected control. Implementation order is:

1. Close or explicitly supersede the active Build Contract 05 exclusion that currently keeps Camera/later capability work out of that contract.
2. Pass Camera gates C1-C4 with a real frame on the physical R1.
3. Freeze the standalone runtime upload/inspection API, retention rule, size ceiling, provider model source, and error contract.
4. Implement and test the runtime domain and runtime-host client without user-facing UI.
5. Add the narrow Voice handoff port and its ordering tests.
6. Add `feature:handoff` review/coordinator behavior.
7. Expose `Hand to Voice` only when the complete real path is connected.
8. Complete physical acceptance before declaring the capability available.
