# JackRabbitOS to Rabbit R1 Stock Transition Log

**Document role:** Authoritative progress and execution record  
**Started:** 2026-08-22  
**Device:** Rabbit R1  
**Expected serial:** `919109A5P1600502814D`  
**Target stock release:** Rabbit OS `v0.8.293`  
**Current phase:** Host preparation complete; official browser-based stock transition not started

## Rules for this log

- Record every material preparation step, device command, response, decision, failure, retry, and physical observation.
- Add entries in chronological order. Do not rewrite earlier results to make later work appear cleaner.
- Clearly label planned actions separately from completed actions.
- Record exact file paths and SHA-256 values for every image or APK used.
- Record the device serial, Fastboot mode, product, slot, and unlock state before any write.
- Stop on any identity mismatch, hash mismatch, unexpected boot state, failed command, or unexplained result.
- Never claim a checkpoint passed without command output or owner-observed physical evidence.
- Use Rabbit's official browser-based stock-return flow without altering its stock partition sequence.
- The official tool automatically relocks the bootloader. Its browser flow does not provide an option to omit that operation.
- Stop after the stock base is physically proved. Do not complete Rabbithole account setup during this rehearsal.
- Do not erase or overwrite the preserved JackRabbit backups.
- Do not treat copied encrypted credential records as recoverable credentials after a userdata wipe.

## Transition objective

Return the physical R1 from the current JackRabbitOS/CipherOS-derived build to the official Rabbit OS `v0.8.293` stock baseline using the same supported browser flow available to an end user, while preserving enough verified host-side evidence to restore the current JackRabbit product later.

This document covers:

1. Preservation of the current JackRabbit build and runtime data.
2. Validation of the official Rabbit stock package.
3. Pre-flash device identity and safety gates.
4. The complete stock flash transcript.
5. Physical stock boot acceptance.
6. Any failures, deviations, and recovery actions.

## Starting state

### Last recorded device state

The last Android-side observations before this transition were:

- Serial: `919109A5P1600502814D`
- Product: `r1`
- Active slot: `_a`
- Android version: `16`
- Fingerprint: `rabbit/cipher_r1/r1:16/BP2A.250605.031.A2/eng.ubuntu:userdebug/test-keys`
- Installed HOME package: `com.resonolabs.voice.engineering`
- Installed HOME APK SHA-256 matched the preserved host copy.

Android reported locked/green properties, while earlier physical Fastboot evidence reported an unlocked bootloader. This conflict is unresolved until bootloader Fastboot is entered again. No write is permitted unless live Fastboot reports `unlocked: yes`.

### Current JackRabbit product backups

| Preserved item | Path | SHA-256 |
|---|---|---|
| Current ReSono HOME/runtime APK | `artifacts/install-readiness/2026-08-22-pre-stock/packages/com.resonolabs.voice.engineering.apk` | `34ab6a5d73194d58a38ea9da408a1fbd82af1a9c0e821afbbd991bad8299e8f9` |
| Current motor service APK | `artifacts/install-readiness/2026-08-22-pre-stock/packages/com.resonolabs.hardware.apk` | `102cea3aa4d853a29d889ad8835feed991482e560b892280608cf86fb68c9c29` |
| Full stopped device-protected runtime | `artifacts/install-readiness/2026-08-22-pre-stock/runtime/device-protected-runtime.tar` | `96b20d0c1fd4f4036c97e286471d1ce331846c415fb6895d681d3e1ce9f25149` |
| Full credential-protected app data | `artifacts/install-readiness/2026-08-22-pre-stock/runtime/credential-protected-app-data.tar` | `5ddbb6a2d3c2c1b0fe3e0e7e0832700cd335cddffc92fc21f886cbadaee728e0` |
| Restorable runtime without stale credential envelopes | `artifacts/install-readiness/2026-08-22-pre-stock/runtime/runtime-restorable-no-credentials.tar` | `c93784c5d0d6fed5f65d2e3dfd7cc389c56fa0751cc0d03f940a19f26b5d726e` |

The full runtime archive is the untouched rollback/forensic source. The restorable archive retains canonical data and workspace content but intentionally requires OpenAI, Mail, and authenticated Calendar reconnection after a wipe.

### Runtime backup validation

Completed on 2026-08-22:

