# R1 Camera, Motor State, and Preview Recovery Research

**Research date:** 2026-08-20  
**Status:** evidence consolidation only; no implementation authorization  
**Authority:** historical physical records, exact donor sources, exact current-image audit, Android Camera2 documentation, and owner statement that CipherOS camera operation is known working

## Purpose

This document brings the surviving Rabbit R1 camera research into the standalone ReSono R1 repository without copying donor code. It records:

- the three physical rotating-camera states;
- what was physically proven working;
- the later reopen and preview-orientation correction;
- which later correction was not physically closed in its own report;
- why the current product camera does not open;
- how an upright, undistorted 480×640 preview must be calculated;
- the clean ownership boundaries a future implementation must preserve;
- the evidence required before declaring recovery complete.

It does not authorize direct sysfs access, import a donor source file, add a disconnected camera UI, or claim that the current APK has a working camera.

## Executive finding

The CipherOS CameraService, MediaTek camera provider/HAL, sensor path, and rotating camera hardware were not the first evidenced defect. ReSono previously produced a real Camera2 preview and JPEG after a safe motor move. The retained image omitted the required motor-service package, and the first standalone repair then installed that service with the wrong debug signing identity, causing it to run as `untrusted_app` and fail closed. Physical correction on 2026-08-20 reproduced the historical mechanism: a removable bridge signed with the matching AOSP development platform key ran as `platform_app`, confirmed OUTWARD before Camera2 opened, and returned to privacy on close.

The earlier preview-orientation defect is also understood. The first implementation applied an unconditional 90-degree `TextureView` rotation. That double-applied part of the orientation work because `TextureView` already brings the sensor buffer into the device's natural orientation. The correction used measured Camera2 characteristics, current display rotation, lens facing, and aspect-preserving center-fill scaling.

## Evidence hierarchy

### Physically confirmed

The donor phase contract records a physical engineering run on 2026-08-02:

- privacy position `90` moved to outward position `180`;
- Camera2 device `0` connected only after the privileged bridge confirmed `OUTWARD`;
- a real JPEG was written under app-private storage with mode `0600`;
- Camera2 disconnected and reported closed;
- the motor returned from `180` to privacy `90`;
- a negative run with the bridge unavailable reported `Motor unavailable`, kept the motor at `90`, and opened no camera device.

Authority:

`/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace/phases/2026-08-02_rabbit_r1_modular_pages_cards/F5-CAMERA-MOTOR-BUILD-CONTRACT-v1.0.md`

### Implemented and locally validated, but not physically closed by its own report

The 2026-08-03 correction addressed:

- first-open success followed by later `Motor failed`;
- stale in-process motor state;
- repeated/duplicate privacy requests;
- preview rotated incorrectly on the portrait screen;
- preview not filling the available screen;
- preview-size selection and aspect handling.

That report records a successful focused build and these hashes:

- corrected application APK: `deab1d79fc1061a95d83983807414e8a04d12ef3b4a90b1b28b51724948573e6`;
- corrected motor bridge APK: `5f000b02c7e55b4d2ec5b68a030b2cf07673fc32d95fbd09ae44dc30a10afb5a`.

However, the same report explicitly says USB permission prevented installation during that correction pass. It leaves repeated open/close/open, orientation, fill, and owner acceptance as physical gates. No later document found in the donor workspace truthfully closes those exact gates. The owner's present statement that the deleted APK worked perfectly is important product authority, but it is not replaced here with a fabricated missing log.

Authority:

`/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace/phases/2026-08-02_rabbit_r1_modular_pages_cards/CAMERA-AUDIO-QUALITY-CORRECTION-REPORT-2026-08-03.md`

### Later exact regression audit

The 2026-08-12 exact-image audit found:

- ReSono's packaged Camera feature first binds action `com.resonolabs.hardware.motor.R1_MOTOR_SERVICE` in package `com.resonolabs.hardware`;
- it deliberately does not call Camera2 until the requested named position returns `AT_POSITION`;
- the current system image contains `ReSonoHome.apk` but no `com.resonolabs.hardware` motor-service APK;
- therefore the first deterministic image failure was an omitted dependency; after adding it, the remaining failure was the bridge signing/domain identity, not Camera2;
- historical physical validation opened camera IDs `0` and `1` after motor confirmation, but the later exact image had no current camera-attempt trace.

Authority:

`/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace/phases/2026-08-12_r1_wheel_backlight_trigger_grounding/RESEARCH-AND-HOME-APK-AUDIT.md`

