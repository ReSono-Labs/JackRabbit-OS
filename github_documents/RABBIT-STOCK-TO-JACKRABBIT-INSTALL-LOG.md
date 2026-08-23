# Rabbit Stock to Current JackRabbit Installation Log

**Date:** 2026-08-22  
**Purpose:** Exact physical evidence for the stock-R1-to-current-JackRabbit installer flow  
**Device product:** `k65v1_64_bsp`  
**Device serial:** `919109A5P1600502814D`  
**Starting state:** Rabbit OS `v0.8.293`, bootloader FASTBOOT, slot `a`, unlocked  
**Ending transfer state:** All required image writes completed and reboot returned success  
**Physical boot acceptance:** Passed by owner — “it looks good”

## Current product selected for this installation

The current Android product source under `android/`, `runtime/`, `web/`, and
`tests/` had no uncommitted differences from `HEAD` at installation time. The
repository did contain legitimate uncommitted installer and documentation work;
those changes remain part of the working project but do not change the embedded
R1 product APK.

The current APK build output and the APK preserved immediately before the stock
transition were byte-identical:

| Artifact | SHA-256 |
|---|---|
| `android/app/build/outputs/apk/debug/app-debug.apk` | `34ab6a5d73194d58a38ea9da408a1fbd82af1a9c0e821afbbd991bad8299e8f9` |
| `artifacts/install-readiness/2026-08-22-pre-stock/packages/com.resonolabs.voice.engineering.apk` | `34ab6a5d73194d58a38ea9da408a1fbd82af1a9c0e821afbbd991bad8299e8f9` |
| Preserved platform-signed `com.resonolabs.hardware.apk` | `102cea3aa4d853a29d889ad8835feed991482e560b892280608cf86fb68c9c29` |

The HOME APK is version code `29`, version
`0.4.24-openai-settings-controls-debug`. The flashed current system image embeds
that HOME APK and the preserved platform-signed motor-service APK.

## Exact image inventory used

| Function | Repository path | SHA-256 |
|---|---|---|
| Stock boot | `image/baseline/rabbit-0.8.293/official/boot.img` | `0480ffab24e208ca20e761ebc07c15c0992ee3c91a3f55377731fdec532ae30f` |
| Stock super reset | `image/baseline/rabbit-0.8.293/official/super.img` | `d723922e8b0308c1c2363da513592a44cb20c21ed4023e55f05f3a0b8578b7a2` |
| Stock VBMeta | `image/baseline/rabbit-0.8.293/official/vbmeta.img` | `91fabaff6e5d61d7dbab02f181c36d4f9ab3aff9f833b92a6ddec92bf43dc6dc` |
| Stock system VBMeta | `image/baseline/rabbit-0.8.293/official/vbmeta_system.img` | `10d7c932c1b2974efcb35288e2ceea9d35aff2480a19a4882d86f0e2a245d373` |
| Stock vendor VBMeta | `image/baseline/rabbit-0.8.293/official/vbmeta_vendor.img` | `5b23d1e31f4b8b196b988ae1490a95fba649f8403dd2b11309efa612ac41ddfc` |
| Current JackRabbit system | `image/candidates/current-product-v0.1/system.img` | `2cc98b074b915ffb4346ee0d3226e06d56e2b29c6a3dc98f2571ca0915e85434` |
| Current JackRabbit product | `image/candidates/current-product-v0.1/product.img` | `eac03525513be044b804c0a33711eda75922d0fc25ef815ad4f2efa6168e1c41` |
| CipherOS system extensions | `image/extracted/system_ext.img` | `db08515c52d0e679d1926bdc11719935efd3bac581e683e07a15bfe49f4f1dd9` |
| CipherOS vendor | `image/extracted/vendor.img` | `6ea508648edce2e15debddacf2c161a46553c21c6a64de43f90b2eadfae5eba6` |
| CipherOS VBMeta | `image/extracted/vbmeta.img` | `36fedb0f1d79bbf9bebe509320296346667ced09c1f46c0bfb8719b52c18c1f2` |
| CipherOS system VBMeta | `image/extracted/vbmeta_system.img` | `89333175d7f1fa9c368c87e39015213726f2e4f469198f9c8a44a2ceafb4245e` |
| CipherOS vendor VBMeta | `image/extracted/vbmeta_vendor.img` | `4bf39aadc797948e0cceb1332220f7822d5801b21edae9ad44bd16692afa1158` |

## Verified starting gate

Native fastboot reported:

```text
product: k65v1_64_bsp
current-slot: a
unlocked: yes
is-userspace: no
max-download-size: 0x8000000
```

No partition write began before these values passed.

## Exact successful installation sequence

### 1. Bootloader FASTBOOT foundation

The stock `boot.img` was written to `boot_a` and `boot_b`. Stock `vbmeta`,
`vbmeta_system`, and `vbmeta_vendor` were written to both slots using native
fastboot's `--disable-verity --disable-verification` handling. Every write
returned `OKAY`.

The device was then sent to fastbootd with:

```text
fastboot reboot fastboot
```

### 2. Fastbootd USB transition

Bootloader FASTBOOT enumerated as MediaTek `0e8d:201c`. Fastbootd re-enumerated
as Google `18d1:4ee0`.

On this Debian host, the fastbootd USB node appeared as `root:root` mode `0664`.
Native fastboot reported:

```text
no permissions (missing udev rules? user is in the plugdev group)
```

The run continued only after a PolicyKit authentication prompt temporarily
changed that single live USB node to mode `0666`. This is installer evidence:

- Linux setup must provide a narrow udev rule for `18d1:4ee0`, or the guided
  CLI must detect this exact denial and prompt for a bounded authorization step.
- The installer must re-probe product, slot, unlock state, and `is-userspace`
  after the mode change.

After permission correction, fastbootd reported the same serial and:

```text
product: k65v1_64_bsp
current-slot: a
unlocked: yes
is-userspace: yes
```

### 3. Super reset and observed blank screen

The verified stock `super.img` was flashed in fastbootd. A first host command
runner invocation ended after sparse chunk 3 of 9. Fastbootd remained available.
The correct recovery was to restart the same complete `super` flash from the
beginning; no different image or partition operation was selected.

During the successful retry, the R1 display went blank after sparse chunk 6 had
started and before the host reported chunks 7 through 9. USB remained connected,
the transfer continued, all 9 chunks returned `OKAY`, and fastboot exited 0:

```text
Sending sparse 'super' 9/9 (32204 KB) OKAY
Writing 'super' OKAY
Finished. Total time: 103.945s
```

Required user-facing installer prompt:

> The R1 screen may go blank while `super` is being written. Do not unplug the
> cable. Follow the installer transfer status; a blank display by itself is not
> a failure.

Required recovery behavior:

- If the host operation ends before all sparse chunks are acknowledged, do not
  advance.
- Reconnect to fastbootd, reverify the same device and signed release, and
  restart the complete `super` operation from its beginning.

### 4. Logical partition creation and writes

After the stock super reset, `partition-size:system_ext_a` correctly failed with
`Could not open partition`. The required CipherOS logical partition was created:

```text
fastboot create-logical-partition system_ext_a 559304704
```

The following writes then completed with exit code 0:

```text
system_a     <- current JackRabbit system.img       (6 sparse chunks)
system_ext_a <- CipherOS system_ext.img              (3 sparse chunks)
product_a    <- current JackRabbit product.img       (2 sparse chunks)
vendor_a     <- CipherOS vendor.img                  (2 sparse chunks)
```

### 5. Bootloader finalization

The R1 returned to bootloader FASTBOOT with `fastboot reboot bootloader`. The
same product, slot, serial, and unlock state were reverified. The final CipherOS
`vbmeta_a`, `vbmeta_system_a`, and `vbmeta_vendor_a` images were written with
verification disabled. Every write returned `OKAY`.

The install then completed:

```text
fastboot erase userdata
fastboot set_active a
fastboot reboot
```

All three commands returned `OKAY`; the final command process exited 0.

## Installer behavior derived from this run

The normal stock-to-JackRabbit flow must be one state machine:

1. Guide Rabbit developer-mode approval and Rabbithole unlock authorization.
2. Enter bootloader FASTBOOT through the reviewed Web Serial `FASTBOOT` command.
3. Select the R1 through WebUSB and read the starting gate.
4. If locked, warn that unlock erases data, run the authorized unlock sequence,
   re-enumerate, re-read the gate, and rejoin the same flow.
5. Write the bootloader-stage foundation.
6. Reboot to fastbootd and explicitly handle its different USB identity and host
   permission requirements.
7. Write stock super, create `system_ext_a`, and write the four final logical
   images.
8. Return to bootloader FASTBOOT, write final prepared VBMeta bytes, erase
   userdata, select slot A, and reboot.
9. Distinguish successful transfer from successful physical Android boot.

The release package must contain the exact functions represented above. It may
be delivered as one user-selected/downloaded release bundle even though Android
requires multiple partition image files internally.

## Physical acceptance

The owner confirmed after first boot that the installed product “looks good.”
This accepts the visible JackRabbit boot/HOME result for this installation.
Machine-verifiable post-boot package/runtime checks may still be appended when
the device exposes ADB, but they do not replace the owner's physical result.

The run now proves successful image transfer, reboot, and owner-accepted visible
first boot.

## 2026-08-23 guided CLI acceptance correction

A physical guided-CLI run completed operations 1 through 10, including the
complete stock `super` write, then stopped before any JackRabbit/CipherOS
logical-partition write with:

```text
JR-CLI-SYSTEM-EXT: system_ext_a has an unexpected existing layout
```

The R1 remained safely connected in fastbootd. A read-only reproduction showed
that Google Platform Tools printed the expected remote response
`FAILED (remote: 'Could not open partition')` for the absent `system_ext_a`,
but returned host process status 0. The first CLI parser trusted only process
status, so it misclassified that expected absent-partition state.

The shared Linux, macOS, and Windows CLI engine now treats either a failed
process status or a `FAILED` protocol line as a native-fastboot failure. The
exact expected `Could not open partition` response is then handled only at the
post-super `system_ext_a` probe, where it creates the reviewed 559,304,704-byte
logical partition. Any other remote failure remains fail-closed. Unit tests
cover the exit-zero/`FAILED` behavior, expected missing partition, accepted
partition size, and unexpected output. The corrected installer restarts the
fixed route from bootloader FASTBOOT; it does not try to infer or resume a
partially completed destructive sequence.
