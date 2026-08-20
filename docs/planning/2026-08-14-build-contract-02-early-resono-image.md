# Build Contract 02 — Early Reversible ReSono Image

**Candidate:** `R1-BUILD-CONTRACT-02-v0.1`  
**Grounding:** `GROUNDING-BASELINE-v0.4`  
**Delivery plan:** `R1-STANDALONE-DELIVERY-PLAN-v0.3`, Delivery Slice 2  
**Status:** Complete and owner accepted 2026-08-14  
**Owner direction:** Move on from hardware/camera investigation. Existing behavior is accepted except for the deferred camera defect.

## Exact success scenario

Produce one recoverable engineering R1 image derived from the exact working CipherOS/Rabbit baseline. It boots directly into the real ReSono HOME, removes only proven optional Cipher product surfaces, and retains the working low-level hardware and required Android services.

Camera repair is not part of this contract. The existing camera failure must remain visible in acceptance results and must not be worsened or misreported.

## Small dependency-ordered checkpoints

1. **Offline baseline intake and inventory — authorized now.** Copy the exact known-good CipherOS archive, Rabbit boot image, and payload extraction tool into `image/baseline/` and `image/tools/`; verify hashes; extract the OTA logical partitions offline; inventory filesystem packages, services, overlays, permissions, and partition metadata. Do not touch the device.
2. **Minimal image composition.** Classify packages and system surfaces as `KEEP`, `REPLACE`, or `REMOVE`. Copy only the proven image overlay/build inputs required from the donor. Create one reproducible remaster command that embeds the existing ReSono HOME and changes the smallest safe group of visible Cipher product surfaces.
3. **Offline candidate verification.** Verify image mountability, package placement, HOME/permissions configuration, partition size, hashes, and that required framework/vendor components remain. Freeze the candidate and exact rollback set.
4. **Physical image proof — not yet authorized.** After an explicit owner confirmation immediately before mutation, flash only the reviewed candidate through the proven same-device route and test boot, HOME, rollback, and existing working behavior. Do not add camera repair to this test.

## Frozen input boundary

| Input | Read-only donor source | Standalone destination | SHA-256 |
|---|---|---|---|
| CipherOS OTA | `project-3d3354dadcad/workspace/phases/2026-08-13_r1_cipheros_resono_restore/artifacts/cipheros/CipherOS-7.0-ALHENA-cipher_r1-20250623-0753-BETA-OFFICIAL-VANILLA.zip` | `image/baseline/cipheros/CipherOS-7.0-ALHENA-cipher_r1-20250623-0753-BETA-OFFICIAL-VANILLA.zip` | `9ba81b11e9bce06dd604204fcdb2d3d43998931066edfb339a16aaa78e705eb0` |
| Rabbit boot | `project-3d3354dadcad/workspace/phases/2026-08-13_r1_cipheros_resono_restore/artifacts/rabbit-0.8.293/boot.img` | `image/baseline/rabbit-0.8.293/boot.img` | `0480ffab24e208ca20e761ebc07c15c0992ee3c91a3f55377731fdec532ae30f` |
| Payload dumper | `project-3d3354dadcad/workspace/phases/2026-08-13_r1_cipheros_resono_restore/tools/payload-dumper-linux-amd64-v3` | `image/tools/payload-dumper-linux-amd64-v3` | `40d7242fbd384fd93c880fd701515ba995fca6ab1c0d8bc0eaf2ab52383272a6` |
| ReSono HOME | `artifacts/android-baseline/ReSonoVoice-engineering-system-v0.1.apk` | image candidate privileged application location selected after inventory | `43f0c727ed44c306104767c709374ca7b53516ddeffdbfd92706530189b5cd4a` |

The donor revision remains `0f3b34223f745920e79d1d9db301f3b639d08393`. Donors are read-only. All extraction and modification occurs only inside this standalone project.

## Functional invariants

| Invariant | Observable control and failure |
|---|---|
| Exact working base | Intake hashes must match before extraction. Any mismatch stops the checkpoint. |
| Low-level hardware preserved | `boot`, `vendor`, firmware, modem/calibration, and device-specific hardware layers remain unchanged in the first candidate unless a later recorded dependency proves a required narrow change. |
| ReSono is the product surface | The real ReSono HOME is embedded and selected; no placeholder launcher or mock UI is allowed. |
| Removal is evidence-based | A package is removed only after inventory assigns it `REMOVE` and required dependents are absent or replaced. Unknown packages default to `KEEP`. |
| Recovery precedes flash | Exact rollback inputs and commands must be verified before any physical write. No flash occurs under Checkpoints 1–3. |
| Known defect stays truthful | Camera remains recorded as failing/deferred. Structural camera-service presence cannot be reported as functional success. |
| Repository isolation | Donor hashes/status remain unchanged; all new files are below this project. |

