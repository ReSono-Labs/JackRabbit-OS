# Realtime push-to-talk acceptance

## Implementation boundaries

- `VoiceSessionService` owns the application-context controller and foreground microphone/media service lifetime. Views only render and forward user input.
- `SideButtonGesture` classifies the first 200 ms as a local candidate. A tap discards candidate audio; a hold promotes it without directly stopping output.
- `NativeVoicePeer` captures 24 kHz mono PCM16 with the pinned WebRTC ADM. A receive-only RTP transceiver carries speaker audio. PCM appends and commits use the same ordered data channel, avoiding a cross-channel release barrier.
- `RealtimeAudioInput` bounds candidate and confirmed PCM plus the conservative data-channel backlog allowance to 1,440,000 bytes. A closed gate rejects later frames. PCM never passes through Python or MCP.
- Each authorized-audio END lazily emits 1500 ms of digital silence before the existing commit path, covering the configured 1200 ms server-VAD stop window. Blocks are at most 12,000 PCM bytes and use the same ordered append path and byte timeline. No microphone capture or wall-clock sleep produces this tail. Pending END markers reserve 16 KiB when admitting later captured PCM; the virtual tails are counters, not retained 72 KiB audio arrays. The 30-second limit concerns captured PCM, not the summed sample duration of generated tails, and is not an absolute Java heap limit.
- Encoded audio appends use a bounded 128 KiB transport window. Generated tails are additionally limited by the capture budget remaining after queued PCM, so a nearly full later capture cannot lose its reserved END workspace. Successful send admission precedes removal from the audio queue.
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

The user's v37 reproduction confirmed the multi-turn failure. Subsequent holds
captured and transmitted nonzero PCM (including 188,640 and 129,120 bytes), with
no stale frames. Both manual commits succeeded, but no new `speech_started`
arrived, so the client classified the items as silent, deleted them, and returned
to standby. The original VAD interval stopped only when a later captured pause
supplied enough silence; one new turn then worked before manual commit caused
the same pattern again. Manual commit and microphone closure do not themselves
terminate that provider VAD interval.

The v38 correction inserts the digital-silence boundary described above. The
regression uses the real audio queue and input/response coordinators with only
the observed server VAD behavior modeled: manual commit clears buffered bytes
without ending VAD. The old implementation answered only the first of three
turns; the corrected implementation answers each turn once, including delayed
acknowledgements and cancellation followed by a new hold. The local APK build
and boundary checks passed. The final Voice suite passed 95 tests, including
15 audio-queue tests and four multi-turn integration tests.

