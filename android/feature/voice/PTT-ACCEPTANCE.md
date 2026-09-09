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

An ADB-injected three-second `KEYCODE_DPAD_CENTER` hold did not start a Voice session. InputDispatcher recorded the injected events, the application remained focused and running, and no recording or Voice service started. The device was awake with keyguard showing, occluded, non-secure, and input-restricted. These observations do not establish why the injected input was ineffective or whether the physical side button has the same result. No subsequent continuous-mode or live-speech checks were claimed; physical input confirmation is required before completing the matrix below.

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