## Material Decision Gates

### BC2-MDG-01 — Image route

- **Question:** Build a new low-level R1 port, mutate the live device package-by-package, or remaster the exact recovered working images offline?
- **Authority/evidence:** OD-01, OD-02, OD-12, OD-18; same-device successful restore evidence; owner decision not to rewrite low-level drivers.
- **Alternatives:** New AOSP/device port; live debloat; exact offline remaster; blocked.
- **Selection/function:** Exact offline remaster. It preserves the proven hardware base and makes every removal reproducible and reversible.
- **Counterexample:** The candidate silently changes boot/vendor inputs or can exist only because packages were manually disabled on one live device.
- **Dependents:** Every checkpoint in this contract.
- **Result:** `CONTINUE`.

### BC2-MDG-02 — First removal size

- **Question:** Remove every unwanted app at once or start with one minimal classified group?
- **Authority/evidence:** OD-01–OD-03; prior donor failures from combined HOME/system changes; final release still requires full cleanup.
- **Alternatives:** Broad removal; one reversible group; no cleanup.
- **Selection/function:** One minimal group after inventory, while retaining uncertain framework dependencies and recovery fallback until replacements are proven.
- **Counterexample:** The image looks clean but loses boot, HOME, settings, input, networking, audio, permissions, or recovery behavior.
- **Dependents:** Checkpoints 2–4.
- **Result:** `CONDITIONAL` on Checkpoint 1 inventory.

### BC2-MDG-03 — Physical mutation

- **Question:** Flash while building or keep all work offline until the exact candidate and rollback are frozen?
- **Authority/evidence:** Anti-drift recovery rule; same-device restore history; physical device is the owner's working unit.
- **Selection/function:** Keep Checkpoints 1–3 offline. Require immediate explicit owner confirmation for the exact Checkpoint 4 flash command and artifacts.
- **Counterexample:** A generated image is flashed before its partition sizes, contents, hashes, and rollback inputs are known.
- **Dependents:** Physical acceptance.
- **Result:** `BLOCKED/REOPEN` for device writes; `CONTINUE` for offline work.

### BC2-MDG-04 — Embedded APK selection

- **Question:** Embed APK version code 1 while the same package/version is installed under `/data`, uninstall the working HOME before flashing, or advance the standalone engineering APK version for the image candidate?
- **Authority/evidence:** The current data-installed HOME and baseline APK both use package `com.resonolabs.voice.engineering`, version code 1, and the same signer. Android can retain a data-installed system-app update, which would make a successful boot insufficient proof that the embedded APK ran.
- **Alternatives:** Keep equal versions; uninstall first; use a higher standalone engineering version.
- **Selection/function:** Advance the standalone engineering APK to version code 2/name `0.1.1-engineering-debug`, rebuild/test it, and embed that exact artifact. This lets Package Manager select the newer system copy without a destructive pre-flash uninstall.
- **Counterexample:** After boot, `pm path` still resolves only to `/data/app`, or reported version code is not 2.
- **Dependents:** Candidate manifest, APK hash, physical proof, rollback.
- **Result:** `CONTINUE`; no device action is authorized.

## Checkpoint 1 acceptance

- All three input hashes match.
- OTA integrity and metadata match the recorded R1 CipherOS build.
- Extracted partition hashes match the preserved donor extraction record.
- Package/service inventory is generated from actual extracted filesystems, not only the currently installed package list.
- No donor or device state changes.

Checkpoint 1 rollback removes only its copied/extracted files from this standalone project's `image/` boundary. No other project or device is changed. Checkpoint 2 cannot begin until Checkpoint 1 passes and its package classification has been reviewed against real dependencies.

## Checkpoint 1 execution result

**Candidate:** `R1-IMAGE-BASELINE-v0.1`  
**Result:** `PASS` — offline only; no device command or donor mutation

- All three copied input hashes match the frozen contract.
- ZIP integrity passes with no compressed-data errors.
- OTA metadata identifies `rabbit/cipher_r1/r1`, Android 16/API 36, build `BP2A.250605.031.A2`, security patch `2025-06-05`, and A/B OTA type.
- All eight extracted partition hashes match the previously preserved extraction record exactly.
- The deterministic inventory contains 371 lines across filesystem types, OTA metadata, payload properties, package directories, init service directories, and overlay directories.
- `image/inventory/PACKAGE_CLASSIFICATION.md` freezes the first removal group and defaults every uncertain or dependency-bearing component to `KEEP`.
- The extracted Cipher OTA boot differs from the working Rabbit boot. The first candidate retains the exact Rabbit boot and does not change `vendor`.
- `image/scripts/inventory_baseline.sh` regenerates the evidence from the copied images.

