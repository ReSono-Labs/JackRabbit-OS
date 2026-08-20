# R1 Camera Recovery Contract

**Identity:** `R1-CAMERA-RECOVERY-v0.1-research-gate`  
**Status:** Camera preview/root-swipe recovery physically proved; Direct Handoff end-to-end acceptance remains open  
**Authority:** Owner direction on 2026-08-20 to move from Rabbit Creation QR host
implementation to the deferred camera defect

## Purpose and non-negotiable boundary

Recovered historical evidence, the three-state mapping, the physically proven run, the later reopen/orientation correction, exact donor source identities, and the current missing-service regression are consolidated in [`../research/R1_CAMERA_MOTOR_AND_PREVIEW_RECOVERY.md`](../research/R1_CAMERA_MOTOR_AND_PREVIEW_RECOVERY.md). That research record informs this contract but does not close its physical gates.

Restore the real R1 rotating-camera path without guessing which layer failed and
without copying the donor's known-failing behavior into the clean product. This
contract is a focused recovery intermission. It does not pull Calendar,
Contacts, Reminders, a gallery/store, or unrelated system-image work forward.

No user-facing camera or QR-scanner surface may land until a real Camera2 frame
is physically produced. No fake preview, static image, simulated scan, or
disconnected camera card is permitted.

## Frozen product navigation and Voice continuity

Camera is a second root page, not a third tab inside the existing Voice/Cards page:

```text
Root page 1: Main product page                 Root page 2: Camera
  persistent Voice/Cards header       <---->    full-screen native preview
  Voice tab                                      Camera state/controls
  Cards tab                                      Creation scan review overlay
```

- Tapping the existing header tabs switches only between Voice and Cards.
- A deliberate horizontal swipe moves the complete Main product page, including its header, off screen and reveals full-screen Camera.
- The reverse swipe returns to the Main product page and restores whichever of Voice or Cards was selected before Camera opened.
- Vertical Cards navigation must not be captured as a root-page swipe. Root navigation commits only after horizontal travel clearly exceeds vertical travel and the distance/velocity threshold.
- Camera does not remain open behind the Main product page. Leaving Camera stops analysis, closes Camera2, releases surfaces, and requests confirmed `HOME`/privacy.

An active Voice connection must remain live throughout Camera entry, use, and return. This is non-negotiable:

- Root-page navigation hides the Voice presentation; it does not detach, destroy, stop, or recreate the Voice session owner.
- The existing Activity/runtime-owned WebRTC session continues receiving and playing audio.
- Camera preview requests `CAMERA` only. It must not request microphone capture, change audio mode, take audio focus, stop WebRTC, or recreate the Activity.
- Voice state accumulated before the swipe remains the same on return, including live/connecting/responding/error state and conversation/session identity.
- If Camera2 fails, Voice remains live and Camera alone reports failure/returns to privacy.
- If Voice changes state while Camera is visible, the state is retained and rendered immediately when the Main product page returns.
- Explicit photo/vision submission is the separately owned Direct Handoff capability defined by [`2026-08-20-r1-direct-handoff-contract.md`](2026-08-20-r1-direct-handoff-contract.md). Keeping Voice connected grants no camera-frame access; only an explicit reviewed `Hand to Voice` confirmation may submit one captured frame to the current session.

Physical acceptance must include an active Voice session before the swipe, continuous two-way audio while Camera preview is live, continued session identity after swiping back, and no Camera/microphone ownership conflict in logs.

## ReSono-owned overlays; system dialogs prohibited for product flow

Camera scanning, import review, overwrite warning, validation errors, and success state must render as components inside the ReSono Camera page. Do not use `AlertDialog`, a CipherOS-styled dialog, Toast confirmation, a browser popup, notification, or separate Activity.

The only system surface that may appear is an Android runtime permission prompt where the platform requires it. Product confirmation immediately before import remains ReSono-owned even if permission was granted in the same visit.

The overlay uses the established R1 language: translucent navy surface over a frozen/dimmed real preview, hairline border, restrained type, aqua primary action, yellow conflict/replacement warning, and red only for an error or destructive action. It must be accessible, focus-contained, dismissible without mutation, and driven by real preflight state.