## Three-state physical contract

The rotating camera has exactly three product states, but they cannot be inferred from the orientation command alone. Final instrumented behavior on product R1 `919109A5P1600502814D` uses raw `180` before opening the OUTWARD Camera2 device and again only after Camera2 fully closes to establish CLOSED/privacy. INWARD uses raw `0`. Camera2 open/closed lifecycle is therefore part of the authoritative state; an echoed `180` without Camera2 state cannot distinguish OUTWARD from CLOSED.

Instrumented review refined the failure mechanism twice. Requesting `0` before outward open caused an unnecessary full sweep through the user-facing direction; that approach is rejected. The correct OUTWARD path requests `180` and then opens Camera2 ID `0` directly. On shutdown, privacy return occurs after `CameraDevice.StateCallback.onClosed`, with a bounded fallback, so the final writer is the narrow motor service commanding CLOSED `180`. The orientation file reports the last command and cannot prove mechanical arrival by itself.

| Product name | CipherOS/hardware meaning | Raw orientation | Lens direction |
| --- | --- | ---: | --- |
| `INWARD` | Front | `0` | toward the user/display side |
| `HOME` | Privacy | `90` | mechanically closed/down |
| `OUTWARD` | Rear/Back | `180` | away from the user |

The raw numbers belong only inside the privileged hardware adapter. Application and UI code use named positions. Public Rabbit R1 community documentation independently reports the same node and values: [Rabbit R1 Android guide](https://gist.github.com/sayhiben/3360560925f922857e3f8d159ee5d50d). Rabbit's official manual confirms that its Vision experience flips the physical camera with the wheel: [Rabbit R1 manual](https://www.rabbit.tech/guide/rabbit-r1-manual.pdf).

Android's generic lens-cover state is not the R1 motor-state authority. Preserved system evidence reports `CAMERA_LENS_COVER_ABSENT` even on this rotating device. The authoritative state is the confirmed value read from:

`/sys/devices/platform/step_motor_ms35774/orientation`

Only the privileged motor service may read/write that node in the product architecture.

## Required state model

Position and operation state are different facts and must not be collapsed.

### Confirmed position

```text
UNKNOWN
INWARD
HOME
OUTWARD
```

### Movement state

```text
CONNECTING
MOVING
AT_POSITION
FAILED
UNAVAILABLE
```

The service must reread the hardware node before every move. If hardware already reports the requested position, it returns `AT_POSITION` without performing a redundant full movement. Persisted application state is useful for UI continuity but cannot override the current hardware reading after process death, reboot, service reconnect, timeout, or manual/system movement.

The original correction moved the Binder client to root-application lifetime rather than recreating and closing it for each Camera view. This prevented a view close, duplicate `HOME`, stale service state, and immediate reopen from racing one another.

## Safe movement rules

- Accept only `INWARD`, `HOME`, and `OUTWARD` across the app/service boundary.
- Map names to raw values only in the privileged service.
- Serialize all movement on one executor/queue.
- Before reversing across the full arc (`0` to `180` or `180` to `0`), pass through privacy `90`.
- Report `MOVING`, then confirm the node within a bounded timeout.
- Do not open Camera2 until the exact requested position is confirmed.
- Close Camera2 before changing physical direction.
- On failure, cancellation, view close, Activity removal, service destruction, or shutdown, request `HOME`.
- A failed privacy return remains a visible hardware fault; it must not be reported as closed.
- Neither the app nor a model may send raw degrees or open sysfs.

## Preview-orientation defect and correction

### What was wrong

The first Camera view rotated its `TextureView` by 90 degrees unconditionally. That assumption was invalid because the correct result depends on:

- the selected camera ID;
- `CameraCharacteristics.SENSOR_ORIENTATION`;
- `CameraCharacteristics.LENS_FACING`;
- current display rotation;
- whether width and height swap after relative rotation;
- the preview buffer aspect ratio versus the 480×640 viewfinder.

It produced a sideways or double-rotated preview and could also stretch or under-fill the display.

Android documents that `TextureView` accounts for sensor orientation but does **not** handle current display rotation or preview scaling. Those remaining transforms must be applied deliberately: [Camera preview](https://developer.android.com/media/camera/camera2/camera-preview) and [resizable Camera2 surfaces](https://developer.android.com/codelabs/android-camera2-preview).

### Relative-rotation calculation

The surviving correction and Android's official formula agree:

```text
sign = +1 for front-facing, -1 for back-facing
relativeRotation =
    (sensorOrientation - displayRotationDegrees * sign + 360) % 360
```

The surviving donor unit tests preserve measured expectations:

| Sensor | Display | Facing | Expected relative rotation |
| ---: | ---: | --- | ---: |
| `90` | `0` | back | `90` |
| `90` | `90` | back | `180` |
| `90` | `90` | front | `0` |

These tests are evidence for the sign difference, not a license to hard-code a universal 90-degree rotation.

### Aspect-preserving 480×640 preview

The corrected policy was center-fill, not stretch:

1. Read supported `SurfaceTexture` output sizes from the selected camera.
2. Determine whether relative rotation swaps displayed width and height.
3. Compare each candidate's displayed aspect ratio with the actual viewfinder dimensions.
4. Prefer the closest displayed aspect ratio, then the largest bounded resolution.
5. Set the `SurfaceTexture` buffer to that selected size.
6. Compute X and Y scales with swapped dimensions when rotation requires it.
7. Use one uniform fill scale equal to `max(scaleX, scaleY)`.
8. Apply only the minimum centered crop needed to fill 480×640.
9. Apply display-rotation compensation; do not repeat sensor-orientation rotation already handled by `TextureView`.

The acceptance result is upright, centered, filled, and not geometrically stretched. Some edge crop is expected when the sensor and display aspect ratios differ.

### Still-image orientation is separate

Preview transformation affects only the viewfinder. JPEG capture must set its own orientation metadata/request from measured sensor and device orientation. A correct preview does not by itself prove a correctly oriented saved image.

## Camera selection after motor confirmation

The donor correction chose the Camera2 lens facing that corresponds to the confirmed physical position:

- `INWARD` requests a front-facing Camera2 device;
- `OUTWARD` requests a back-facing Camera2 device;
- `HOME` opens no camera.

Selection must inspect the current `CameraManager` ID list and characteristics. IDs such as `0` and `1` are evidence from a device run, not permanent semantic names. If no requested facing exists, any fallback must be explicitly measured and must never contradict the physical lens direction.

## Preview lifecycle

The clean order is:

```text
camera surface requested
  -> close any existing Camera2 device/session
  -> request named motor position
  -> receive exact AT_POSITION confirmation
  -> select Camera2 ID by measured facing
  -> read sensor orientation and output sizes
  -> configure TextureView buffer and transform
  -> open Camera2
  -> configure preview session
  -> first real repeating frame
```

Close order is:

```text
stop repeating / close session
  -> close CameraDevice
  -> close ImageReader and release surfaces
  -> stop camera thread
  -> request HOME
  -> confirm privacy or report fault
```

Opening, closing, reopening, Activity stop/resume, screen suspend, permission denial, motor timeout, Camera2 disconnect, and Camera2 error all need physical tests.

## Real preview surface placement

Historical ReSono presented Camera as a Card and opened a full native Camera detail surface. The owner has now frozen a cleaner two-level composition: Voice and Cards remain tabs together on the Main product page; Camera is a separate full-screen root page reached by horizontal swipe. The Main header moves off screen with its page. Swiping back restores the prior Voice or Cards selection.

```text
Main product page                         Camera page
  Voice / Cards header          <---->      full-screen preview
  selected Voice or Cards tab               camera state and controls
```

This is not a third header tab and does not require a Camera icon. A future discoverability cue may teach the swipe without changing the frozen hierarchy.

Whichever entry is selected, it must open one real native preview owned by the Camera feature module. It must not:

- embed a management-web camera viewer;
- add a static/fake preview;
- make Cards or `ProductChromeView` own Camera2;
- open camera in the background merely because the icon is visible;
- hide the physical position or privacy-return state.

A real camera surface should visibly distinguish `Moving`, `Facing you`, `Facing outward`, `Returning to privacy`, `Closed`, and `Hardware fault`. The UI label is derived from confirmed named state, never a guessed timer.

## Voice session continuity while Camera is visible

Presentation and connection lifetime must be independent. Swiping the Main page away must not close the active WebRTC Voice connection. The existing session owner remains at Activity/runtime lifetime while the Voice view becomes non-visible.

Camera preview is video-only and must not request microphone input, audio focus, communication mode, or an audio route. Therefore Camera2 preview and the existing WebRTC microphone/speaker path can coexist. Camera errors affect Camera only. Voice errors affect Voice only. Neither page transition recreates `MainActivity`.

Required physical proof:

1. Start a real Voice session and record its session identity/state.
2. Swipe to Camera without a WebRTC disconnect or renegotiation.
3. Confirm live Camera2 preview while two-way Voice audio continues.
4. Swipe back and confirm the same Voice session and current state render immediately.
5. Repeat the cycle and confirm no leaked CameraDevice, surface, motor request, microphone owner, or audio-focus change.

This continuity does not grant the Voice model access to camera frames. The separate explicit submission path is now defined by [`../planning/2026-08-20-r1-direct-handoff-contract.md`](../planning/2026-08-20-r1-direct-handoff-contract.md): a reviewed frame is uploaded and inspected, then grounded inspection text is injected through the existing Voice session's open Realtime data channel. Raw image bytes are not sent through that channel, and no second Voice session or agent is created.

## Automatic Creation QR recognition

Creation recognition is an analysis path over real preview frames:

```text
Camera2 preview frame
  -> bounded low-resolution analysis image
  -> CreationQrDecoder
  -> decoded text
  -> strict Rabbit descriptor parse
  -> existing runtime QR preflight
  -> ReSono review overlay
  -> explicit confirm/replace
  -> existing Creation lifecycle and Cards generation refresh
```

- Analyze reduced-resolution frames at a bounded rate; preview remains smooth.
- Pause analysis after one supported code is found.
- Debounce the same payload so it cannot repeatedly open review.
- Ignore unsupported QR content rather than treating every QR as a Creation.
- Accept only documented descriptor fields and secure HTTPS destinations.
- Never install from a decoder callback.
- Send decoded descriptor data through the existing `/v1/management/creations/qr/preflight` policy/lifecycle boundary.
- Present server-returned identity, source, audience choice, validation result, and conflict/replacement state.
- Require explicit `Import` or `Replace existing Creation`.
- Cancel performs no mutation and resumes scanning.
- Success refreshes the native Cards catalog dynamically without reboot.

## ReSono overlay research decision

Native Android/CipherOS dialogs visually break the product flow and are not the product confirmation primitive going forward. Camera uses a ReSono-owned overlay composed inside its page over the real preview. The overlay freezes or dims preview presentation while Camera2 ownership remains deterministic, uses the R1 navy/hairline/accent system, traps focus, and exposes explicit Cancel and primary actions.

System permission prompts cannot be restyled and remain the sole permitted platform dialog. Existing product dialogs may be migrated later, but no new Camera or Creation flow may add another system-styled product dialog.

## Surviving donor sources and identities

No file was copied. These read-only sources preserve the researched implementation:

| Concern | Donor source | SHA-256 |
| --- | --- | --- |
| Named position/state interface | `app/rabbit_r1/android/core/motor/src/main/java/com/resonolabs/hardware/motor/MotorController.java` | `eb046e691d23d23bd46c270c4d59c3923b91cc614fbb71054f5ca437f1a3eceb` |
| Binder client/lifetime | `app/rabbit_r1/android/core/motor/src/main/java/com/resonolabs/hardware/motor/R1MotorServiceClient.java` | `e3fb506361cb02f204e8d9ed9f44ac04ed73be81ae9285821a8b2bc5120814b8` |
| Privileged sysfs owner | `app/rabbit_r1/android/system/motor-service/src/main/java/com/resonolabs/hardware/R1MotorService.java` | `77ac5de806dff7a44b25e43c79fcaeff0caf5db03bee6c6cec741d3f87404ceb` |
| Camera2 lifecycle/preview/transform | `app/rabbit_r1/android/feature/camera/src/main/java/com/resonolabs/feature/camera/CameraPanelView.java` | `8fd6a5263f7aa897d920c6d369b2e53630e92b198b34edbabdfacb98d55fce58` |

All paths are relative to the read-only donor root:

`/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace/`

## Current recovery boundary

Research supports this order and no broader claim:

1. Verify CipherOS camera provider/IDs and stock preview on the exact current device.
2. Package/restore the existing narrow privileged motor service with correct signing, caller pin, SELinux, and sysfs access.
3. Read and confirm all three named positions through the service.
4. Prove privacy return.
5. Restore the smallest Camera2 preview using the corrected orientation/aspect policy.
6. Prove first frame, close, reopen, inward/outward switching, suspend/resume, and error cleanup.
7. Only after that decide final native entry placement and any QR scanning integration.
7. Add bounded automatic Creation QR analysis and the shared preflight/confirmation flow.
8. Compose the full-screen Camera root page and prove live Voice continuity across repeated swipes.

The existing [camera recovery contract](../planning/2026-08-20-camera-recovery-contract.md) remains the implementation gate. This research document supplies recovered facts; it does not mark any gate complete.