**Post-checkpoint decision:** `CONTINUE` to Checkpoint 2 offline candidate tooling. Device writes remain `BLOCKED/REOPEN` pending Checkpoints 2–3 and immediate owner confirmation.

## Checkpoint 2 execution result

**Candidate:** `R1-EARLY-IMAGE-v0.1`  
**Result:** `PASS` for offline composition; no device mutation

- Added one small deterministic build script rather than a general image framework.
- Removed exactly the 13 classified optional product-app directories from copied `system`/`product` images.
- Added the real ReSono engineering HOME and its two proven permission files.
- Review found that embedding version code 1 could leave the existing `/data` copy active. The standalone APK was advanced to version code 2, rebuilt, and all 101 tests passed.
- The version-code-2 APK retains the current package and signer; its frozen hash is `43f0c727ed44c306104767c709374ca7b53516ddeffdbfd92706530189b5cd4a`.
- Both candidate filesystems pass read-only `e2fsck`; embedded bytes, ownership, modes, and SELinux type pass.
- Two consecutive candidate builds produced identical hashes: system `8dd79328bf1d63749c64ea0b7ebeb34517f9ca21c3f6e8f999b46719e8631814`, product `eac03525513be044b804c0a33711eda75922d0fc25ef815ad4f2efa6168e1c41`.
- Complete composition is frozen in `image/candidates/v0.1/MANIFEST.md`.

**Post-checkpoint decision:** `CONTINUE` to Checkpoint 3 offline flash/rollback protocol review. Device writes remain `BLOCKED/REOPEN`.

## Checkpoint 3 execution result

**Result:** `PASS` for offline candidate and guarded apply/rollback protocol; no device mutation

- `image/scripts/apply_candidate_v0_1.sh` defaults to non-mutating `--plan` mode.
- Apply and rollback verify every candidate/baseline hash before inspecting or writing a device.
- Mutation requires the exact fastboot serial, fastbootd userspace mode, unlocked state, slot `a`, product `k65v1_64_bsp`, an explicit mode, and its exact confirmation phrase.
- Apply changes only `system_a`, `product_a`, `vbmeta_a`, and `vbmeta_system_a`, then reboots. It does not erase userdata/metadata or change boot, vendor, system_ext, firmware, or slot `b`.
- Rollback restores the same four active-slot partitions from the exact copied CipherOS baseline.
- Plan mode passed. A negative apply test without the confirmation phrase exited `2` before querying or writing any device.

**Post-checkpoint decision:** Checkpoint 4 is `BLOCKED/REOPEN` until the owner explicitly authorizes applying exact candidate `R1-EARLY-IMAGE-v0.1` after reviewing its scope. Camera remains deferred and is not part of the apply acceptance.

## Checkpoint 4 execution result

**Result:** `PASS` for objective physical apply and boot verification

- The owner authorized the exact candidate and identified the connected R1 as a test device without user data.
- Preflight identity, fingerprint, slot, fastbootd, unlocked state, product, and artifact hashes passed.
- Candidate `system_a` and `product_a` wrote successfully.
- The first vbmeta command exposed a real script defect: fastbootd cannot write `vbmeta_a`. The command failed without rebooting. This was classified as an implementation defect, not hidden or treated as success.
- The R1 was moved to bootloader fastboot; identity/unlocked/slot gates passed; active-slot vbmeta and vbmeta_system then wrote successfully.
- The guarded script now encodes the correct fastbootd → bootloader-fastboot sequence for both apply and rollback.
- The device booted successfully. Active system/product block hashes exactly match the frozen candidate.
- ReSono runs from `/system/priv-app`, reports version code 2, resolves as default HOME, and is the resumed activity.
- Removed and retained path tests pass; privileged/runtime grant checks pass.
- No data wipe or change to boot, vendor, system_ext, firmware, slot `b`, or camera paths occurred.

**Acceptance boundary:** Objective validation is complete. On 2026-08-14 the project owner explicitly confirmed the visible/physical result after the hosted enrollment branch was removed from the version-code-3 reference APK. Build Contract 02 and Delivery Slice 2 are complete. Camera remains a truthful deferred defect.