## Current facts

- The owner accepted the original physical baseline as working except camera.
- The current clean APK has no camera feature module and does not request
  `android.permission.CAMERA` in its manifest.
- The image retains `Camera2`, `com.cipheros.camerax`, CameraService init,
  `camerahalserver`, the MTK vendor camera stack, and fixed engineering-package
  camera permission configuration.
- A fixed permission XML cannot grant a permission the APK does not declare.
- The donor camera feature uses Camera2 directly, not CameraX.
- The donor camera opens only after its motor client reports the requested named
  position as confirmed.
- The donor privileged motor service is the sole writer of
  `/sys/devices/platform/step_motor_ms35774/orientation`; it serializes moves,
  uses a privacy waypoint for direction reversal, polls for confirmation, and
  returns to privacy on failure/task removal/destruction.
- Because the donor baseline itself failed camera acceptance, its UI/module is
  reference behavior, not an implementation proven safe to import unchanged.

## Layer map

```text
Native camera feature
    -> Android Camera2 CameraManager / CameraDevice / capture session
    -> cameraserver / CameraService
    -> retained MTK camera provider and HAL
    -> ISP / sensor

Native camera feature
    -> narrow MotorController
    -> IR1MotorService Binder
    -> privileged R1MotorService
    -> step_motor_ms35774 orientation sysfs node
    -> rotating camera motor
```

## Donor reference locations (read-only)

- Camera UI/open/preview/capture/close:
  `/home/christian/Documents/Projects/ReSono-Labs-Voice/project-3d3354dadcad/workspace/app/rabbit_r1/android/feature/camera/src/main/java/com/resonolabs/feature/camera/CameraPanelView.java`
- Camera card metadata:
  `.../android/feature/camera/src/main/java/com/resonolabs/feature/camera/CameraCard.java`
- Narrow application-side motor state adapter:
  `.../android/core/motor/src/main/java/com/resonolabs/hardware/motor/MotorController.java`
- Binder client and AIDL:
  `.../android/core/motor/src/main/java/com/resonolabs/hardware/motor/R1MotorServiceClient.java`
  and `.../android/core/motor/src/main/aidl/com/resonolabs/hardware/motor/`
- Privileged motor owner:
  `.../android/system/motor-service/src/main/java/com/resonolabs/hardware/R1MotorService.java`
- Hardware boundary:
  `.../app/rabbit_r1/docs/08_HARDWARE_INVOCATION_CONTRACT.md`

Before copying any donor file, record its source revision, exact source and
destination, retained/omitted behavior, license, and mirrored tests as required
by repository policy.

## Required physical diagnosis, in order

### Gate C1: framework and HAL inventory

Read only:

- `pm list features` camera declarations;
- `dumpsys media.camera` provider, IDs, characteristics, client/error state;
- camera/provider/cameraserver process and service state;
- relevant package enabled/install state;
- camera AppOps and runtime grants for the stock camera and engineering APK;
- logcat categories for CameraService, camera provider/HAL, SELinux denials, and
  application exceptions.

Do not move the motor or install a camera build in this gate.

Decision:

- No camera IDs/provider failure means image/vendor/HAL diagnosis first.
- Valid IDs advance to stock Camera2 isolation.

### Gate C2: retained stock-camera isolation

Launch the retained stock `Camera2`/Cipher camera package and capture exact
CameraService/provider/logcat evidence.

Decision:

- Stock failure means the defect is below ReSono and app code must not be built
  as a supposed fix.
- Stock preview success means the retained HAL path works and diagnosis advances
  to ReSono permission/lifecycle/motor ordering.

### Gate C3: motor state without unsafe movement

Read the current orientation and inspect existing privileged motor service,
Binder registration, caller certificate allowlist, SELinux state, and package
presence. Do not write sysfs directly from the app or shell. A movement test
requires an explicit command through the narrow service and physical owner
observation, with privacy return as a mandatory postcondition.

Decision:

- Motor unavailable/unauthorized is repaired at the service/permission boundary.
- Confirmed safe named positions advance to coordinated camera open.

### Gate C4: minimal real Camera2 producer