- `PRAGMA quick_check`: `ok`
- `PRAGMA integrity_check`: `ok`
- Mail messages preserved: `659`
- Calendar events preserved: `1`
- Memory records preserved: `9`
- Background Agent runs preserved: `19`
- Background Agent run events preserved: `550`
- Session summaries preserved: `61`
- Transcript entries preserved: `605`
- Workspace catalog entries preserved: `8`
- Creation catalog records preserved: `2`
- Plugin catalog records preserved: `1`
- Skill catalog records preserved: `1`

## Official Rabbit stock input

### Downloaded package

- Release: Rabbit OS `v0.8.293`
- Source: `https://github.com/rabbit-hmi-oss/firmware/releases/download/v0.8.293/rabbit_OS_v0.8.293.zip`
- Local path: `image/baseline/rabbit-0.8.293/rabbit_OS_v0.8.293.zip`
- Size: `967477397` bytes
- SHA-256: `f6c28b221a91055ec5e44ab0ac0ee59c7e6b52fac12ad08f2bb23c8f0551c6c0`
- ZIP integrity: passed

### Extracted stock files

Directory:

`image/baseline/rabbit-0.8.293/official/`

The authoritative extracted-file manifest is:

`image/baseline/rabbit-0.8.293/official/SHA256SUMS`

Critical inputs include:

- `preloader_k65v1_64_bsp.bin`
- `vbmeta.img`
- `vbmeta_system.img`
- `vbmeta_vendor.img`
- `md1img.img`
- `spmfw.img`
- `scp.img`
- `sspm.img`
- `gz.img`
- `lk.img`
- `boot.img`
- `dtbo.img`
- `tee.img`
- `logo.bin`
- `super.img`
- `userdata.img`

Critical known hashes:

| File | SHA-256 |
|---|---|
| `boot.img` | `0480ffab24e208ca20e761ebc07c15c0992ee3c91a3f55377731fdec532ae30f` |
| `super.img` | `d723922e8b0308c1c2363da513592a44cb20c21ed4023e55f05f3a0b8578b7a2` |
| `userdata.img` | `9b06c8b4ff198d6fa1dc92bcbb2d085bdd65a8a33e1f8c08c258d1d07e2b0981` |
| `vbmeta.img` | `91fabaff6e5d61d7dbab02f181c36d4f9ab3aff9f833b92a6ddec92bf43dc6dc` |
| `vbmeta_system.img` | `10d7c932c1b2974efcb35288e2ceea9d35aff2480a19a4882d86f0e2a245d373` |
| `vbmeta_vendor.img` | `5b23d1e31f4b8b196b988ae1490a95fba649f8403dd2b11309efa612ac41ddfc` |

## Official stock sequence reviewed

Rabbit's official web flasher was reviewed from:

`https://rabbit-hmi-oss.github.io/flashing/js/stock-flash.js`

The browser Fastboot transport used by Rabbit's tool is based on kdrag0n's `fastboot.js`:

`https://github.com/kdrag0n/fastboot.js`

Keep these responsibilities distinct when producing the later user-facing documentation:

- Rabbit's flash tool owns the R1-specific user flow, partition sequence, firmware mapping, and final relock.
- `fastboot.js` supplies the browser/WebUSB Fastboot implementation used underneath that flow.
- Rabbit's official firmware release supplies the stock partition bytes.

Its stock sequence is:

1. Erase userdata.
2. Flash preloader to slots A and B.
3. Flash all three VBMeta images to slots A and B.
4. Flash modem and firmware partitions to slots A and B.
5. Flash LK, boot, DTBO, and TEE to slots A and B.
6. Flash logo.
7. Flash super.
8. Flash userdata.
9. Set active slot A.
10. Lock the bootloader.
11. Reboot.

For this controlled transition, the official sequence automatically runs through its final bootloader relock. Relocking is not an optional rehearsal choice in the official browser tool. This supersedes the earlier preparation assumption that relocking could be omitted. The later JackRabbit installer rehearsal must begin from the resulting real stock state and handle its own documented unlock entry conditions.

## User-facing stock return path

A JackRabbitOS user returns to Rabbit OS through Rabbit's official browser-based flashing tool:

1. Back up anything they want to keep. Returning to stock erases the R1.
2. Download and extract the official `rabbit_OS_v0.8.293.zip` firmware.
3. Open the [Rabbit R1 Flash Tool](https://rabbit-hmi-oss.github.io/flashing/) in Chrome or Edge.
4. Power off and disconnect the R1.
5. Click **Enter Fastboot Mode**.
6. Connect the R1 and quickly select **MT65xx Preloader** when the browser's USB device prompt appears.
7. Wait for `FASTBOOT` to appear on the R1.
8. Click **Select Device in Fastboot** and select the R1.
9. Click **Flash Stock ROM**.
10. Select the directory containing the extracted official stock firmware files.
11. Wait while the official tool wipes userdata, flashes the stock partitions, sets slot A, relocks the bootloader, and reboots.
12. A user permanently returning to Rabbit OS would complete normal Rabbit OS setup and reconnect the device to their Rabbithole account.

Rabbit documents this as the supported path for returning a modified R1 to Rabbit OS:

- `https://www.rabbit.tech/support/article/unlock-bootloader-rabbit-r1`
- `https://rabbit-hmi-oss.github.io/flashing/`

### Rehearsal-specific stopping point

This rehearsal performs steps 1 through 11. It deliberately skips step 12. We need the genuine stock software and bootloader base for the following JackRabbit installer test, but we do not need to enroll or reconnect the test device to a Rabbithole account.

## Completed progress log

### 2026-08-22: Current product preservation

**Status:** Completed

- Preserved the exact installed ReSono APK.
- Preserved the exact installed motor service APK.
- Captured a stopped device-protected runtime archive.
- Captured credential-protected application data as forensic evidence.
- Generated a separate post-wipe restore archive with device-sealed connection envelopes removed.
- Recorded SHA-256 values in `artifacts/install-readiness/2026-08-22-pre-stock/SHA256SUMS`.

### 2026-08-22: Runtime recovery audit

**Status:** Completed

- Extracted the runtime backup on the host only.
- Confirmed the canonical SQLite database passes both integrity checks.
- Inventoried preserved domain, memory, background-run, import, session, and workspace records.
- Confirmed copied credential envelopes cannot be treated as valid after an Android Keystore reset.
- Preserved the full original backup without modification.

### 2026-08-22: Stock package preparation

**Status:** Completed

- Downloaded the official Rabbit OS `v0.8.293` release package.
- Confirmed the release asset size and SHA-256.
- Confirmed ZIP integrity.
- Extracted the official images.
- Generated and retained an extracted-file SHA-256 manifest.
- Reviewed the official Rabbit web flasher partition order and its final relock behavior.

### 2026-08-22: Device mutation boundary

**Status:** Stopped as required

- No stock partition has been flashed.
- No Fastboot write has been issued.
- No userdata wipe has been issued.
- The bootloader has not been locked or unlocked during host preparation. The official stock transition is expected to relock it.
- The R1 has not been rebooted or otherwise changed as part of this preparation.

## Next checkpoint: live pre-flash gate

This checkpoint has not started and requires explicit owner authorization.

The first live interaction must be read-only and must record:

| Gate | Required result | Actual result |
|---|---|---|
| Connected devices | Exactly one Fastboot device | Not checked |
| Serial | `919109A5P1600502814D` | Not checked |
| Product | `k65v1_64_bsp` | Not checked |
| Fastboot mode | Bootloader Fastboot, not Fastbootd | Not checked |
| Unlock state before stock flash | `yes` | Not checked |
| Current slot | `a` | Not checked |

If any result differs, stop before writing anything.

## Planned stock execution record

Populate each row during the physical transition. Record the exact command and the meaningful response in the Notes column.

| Step | Operation | Status | Notes/evidence |
|---:|---|---|---|
| 1 | Validate every stock file against `official/SHA256SUMS` | Completed | Host manifest and ZIP integrity passed before device work |
| 2 | Enter bootloader Fastboot and pass all identity gates | Completed | Expected serial/product, unlocked `yes`, slot `a` |
| 3 | Erase userdata | Completed | Official tool reported progress `1/32` |
| 4 | Flash `preloader_a` | Completed | Official tool reported success |
| 5 | Flash `preloader_b` | Completed | Official tool reported success |
| 6 | Flash VBMeta family to both slots | Completed | Six VBMeta targets reported success |
| 7 | Flash modem and firmware family to both slots | Completed | Ten targets reported success |
| 8 | Flash LK, boot, DTBO, and TEE to both slots | Completed | Eight targets reported success |
| 9 | Flash logo | Completed | Official tool reported success |
| 10 | Flash super | Completed | `2110680916`-byte sparse image reported success |
| 11 | Flash official userdata image | Completed | Official tool reported success |
| 12 | Set active slot A | Completed | Official tool reported progress `31/32` |
| 13 | Official tool automatically relocks the bootloader | Completed | Official tool reported progress `32/32`; cannot be omitted in supported flow |
| 14 | Reboot into stock Rabbit OS | Command completed | Reboot issued; physical boot acceptance pending |
| 15 | Record physical stock boot acceptance | Completed | Owner confirmed the R1 returned to stock Rabbit OS |

## Live execution log

### 2026-08-22 16:34:59Z–16:35:39Z: Entered bootloader Fastboot

**Status:** Passed  
**Source:** Rabbit R1 Flash Tool browser log supplied by the owner

Chronology:

1. `16:34:59.337Z`: Device detection initialized.
2. `16:34:59.338Z`: Fastboot operations initialized.
3. `16:35:12.924Z`: Browser requested the MediaTek BROM device through the Serial API.
4. `16:35:15.057Z`: Serial port opened in BROM mode.
5. `16:35:15.058Z`: Tool sent its `FASTBOOT` transition command.
6. `16:35:15.059Z`: Tool reported that the Fastboot command was sent successfully.
7. `16:35:17.834Z`: The R1 re-enumerated as Android USB Fastboot device VID `0x0e8d`, PID `0x201c`.
8. `16:35:17.835Z`: USB serial reported as `919109A5P1600502814D`.
9. `16:35:37.115Z`: Browser requested the Fastboot device through WebUSB.
10. `16:35:39.073Z`: Owner selected the Android Fastboot device.
11. `16:35:39.368Z`: Fastboot initialization returned the authoritative live identity state.
12. `16:35:39.370Z`: Official tool reported a successful Fastboot connection.

Authoritative device information returned by Fastboot:

```json
{
  "product": "k65v1_64_bsp",
  "serialno": "919109A5P1600502814D",
  "secure": "no",
  "unlocked": "yes",
  "currentSlot": "a"
}
```

Gate results:

| Gate | Required | Actual | Result |
|---|---|---|---|
| Device count/selection | One intended R1 | One selected Fastboot endpoint | Pass |
| Serial | `919109A5P1600502814D` | `919109A5P1600502814D` | Pass |
| Product | `k65v1_64_bsp` | `k65v1_64_bsp` | Pass |
| Transport | Bootloader Fastboot | Fastboot USB protocol `0x03`, PID `0x201c` | Pass |
| Unlock state | `yes` | `yes` | Pass |
| Current slot | `a` | `a` | Pass |

The browser emitted the USB-connected block twice. Both blocks reported the same VID, PID, serial, USB version, interface, subclass, and protocol. This is recorded as duplicate detection logging for one physical endpoint, not evidence of two devices.

**Device state after checkpoint:** R1 is connected to the official Rabbit tool in bootloader Fastboot. No stock erase or flash result has been reported yet.

### 2026-08-22 16:36:12Z–16:39:57Z: Stock folder selection

**Status:** Completed

The owner initiated the stock-ROM action multiple times while locating the required extracted directory. The browser logged `Starting stock ROM flash...` at:

- `16:36:12.993Z`
- `16:37:45.743Z`
- `16:37:59.495Z`
- `16:39:32.552Z`

No erase or partition write was logged during those attempts. At `16:39:57.998Z`, the browser accepted the extracted `official/` directory and reported 24 files selected.

The tool mapped the required files to 29 partition targets. Files shared by slots A and B were correctly reused for both targets. Reported sizes matched the extracted stock package inventory, including:

- Preloader: `237912` bytes
- Each VBMeta image: `4096` bytes
- Each boot image: `33554432` bytes
- Each DTBO image: `8388608` bytes
- Super image: `2110680916` bytes
- Userdata image: `7356684` bytes

At `16:39:58.007Z`, the tool began the stock flash sequence. Immediately before the first mutation it rechecked:

- Product: `k65v1_64_bsp`
- Unlocked: `yes`
- Planned operations: `32`

### 2026-08-22 16:39:58Z–16:42:53Z: Official stock flash

**Status:** All 32 tool operations completed successfully  
**Physical stock boot:** Passed by owner observation

#### Data reset

- `16:39:58.011Z`: Official tool began the `wipe` operation.
- `16:39:59.702Z`: Tool received a response object from the erase command.
- `16:39:59.703Z`: Tool marked progress `1/32` complete.

The browser UI rendered the raw response as `[object Object]`, so the response payload itself is not available in this log. The official tool treated the command as successful and continued.

#### Preloader and Verified Boot metadata

| Progress | Partition | File | Completion time | Result |
|---:|---|---|---|---|
| 2/32 | `preloader_a` | `preloader_k65v1_64_bsp.bin` | `16:39:59.735Z` | Success |
| 3/32 | `preloader_b` | `preloader_k65v1_64_bsp.bin` | `16:39:59.767Z` | Success |
| 4/32 | `vbmeta_a` | `vbmeta.img` | `16:39:59.779Z` | Success |
| 5/32 | `vbmeta_b` | `vbmeta.img` | `16:39:59.791Z` | Success |
| 6/32 | `vbmeta_system_a` | `vbmeta_system.img` | `16:39:59.803Z` | Success |
| 7/32 | `vbmeta_system_b` | `vbmeta_system.img` | `16:39:59.815Z` | Success |
| 8/32 | `vbmeta_vendor_a` | `vbmeta_vendor.img` | `16:39:59.827Z` | Success |
| 9/32 | `vbmeta_vendor_b` | `vbmeta_vendor.img` | `16:39:59.839Z` | Success |

#### Modem and platform firmware

| Progress | Partition | Completion time | Result |
|---:|---|---|---|
| 10/32 | `md1img_a` | `16:40:03.272Z` | Success |
| 11/32 | `md1img_b` | `16:40:06.729Z` | Success |
| 12/32 | `spmfw_a` | `16:40:06.746Z` | Success |
| 13/32 | `spmfw_b` | `16:40:06.762Z` | Success |
| 14/32 | `scp_a` | `16:40:06.806Z` | Success |
| 15/32 | `scp_b` | `16:40:06.870Z` | Success |
| 16/32 | `sspm_a` | `16:40:06.928Z` | Success |
| 17/32 | `sspm_b` | `16:40:06.969Z` | Success |
| 18/32 | `gz_a` | `16:40:07.158Z` | Success |
| 19/32 | `gz_b` | `16:40:07.344Z` | Success |

#### Boot-critical partitions

| Progress | Partition | Completion time | Result |
|---:|---|---|---|
| 20/32 | `lk_a` | `16:40:07.415Z` | Success |
| 21/32 | `lk_b` | `16:40:07.482Z` | Success |
| 22/32 | `boot_a` | `16:40:09.544Z` | Success |
| 23/32 | `boot_b` | `16:40:11.609Z` | Success |
| 24/32 | `dtbo_a` | `16:40:12.120Z` | Success |
| 25/32 | `dtbo_b` | `16:40:12.676Z` | Success |
| 26/32 | `tee_a` | `16:40:12.698Z` | Success |
| 27/32 | `tee_b` | `16:40:12.719Z` | Success |

#### Stock system and user-data partitions

| Progress | Partition | File size | Completion time | Result |
|---:|---|---:|---|---|
| 28/32 | `logo` | `1452528` | `16:40:12.825Z` | Success |
| 29/32 | `super` | `2110680916` | `16:42:49.614Z` | Success |
| 30/32 | `userdata` | `7356684` | `16:42:50.120Z` | Success |

The `super` write ran for approximately 2 minutes 37 seconds and was the longest operation. No disconnect or error was reported during it.

#### Slot selection, relock, and reboot

- `16:42:50.120Z`: Official tool began setting active slot `a`.
- `16:42:50.123Z`: Tool marked progress `31/32` complete.
- `16:42:50.124Z`: Official tool automatically began `flashing lock`.
- `16:42:53.172Z`: Tool marked progress `32/32` complete.
- `16:42:53.172Z`: Tool reported all files flashed successfully and began reboot.
- `16:42:53.174Z`: Tool displayed `Stock ROM flashed successfully! Device is rebooting.`
- `16:42:53.337Z`: Fastboot USB endpoint disconnected as expected during reboot.

The disconnect event was logged twice with the same VID `0x0e8d` and PID `0x201c`, consistent with the duplicate browser device listeners already observed at connection time.

**Device state after checkpoint:** Official stock bytes were written, slot A was selected, the official lock command completed, and the R1 rebooted successfully into stock Rabbit OS.

### 2026-08-22: Physical stock boot acceptance

**Status:** Passed  
**Evidence source:** Owner physical observation

The owner confirmed that the R1 returned to stock Rabbit OS after the official flash and reboot. This completes the JackRabbitOS-to-stock software transition.

The owner initially expected the bootloader to remain unlocked. The browser transcript, however, records that the official tool executed `flashing lock` and completed progress `32/32`. The authoritative state must be determined by a fresh Fastboot `unlocked` query before beginning the JackRabbit installer rehearsal. Until that query is recorded, the bootloader is treated as locked.

## Physical stock acceptance

Complete only after the stock flash:

- [ ] Rabbit stock boot screen appears.
- [ ] Stock setup or expected stock product surface loads.
- [ ] Display orientation and touch input work.
- [ ] Buttons and wheel respond.
- [ ] Camera behavior is observed and recorded without repair work.
- [ ] The device does not enter a boot loop.
- [ ] No red Verified Boot failure appears.
- [ ] The official tool completes its bootloader relock without error.
- [ ] The resulting locked stock state is recorded as the starting point for the JackRabbit installer rehearsal.

## Failures and deviations

No transition failures or deviations have occurred yet.

Add every future event using this format:

```text
Timestamp:
Stage/step:
Command or physical action:
Expected result:
Actual result:
Device state afterward:
Decision:
Evidence path:
```

## Current handoff

The host is ready for the official browser-based transition. The next action is to open Rabbit's flash tool, enter Fastboot through its supported WebUSB flow, record the live identity gate, and continue only if the expected R1 is selected. The official tool will then erase userdata, flash stock, relock, and reboot. The rehearsal stops after stock boot acceptance and does not complete Rabbithole setup.

## CipherOS installation model for the following JackRabbit rehearsal

CipherOS does not live entirely in `system_ext_a`. Its Android base is divided across multiple logical partitions inside the physical `super` partition:

| Partition | Responsibility |
|---|---|
| `system_a` | Main Android operating system and framework |
| `system_ext_a` | Additional system framework components and extensions |
| `product_a` | Product configuration, overlays, permissions, and product applications |
| `vendor_a` | Rabbit hardware drivers, HAL integration, and vendor configuration |

Stock Rabbit OS does not define the `system_ext_a` logical partition in the layout needed by CipherOS. The documented R1 CipherOS installation flow creates it inside `super` before writing the CipherOS image:

```bash
fastboot create-logical-partition system_ext_a 559304704
```

This creates a `559304704`-byte logical partition, approximately 533 MiB. It does not create a container for the complete operating system. CipherOS `system_ext.img` is written into that one partition after it is created.

The documented CipherOS logical-partition writes are:

```bash
fastboot flash system_a system.img
fastboot flash system_ext_a system_ext.img
fastboot flash product_a product.img
fastboot flash vendor_a vendor.img
```

These logical partition operations belong in Fastbootd. Boot and VBMeta operations belong in bootloader Fastboot.

### JackRabbit partition ownership

JackRabbit uses CipherOS as its Android and Rabbit-hardware base while replacing the two product-owned images already proved by the project:

| Partition | JackRabbit source |
|---|---|
| `system_a` | JackRabbit-modified CipherOS `system.img` |
| `system_ext_a` | CipherOS `system_ext.img` |
| `product_a` | JackRabbit-modified CipherOS `product.img` |
| `vendor_a` | CipherOS `vendor.img` |

Therefore:

- CipherOS spans all four logical partitions; it is not located only in `system_ext_a`.
- JackRabbit does not replace the Rabbit hardware/vendor base unnecessarily.
- JackRabbit's accepted `system.img` and `product.img` carry the intentional product changes.
- CipherOS `system_ext.img` and `vendor.img` retain the Android extension and hardware integration required by the R1.

### Source evidence

The Rabbit R1 CipherOS procedure and the missing-`system_ext` stock-layout finding are documented by:

`https://github.com/TurboTheTurtle/rabbit-r1-firmware`

This is a third-party technical source, not an official Rabbit or CipherOS installer. Its sequence must be reconciled with this project's physically proved Fastboot/Fastbootd boundaries before it becomes the public JackRabbit installer contract.
