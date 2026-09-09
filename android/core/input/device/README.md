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
This device-specific layout has not yet been deployed. Physical press/release,
screen-off wake behavior, camera behavior, and recovery controls must be checked
after installation. The R1's D-pad wake resource is enabled, but the system's
noninteractive path can consume the press used to wake the display; do not
promise that the first hold from screen-off also starts recording before
physical verification. No PMIC reset behavior is inferred from an Android key map.