Only after C1-C3 pass, build the smallest native diagnostic producer:

- one lifecycle-owned `TextureView`;
- one background camera thread;
- one selected camera ID from measured characteristics;
- preview only at first;
- deterministic timeout and complete close on detach/focus loss/error;
- no capture, QR decode, gallery, Creation import, or agent tool yet.

The diagnostic must report the actual camera ID, selected output size, state
callbacks, session configuration, first-frame proof, and close/reopen result.

### Gate C5: clean product module

After first-frame and reopen proof, create modular owners:

```text
android/
  core/motor/              narrow Binder client/state contract
  feature/camera/          Camera2 lifecycle and preview only
  system/motor-service/    privileged serialized motor owner, if absent/broken
```

The app module composes these owners. It must not absorb Camera2, motor sysfs,
or QR decoding into `ProductRootView`, `MainActivity`, Cards, Voice, or generic
utility classes.

### Gate C6: Rabbit Creation QR scanning

Only after stable preview/reopen:

- add a decoder behind a narrow `CreationQrDecoder` contract;
- accept only the documented Rabbit descriptor JSON fields;
- send decoded JSON to the existing authenticated
  `/v1/management/creations/qr/preflight` lifecycle;
- show preflight/overwrite details and require explicit confirmation;
- never install directly from the camera callback;
- reject malformed/non-HTTPS/private destinations through the runtime's
  existing descriptor inspector.

Camera scanning and browser QR-image decoding must converge on the same runtime
preflight contract.

### Gate C7: full-screen root navigation and connected-Voice proof

After preview/reopen and QR lifecycle pass:

- compose a root pager with Main product page and Camera page;
- preserve the existing nested Voice/Cards tab state inside the Main page;
- move the complete Main header with its page during horizontal transition;
- instantiate Camera ownership only when entering the Camera page;
- stop analysis, close Camera2, and confirm privacy when leaving;
- preserve the live WebRTC Voice session independently of presentation visibility;
- prove swipe discrimination against Cards vertical navigation and Camera controls;
- prove process/session survival across repeated Main/Camera/Main cycles.

Do not move Camera2, motor state, QR parsing, import validation, or Voice session ownership into `ProductChromeView`. The root owns navigation only.

### Gate C8: explicit Direct Handoff

Only after C1-C7 pass, implement the contract in [`2026-08-20-r1-direct-handoff-contract.md`](2026-08-20-r1-direct-handoff-contract.md):

- expose `Hand to Voice` as a labeled secondary Voice action, never as the Camera icon;
- enter Camera directly in explicit handoff-capture mode while the existing Voice session remains live;
- show a shutter before capture, then change that primary control to `Send to Voice` over the frozen real frame;
- provide `Retake` and `Cancel`; capture alone must not upload, inspect, or inject anything;
- upload and inspect through the on-device runtime before injecting context;
- inject inspection text through the current Voice owner's existing Realtime data channel;
- bind confirmation and injection to the same session identity;
- use ReSono-owned review/progress/error overlays and never a CipherOS product dialog;
- prove that no second agent, WebRTC connection, or Realtime session is created.

Direct Handoff does not absorb automatic Creation QR scanning. A frame is either in explicit handoff-capture flow or normal Camera/Creation analysis flow; it cannot silently perform both actions.

## Acceptance

- Provider/ID inventory recorded from the exact device/image.
- Retained stock-camera result identifies whether the defect is below ReSono.
- Motor state and privacy return physically proved without direct app/sysfs
  writes.
- Real preview first frame, stop, reopen, suspend/resume, and failure cleanup
  pass on an exact hashed APK.
- Camera and microphone ownership do not conflict with active Voice WebRTC.
- Active Voice remains connected and usable while Camera is visible and returns with the same session identity/state.
- Full-screen Camera swipes away the complete Main page/header and reverse swipe restores the prior Voice/Cards selection.
- All Camera/Creation review states use ReSono-owned in-page overlays; no CipherOS product dialog is introduced.
- QR scan decodes a real Rabbit descriptor, reaches shared preflight, requires
  confirmation, appears dynamically in native Cards, opens at 240x282 logical
  size, and deletes through the shared Creation lifecycle.
