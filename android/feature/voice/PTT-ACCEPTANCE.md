# Realtime push-to-talk acceptance

## Implementation boundaries

- `VoiceSessionService` owns the application-context controller and foreground microphone/media service lifetime. Views only render and forward user input.
- `SideButtonGesture` classifies the first 200 ms as a local candidate. A tap discards candidate audio; a hold promotes it without directly stopping output.
- `NativeVoicePeer` captures 24 kHz mono PCM16 with the pinned WebRTC ADM. A receive-only RTP transceiver carries speaker audio. PCM appends and commits use the same ordered data channel, avoiding a cross-channel release barrier.
- `RealtimeAudioInput` bounds candidate and confirmed PCM plus the conservative data-channel backlog allowance to 1,440,000 bytes. A closed gate rejects later frames. PCM never passes through Python or MCP.
- Server VAD stays enabled with automatic response creation off and speech interruption on. Input, response, and cancellation coordinators handle commit races, valid speech, response IDs, and originating round tokens.
- Connection and stalled transmission have 30-second limits. Processing has a two-minute watchdog; valid speech and playback suspend the idle timer. Idle disconnection waits ten minutes after the last active round/playback.
- Losing the input window releases a physical hold without stopping playback or the session. It prevents a missing key-up from leaving PTT recording active. Continuous input remains active.
- Session reconnection uses the existing summary and approved-memory context builder. There is no full audio-session resumption or automatic replay after a failed session.

## Host validation

Use the JDK/SDK and commands in `BUILDING.md`. The feature's Gradle tests cover gesture boundaries, bounded audio queues, silence, VAD/manual commit races, cancelled rounds, playback ordering, tool queue generations, and timeout transitions. Python provider assertions are in `runtime/tests/test_realtime_turn_detection.py`.

The tested Android dependency is `io.github.webrtc-sdk:android:144.7559.09`. Its capture callback executes before native software audio processing. A passing host build does not establish hardware echo cancellation quality or live-provider interoperability.

On 2026-09-09, the Android suite passed 118 tests (86 Voice tests), with no failures, errors, or skips. The three provider payload tests also passed. The final APK build, standalone boundary check, embedded-runtime check, and signature verification passed using an isolated macOS JDK 17 / Gradle 9.5 / Android 36 toolchain with the authoritative Gradle tasks. The APK has version code 36 and uses a temporary local debug signing key; it was not installed on a device.

## Shared-signing build and device upgrade

