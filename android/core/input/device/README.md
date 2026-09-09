# Rabbit R1 physical side-button mapping

The R1 `mtk-kpd` keypad reports Linux scan code 116. On the inspected Android 36
device, it falls back to `Generic.kl`, which maps that code to Android `POWER`.
Android consumes it for screen-off and the power menu before JackRabbit can
handle it. Injecting `DPAD_CENTER` into the app does not test this physical path.

`mtk-kpd.kl` maps scan code 116 to `DPAD_CENTER`, the existing JackRabbit
push-to-talk input. `WAKE` is supported by the inspected R1's key-layout parser
and marks the press as a wake candidate. The keypad's other advertised key, scan code 114, retains
`VOLUME_DOWN`. This file is scoped to `mtk-kpd`; do not replace `Generic.kl` or
change other input-device layouts.

Android's [device-specific key-layout lookup](https://source.android.com/docs/core/interaction/input/key-layout-files)
supports `/data/system/devices/keylayout/mtk-kpd.kl` before the generic fallback.
For an installer image, the equivalent device-specific location is
`/system/usr/keylayout/mtk-kpd.kl`. This file is an OS configuration asset; the
APK build does not install it.

## Deployment boundary

Installing the layout changes this physical key throughout Android. It will
no longer provide the normal short-press screen-off or long-press power menu;
in other apps it behaves as a center/confirm key. Deployment requires an
explicitly authorized system configuration update and a restart to reload the
input device. It does not require wiping data or changing the shared APK key.

Before deployment, verify the connected R1, its actual input-device name and
advertised scan codes, the selected layout path, and whether a device-specific
layout already exists. Preserve any existing configuration and its metadata;
do not overwrite an unknown layout. Record the installed file hash and restore
the appropriate SELinux context. After restart, confirm InputReader selected
the new file and verify real physical DOWN/UP events and PTT behavior.

When the original device-specific file was absent, rollback consists of moving
the installed file out of the key-layout lookup path and restarting; Android
then uses its original generic mapping again. If a file previously existed,
restore that exact file instead. Do not delete or modify the system generic
layout, and do not change other key remappings.

## Validation status

The physical POWER failure and the incorrect original fallback are confirmed.
The inspected R1 also has a modifier-remapping API, but its native implementation
applies mappings only to alphabetic keyboards; it does not cover `mtk-kpd`.
On 2026-09-09, the user authorized installation and a device restart. The layout
was installed at `/data/system/devices/keylayout/mtk-kpd.kl`, with SHA256
`e21334b506a037d0949fe560738ee2970a6fd2bca019a4f39b90559c5f941c8b`,
system:system ownership, mode0644, and the `system_data_file` SELinux label.
SELinux remained Enforcing and the original `Generic.kl` hash was unchanged.
After one restart, InputReader confirmed that `mtk-kpd` selected this exact
device-specific path, and JackRabbit's MainActivity returned to the foreground.
Real physical events then showed device3, scan116, `DPAD_CENTER` DOWN/repeat/UP.
The user confirmed that the first PTT turn worked, but later holds received no
answer. Key routing is verified; multi-turn Voice acceptance is blocked by that
separate runtime failure. Diagnostic v37 subsequently traced that failure to
manual commit leaving server VAD active, causing later valid input to be treated
as silence. The Voice input boundary correction is tracked in the
[PTT acceptance record](../../../feature/voice/PTT-ACCEPTANCE.md); it requires an
APK update and does not change this verified device layout.

Screen-off wake behavior, camera behavior, and recovery controls must also be
checked. The R1's D-pad wake resource is enabled, but the system's
noninteractive path can consume the press used to wake the display; do not
promise that the first hold from screen-off also starts recording before
physical verification. No PMIC reset behavior is inferred from an Android key map.