- `Hand to Voice` submits one reviewed real frame to the same live Voice session through the separately tested upload, inspection, and current-data-channel path.
- Negative tests cover denied permission, no provider/ID, motor unavailable,
  open timeout, malformed QR, unsafe URL, duplicate overwrite cancellation, and
  deletion.

## Proven bridge identity correction

Physical deployment on serial `919109A5P1600502814D` first installed a debug-signed `com.resonolabs.hardware`. Binder resolution and caller authentication reached the service, but its `u:r:untrusted_app:s0` process received `EACCES` opening the motor node. That run proves fail-closed behavior, not a missing custom policy.

The donor's original physical contract records the concrete working distinction: its removable `/data/app` bridge was re-signed with the same public AOSP development platform certificate as this `cipher_r1-userdebug 16` build and ran as `u:r:platform_app:s0`; OUTWARD `90 -> 180`, Camera2 open, and HOME `180 -> 90` passed under enforcing SELinux. Device inspection independently confirms the stock platform certificate digest is `c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8`. The donor repository's currently retained motor APK is only debug-signed and is not the working artifact.

The repository therefore owns a deterministic signing wrapper, `android/scripts/sign_motor_service_for_r1.sh`, which accepts externally obtained official AOSP development key paths, emits a separately named APK, and refuses any certificate digest other than the exact device platform digest. Keys are never committed. This mechanism is restricted to the userdebug engineering baseline. A production/release-key image must provide a corresponding narrow trusted service identity and reviewed policy rather than shipping public development keys. `setenforce 0`, HOME sysfs access, broad allow rules, and manual motor writes remain prohibited.

Root navigation was also found incomplete: Camera existed only as a Direct Handoff destination and no root horizontal gesture owner existed. The corrected composition separates normal Camera preview from Direct Handoff capture. A left swipe on the Main page opens normal Camera without requiring Voice; a right swipe closes Camera, confirms HOME, and restores the prior Voice/Cards tab. Gesture arbitration commits only to horizontal movement so Cards vertical navigation remains owned by Cards.

## 2026-08-20 physical correction evidence

Target: R1 serial `919109A5P1600502814D`, enforcing `cipher_r1-userdebug 16`.

- HOME APK SHA-256: `539bab64893c363b17b1da2c7b1046eac3ca9447545f4815ebe3938ee06ef3a8`.
- Platform-signed motor APK SHA-256: `a11147d0e60e889d9044aa6ab323642029a5fc8b8100afe61cb62da5c3923899`.
- Motor signer SHA-256: `c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8`, equal to the installed CipherOS platform certificate digest.
- The removable `/data/app` service ran as `u:r:platform_app:s0:c512,c768`; HOME remained separately isolated as `u:r:priv_app:s0:c512,c768`.
- Initial software evidence incorrectly labeled raw `180` as OUTWARD and raw `90` as privacy. Owner physical observation proved the opposite: `180` is CLOSED/privacy and `90` faces INWARD/toward the user. The dark Camera2 surface at `180` was a camera running behind the closed shutter and is not accepted as preview proof.
- Final instrumented behavior establishes `180` as the pre-open OUTWARD command and the post-Camera2 CLOSED command, with Camera2 lifecycle distinguishing the exposed outward camera from the mechanically closed state. INWARD uses raw `0`. Raw command readback alone cannot distinguish OUTWARD from CLOSED; Camera2 open/closed state is part of the authoritative product state.
- The normal Camera page and horizontal navigation are implemented, but real outward preview and final close require revalidation after deploying the corrected mapping.
- No `avc: denied` event occurred during open or close.
- Android build completed successfully with 257 tasks; standalone boundaries and embedded runtime package checks passed.

This closes only the missing normal Camera swipe and platform identity portions. The prior first-preview and privacy-return claims are withdrawn. Real OUTWARD preview, INWARD preview, CLOSED return, repeated/suspend cycles, QR scanning, and live-session Direct Handoff remain open until physically proved with the corrected state machine.

### Close-order correction and replacement evidence