The [GitHub Actions build](https://github.com/ReSono-Labs/JackRabbit-OS/actions/runs/34302564943) for commit `2e1bbb6f21330191d99bbfdafe567cd843e85edb` passed the authoritative Linux build, Android tests, and package boundary checks. Its downloaded APK was independently verified before installation:

- Package: `com.resonolabs.voice.engineering`, version code 36, version name `0.4.29-Carrot1-debug`.
- Signing certificate SHA256: `a3390000a4b6c8bf43774cc235bd967e4c80a9dae30c0e8714c79c01a9b9836a`, matching the R1's installed v35.
- APK SHA256: `261cecb42841a9ea912e9bd5401f130e0c720a93e2faf27abbeec660c164b9c9`.

On 2026-09-09, `adb install -r` succeeded on the connected Rabbit R1 (Android 36). The package UID, first-install time, data directory, and credential/device-encrypted data inodes were unchanged; existing camera and microphone grants were retained. The new foreground microphone/media playback permissions were granted. On launch, the screen showed `Continuous: Off` and `MIC: CLOSED`; AppOps reported no running recording and the current recording configuration was empty. The runtime service was active and the Voice session service was absent, as expected for disconnected standby.

An initial ADB-injected three-second `KEYCODE_DPAD_CENTER` hold with the default `UNKNOWN` input source did not start Voice. Repeating the same key and duration with explicit `keyboard` source did start it: the screen showed `MIC: OPEN` / `Release to send`, AppOps reported recording, and the Voice foreground service started. After release, the UI showed `MIC: CLOSED` and the same service remained. The device was awake with keyguard showing, occluded, non-secure, and input-restricted; the source comparison does not establish the exact system interception path or the physical side button's final key mapping.

The configured real provider accepted the WebRTC answer, ICE reached `CONNECTED` / `COMPLETED`, and the data channel opened. In the connected PTT state, AppOps no longer reported running capture and the retained recorder configuration was explicitly inactive. Hardware AEC and NS both reported active and available. Connection initialization briefly started another recorder after release (the final AppOps duration was 207 ms), so these samples do not establish instantaneous hardware shutdown or the 50 ms input-gating target. Echo quality and actual speech delivery still require physical testing.

The following checks used ADB `keyboard` input and system recording state, not a physical button or an acoustic latency measurement:

- A 100 ms tap retained the same Voice service and left recording inactive. This tap did not establish audible cancellation during playback.
- Tapping `Continuous` enabled recording: the screen showed `MIC: OPEN`, AppOps was running, and the recorder was active.
- A 500 ms key hold and release returned to `Continuous: Off` / `MIC: CLOSED`, with AppOps no longer running and the recorder inactive; the same Voice service remained.
- A subsequent one-second silence check was invalid because the foreground had changed to Android Settings. Automated input stopped without changing that page. The Voice service remained in the background with recording inactive. User/environment input during the continuous-mode check also prevented using initial connection time as an idle-timeout baseline.

Physical side-button acceptance subsequently failed: the user confirmed that a
short press turns the display off and a long press opens the power menu.
InputReader identifies the keypad as `mtk-kpd`, using `Generic.kl` with scan code
116 mapped to `POWER`; KeyGestureController recorded its power-toggle gesture.
The APK's `DPAD_CENTER`/`ENTER` routing therefore does not receive the physical
side button. This is a system input mapping defect, not a signing failure.

The prepared [device-specific key layout](../../core/input/device/README.md)
retains volume-down and maps only that keypad's side button to `DPAD_CENTER`
with `WAKE`. The actual framework parser supports this flag. The alternative
modifier-remapping API was ruled out because the exact native implementation
filters for alphabetic keyboards, which excludes `mtk-kpd`. Following explicit
user authorization on 2026-09-09, the layout was installed at
`/data/system/devices/keylayout/mtk-kpd.kl` with its reviewed SHA256,
system:system ownership, mode0644, and the `system_data_file` label. SELinux
remained Enforcing and the original `Generic.kl` was unchanged. This correction
does not rebuild or replace the shared-signed v36 APK. After one restart,
InputReader confirmed that `mtk-kpd` selected this exact device-specific path,
and MainActivity returned to the foreground. Real physical events showed
device3, scan116, `DPAD_CENTER` DOWN/repeat/UP. The user confirmed that the first
press while disconnected produced a successful spoken turn, but subsequent
holds received no answer. Recording was inactive after release, with the same
Voice service retained. This is a failed multi-turn acceptance result requiring
runtime investigation; it does not invalidate the verified physical key route.
Audible interruption, wake behavior, and the ten-minute idle deadline remain
unverified on the device.

Diagnostic v37 was then built from `b5a048fa42cc0a3e71784212c95944e40bde1acc`
by [GitHub Actions](https://github.com/ReSono-Labs/JackRabbit-OS/actions/runs/34307108235).
It passed the same 118 Android tests and build/package checks. Its APK SHA256 is
`62465b634bfd4d4bb1e973d5e76b47833f684be16fd63dde774ba9208ad64687` and its
certificate matches the shared signing key above. A data-preserving upgrade
succeeded with UID, first-install time, CE/DE data inodes, and the selected
physical key layout unchanged. The added logs contain only per-press aggregate
frame/byte/peak/stale-frame counts, event types, and coordinator state counts.
This build adds evidence collection without a speculative multi-turn fix.

## Required physical and live-service checks

All checks below remain pending until performed on an R1 with the user's configured provider. Do not infer acceptance from mocked or host events.

| Scenario | Required observation |
|---|---|
| Cold start, immediately hold and speak | Press feedback appears promptly; recorder opening is truthful; earliest captured word reaches the provider after connection |
| Release before connection completes | Confirmed PCM is submitted in order; late connection never reopens the microphone |
| Hold, pause, continue, release | VAD may answer during a pause; each committed spoken segment is answered once; no final word is lost |
| Tap during generation or playback | Candidate noise is discarded, local audio stops promptly, old deltas/tools never restart the answer |
| Tap, then start a new question | New response plays normally without reviving cancelled audio or tool continuations |
| Hold without speaking | No answer; ambient speech after release is neither captured nor uploaded |
| Continuous to physical PTT | Same session remains; release closes input; output continues independently |
| Loud R1 speaker during a hold | Platform AEC/NS state is logged; speaker echo does not become a false user interruption |
| Network interruption and recovery | Brief transport recovery preserves queued authorized input; sustained stall fails within the bound and accurately reports possible partial delivery |
| Lock, focus loss, Activity recreation | Playback/session survive; lost physical key-up cannot leave capture open; reopening reflects the current state |
| Long reply, then no interaction | Reply finishes; disconnect occurs ten idle minutes later; silent presses and polling do not reset the timer |
| Tool result after cancellation/reconnect | Result cannot speak under a new round or release a new session's tool queue; independent background jobs remain available in Runs |
| End during initial connection | A late successful runtime call is finalized without reopening the peer |
| Camera/QR | Existing capture and handoff remain usable; no new side-button or double-tap camera shortcut |

Measure press feedback and release gating against the 50 ms target, and short-tap local stop against the 100 ms target. Test every Realtime model currently offered by the configured access path; the catalog alone is not a compatibility result.

## Visual references

The old Rabbit R1 listening/idle Lottie assets were found in the third-party [Pinball3D backup](https://github.com/Pinball3D/Rabbit-R1/tree/main/original%20r1/smali/assets/flutter_assets/assets/lottie). This implementation keeps native Canvas icons and the existing JackRabbit theme; it adds no downloaded Rabbit asset or animation dependency.