The shared-signed v38 APK was built from
`e1e6e32a64c0bdc2c00ce38ccd6ed342454fcc7c` by
[GitHub Actions](https://github.com/ReSono-Labs/JackRabbit-OS/actions/runs/34311518991).
Its APK SHA256 is
`21c0e20d67973213d1725ff6c715daf8a4af81d879217a56ef28d89371bdbcab`, and its
certificate matches the shared signing key above. A data-preserving upgrade
succeeded with UID, first-install time, CE/DE data inodes, and the selected
physical key layout unchanged. Physical v38 multi-turn acceptance remains
pending.

## System microphone indicator layout

An R1 screenshot showed the system microphone indicator at the top-right of
the screen, overlapping the device-settings icon. A transient status bar also
overlapped the Voice title. The app drew its navigation from window coordinate
zero while requesting edge-to-edge fullscreen, without reserving system space.
The indicator appearing during capture and disappearing afterwards is expected;
its overlap with app controls is not.

The v39 layout reserves the system's stable top inset and maximum privacy
indicator bounds for the product pages. Header and page content share the same
vertical scale, with matching touch-coordinate transforms. Visibility changes
do not move the content. Camera and creation-import fullscreen layouts retain
their existing geometry. The app Java compilation, APK build and both package
boundary checks passed for v39; the 127 existing Android test results remained
up to date with zero failures. The R1 reports a 48-pixel stable top inset even
with its status bar hidden. At 480 by 640 pixels, the new menu drawing occupies
approximately y73–106, below the system indicator's maximum y48 boundary.

The shared-signed v39 APK was built from
`f2f4f13a455cb62695d44b2145c183a389e52631` by
[GitHub Actions](https://github.com/ReSono-Labs/JackRabbit-OS/actions/runs/34312653562).
Its APK SHA256 is
`a36594ba53b6e63dfb74b1b8ca3977c29b6eba5ef675782117a74db23d412ca9`.
The matching certificate and package/version were verified before a successful
data-preserving upgrade. UID, first-install time, CE/DE data inodes and the
device key layout remained unchanged. The post-install R1 screenshot confirmed
that the menu is below the system indicator's maximum bounds, with
`Continuous: Off` and `MIC: CLOSED`. This is idle-layout evidence; recording-time
visual/touch acceptance and multi-turn audible acceptance remain pending.

## v39 follow-up evidence and v40 correction

The user subsequently accepted physical hold-to-speak and release-to-close, but
reported delayed interruption during a reply, failed web search, and an
unacceptable permanent top gap. Four consecutive voiced input commits and
responses used the already-connected peer. The persisted conversation retained
earlier context; there was no per-press session reset in this reproduction.
The configured access path was subscription with `gpt-realtime-2.1`, following
the unchanged canonical model resolver. No server model acknowledgement was
logged by v39, so configuration alone is not direct evidence of the model
reported by the server.

During one reply, the interval from physical key-down to the server's
`speech_started` and output clear was 3.815 seconds. Release left 77,280 bytes
of captured PCM queued, and the input END took another 4.015 seconds. The
former 16 KiB send window required a 16,047-byte encoded silence message to
wait until almost all prior data drained. This motivates v40's larger bounded
window; it does not prove the network or JNI will sustain the required rate.
Three new transport regressions fail under the old policy and pass under the
new policy. The full Voice suite passes 98 tests. New per-input diagnostics
record maximum queue age, synchronous send duration and buffered bytes.
Session acknowledgements log only the reported model, tool count and presence
of `web_search`; absent fields are explicitly reported as unknown.

Two real `web_search` calls failed inside the existing search executor, and
their error outputs triggered Realtime continuations. Tool registration,
audience and MCP dispatch remained intact. The legacy exception wrapper hid
the underlying cause. V40 adds bounded failure classifications without query,
answer, exception-message or credential logging; this is diagnostic work,
not yet a verified repair of the live search failure.

V40 removes the permanent top inset and restores compact fullscreen geometry.
On this R1 build, SystemUI privacy animations force status bars visible despite
the app's fullscreen request. A separately reviewed device-wide configuration
can suppress this scheduler's privacy and charging animations while retaining
permissions and privacy records. No such setting is applied without explicit
authorization of its device-wide scope.

The shared-signing [v40 build](https://github.com/ReSono-Labs/JackRabbit-OS/actions/runs/34316139425)
at `77827f5c72a28786ca4e1ef93431118167c56f4a` passed and was installed with
`adb install -r`. Package version 40, the existing shared signer, UID, first
installation time, data-directory inodes and physical key layout were verified.
Both new search diagnostic markers are present in the APK's embedded Python
bytecode. The authoritative host build passes its boundary checks; Android test
results total 130 with zero failures, and 15 focused search-diagnostic tests pass.

After explicit authorization of the device-wide scope, this R1's
`privacy/enable_immersive_indicator` was set from absent to `false` and read back
at 2026-09-09 13:49 Beijing time. The `camera_mic_icons_enabled` key remains
absent and SystemUI still reports `micCameraAvailable: true`. Restoration deletes
only `privacy/enable_immersive_indicator` to return to its original absent state;
the APK does not apply this device setting. A post-install screenshot confirms
compact fullscreen standby with `MIC: CLOSED`, and AppOps reports no active
recording.

Two subsequent physical holds were observed at 13:53:09 and 13:53:23. Each
recording screenshot shows `MIC: OPEN`, with AppOps and the recording monitor
both active and unsilenced. Screenshots taken five seconds after each release
show `MIC: CLOSED` and inactive capture. All four samples retain compact
fullscreen geometry without a system status bar, privacy capsule or dot;
SystemUI's animation scheduler reports Idle with no persistent dot.

The same live session acknowledges `gpt-realtime-2.1`, 30 tools and
`webSearch=true`, directly confirming the configured Realtime model and tool
registration. Two search failures are now classified as
`phase=validate reason=missing_citations`: the executor obtained nonempty
output but extracted no URL citations. The generic "rejected" wrapper is
misleading for this local validation failure. Whether the response omitted
citations or supplied them only in stream events requires additional evidence.

Across four warm inputs, maximum real-PCM queue ages were 41, 2662, 43 and
42 milliseconds; tail transmission still stalled in some rounds. The last
release reached local input END in 61 milliseconds, but server speech-stop
arrived another 2.145 seconds later. Three observed interruptions cleared
server playback 1–2 milliseconds after `speech_started`. Key-down to that
event also includes the user's unknown speech onset, so it is not a pure
transport latency measurement. A physical tap produced server output clear
228 milliseconds after key-up; local audible stop latency is not measured.
These observations establish multi-turn progress but do not close the
remaining latency or live-search acceptance checks.

## v41 follow-up

When the cached transport water level rejects an append, the native owner
thread now refreshes the actual data-channel buffered amount and checks the
same budget again. Capture still reads only the volatile snapshot; neither
the 128 KiB window nor VAD policy changes. A separate per-input `PTT transport`
record reports cache overestimation, refresh duration and blocked-check timing.
`blockedChecks` counts cache rejections, including ones released by a fresh
read; the retry gap only covers consecutive blocked checks, not end-to-end
voice latency. Live measurements are needed to establish whether stale cache,
actual transport backlog or main-thread scheduling caused the observed stalls.

Search validation errors now preserve their accurate no-answer/no-citation
classification. A missing-citation failure additionally logs fixed integer
counts of search calls, terminal annotations and streamed annotations. No
query, answer, source URL or credentials are logged. A real-SDK mocked-stream
test demonstrates that completed item metadata can contain citations absent
from terminal response output; that is a diagnostic fixture, not yet evidence
of this device's cause. The search model, request parameters and success
conditions remain unchanged pending the next live result.

The authoritative v41 build passed with fresh Native/Controller compilation,
98 executed Voice tests and 130 total Android tests with no failures. The 17
focused search tests pass. Independent review found no blocking issues in
the audio or search changes. The [shared-signing v41 build](https://github.com/ReSono-Labs/JackRabbit-OS/actions/runs/34317678704)
at `62ff1cbf812f4e4ccbf8e4f364f83da23e77834f` was installed with data, package
identity and physical key layout preserved. Embedded Python diagnostic markers
and the shared signing certificate were verified. The approved privacy setting
remains `false` and `camera_mic_icons_enabled` remains absent. V41 live-search
and transport measurements are pending; no new visual behavior was introduced.

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