Follow-up physical review identified why Camera appeared closed on entry and faced the user after exit. The orientation attribute echoes commands; it is not a mechanical-arrival sensor. Camera2 shutdown is also asynchronous. The first implementation called `CameraDevice.close()` and immediately commanded HOME, after which the camera stack completed shutdown and wrote `90`, overriding HOME.

The corrected ownership order is now:

```text
leave Camera / error / teardown
  -> stop preview requests
  -> close capture session, CameraDevice, and ImageReader
  -> wait for CameraDevice.StateCallback.onClosed
  -> bounded 1.5-second fallback only if onClosed is absent
  -> command CLOSED raw 180
  -> never reopen Camera2 during the return
```

The motor service is versioned `2 / 1.1-r1-physical-map`, logs every named-to-raw resolution, starts by requesting CLOSED, and has executable unit tests for all three mappings and the CLOSED waypoint required between exposed directions.

Replacement physical artifacts:

- HOME SHA-256: `d1ad88f18c4ca602a67e76579bdd68cf8defbfd218c12d0f83564757894c86ff`.
- Platform-signed motor service SHA-256: `dbdd47f1dccbd5935a4e82404a1ce483d5a9e3554b6052a3d49d957b5e0cc9a7`.
- Open trace: `named=OUTWARD raw=0`, Camera2 ID `0` opened, and a real outward scene rendered; the camera stack's eventual command state was `180`.
- Close trace: Camera2 ID `0` disconnected at `15:30:06.486`; only afterward, at `15:30:07.994`, the service logged `named=HOME raw=180`.
- Final state remained `180`; the former post-close rotation to `90` did not recur.

The earlier HOME/motor hashes in this document are rejected evidence and must not be redeployed.

### Orientation controls and no-sweep open correction

The intermediate correction incorrectly commanded raw `0` before opening Camera2 ID `0`. That caused a visible CLOSED -> toward-user -> outward sweep. It is rejected.

The deployed final open path commands/stays at raw `180`, then opens Camera2 ID `0`. Physical evidence recorded only `OUTWARD raw=180` before Camera2 connected; there was no preliminary `0` or `90` command. The real preview rendered with two in-page controls, `Toward you` and `Outward`, with Outward selected by default. Selecting a different facing closes Camera2 first, moves only after `onClosed`, and reopens the Camera2 lens matching the selected named direction.

Final artifacts for this correction:

- HOME SHA-256: `023112d233cdc26d2253804dd7529c069bd2f3960fdeacc7a9110b2a2729099e`.
- Platform-signed motor service SHA-256: `102cea3aa4d853a29d889ad8835feed991482e560b892280608cf86fb68c9c29`.
- Open: `OUTWARD raw=180` at `15:34:44.017`; Camera2 ID `0` connected at `15:34:46.073`.
- Close: Camera2 disconnected at `15:34:51.466`; `HOME raw=180` followed at `15:34:52.973`; final command state remained `180`.

## Implemented motor boundary

The clean repository now contains `android/core/motor` and the separate privileged `android/system/motor-service` as explicit Gradle modules. The application can discover only the named service; raw sysfs positions remain inside the privileged package. The service retains serialized movement, the privacy waypoint, reported-position confirmation, bounded failure, and privacy return. Its caller check corrects the donor mismatch by accepting production or engineering ReSono package names only when the pinned signing-certificate digest matches.

This source integration does not claim physical motor success. The hardware service must be built, installed in its privileged image location, granted the required SELinux/sysfs authority, and physically prove all three named states before Camera2 may open.

## Implemented Camera2 producer boundary

`android/feature/camera` now owns a non-visual `Camera2Producer` and immutable `CapturedImage`. The producer accepts only an already-confirmed named motor position, selects the matching lens, configures an aspect-filling `TextureView` transform without the donor's former doubled 90-degree rotation, emits JPEG bytes to its listener, and deterministically closes its capture session, device, reader, and thread. It cannot move the motor, navigate, render product controls, store files, call the runtime, or access Voice.

The application now declares Camera permission/capability and depends on the module, but no Camera surface is exposed yet. The next connected unit owns motor-confirmed page lifecycle and the capture/review state; it may expose UI only when wired to this real producer.
