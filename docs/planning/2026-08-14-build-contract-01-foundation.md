# Build Contract 01 — Existing Android Baseline Import and Reproduction

**Candidate:** `R1-BUILD-CONTRACT-01-v0.3`  
**Grounding:** `GROUNDING-BASELINE-v0.4` (owner accepted)  
**Delivery plan:** `R1-STANDALONE-DELIVERY-PLAN-v0.3` (owner accepted)  
**Date frozen:** 2026-08-14  
**Status:** Complete 2026-08-14; existing APK/device baseline accepted, no replacement install performed, camera recorded as a deferred known defect  
**Owner authorization:** “you can pull that apk and any other files over to this build directory if need be. copy do not remove. just copy it over” followed by “ok you are approved to continue on”

This is the sole Build Contract 01. It replaces the withdrawn v0.1 structural-foundation contract. It authorizes only the dependency-ordered checkpoints below; it does not authorize work from later delivery slices.

## Exact success scenario

The standalone project contains a byte-verifiable copy of the coherent, non-generated ReSono R1 Android project and the existing donor debug APK. The donor remains unchanged. Import records identify the exact donor revision, dirty working-tree state, source and destination paths, exclusions, and hashes. The copied project was reproduced locally, and the exact existing installed HOME/device state was captured and accepted without a redundant overwrite install.

The checkpoint definitions below preserve the contract's execution history. The final closure section controls current status: Build Contract 01 is complete and no device mutation was performed.

## Scope

### Permitted now — Checkpoint 1: verified import

- Read the donor repository without modifying it.
- Record donor Git revision and dirty state.
- Copy the exact tracked and non-ignored Android source/configuration set from `app/rabbit_r1/android/` into this project’s `android/`.
- Exclude generated build outputs, Gradle caches, machine-local SDK configuration, and unrelated deployment material.
- Copy the existing debug APK separately into `artifacts/android-baseline/` as immutable grounding evidence.
- Record and verify source and APK hashes.
- Add only import/provenance metadata required to distinguish copied donor bytes from later standalone changes.

### Gated next — Checkpoint 2: local reproduction

- Provision or select JDK 17, Android SDK/API 36, and Gradle 9.5 without embedding machine-specific absolute paths in the community workflow.
- Build the imported engineering APK from this repository.
- Run applicable donor Android unit tests.
- Compare identifiers, manifest behavior, module coverage, and artifact metadata with the copied baseline.

Checkpoint 2 begins only after Checkpoint 1 passes. Downloading tools or dependencies requires the applicable environment/network approval. A successful build may reveal donor defects; it does not authorize unrelated refactoring.

### Gated later — Checkpoint 3: read-only physical capture

- Identify the exact R1 through ADB/fastboot evidence.
- Capture current slot, partitions/build fingerprint, installed packages, HOME resolution, package signatures, relevant grants/services, and recovery route without mutation.
- Record the existing hardware behavior matrix.

Checkpoint 3 requires an attached, authorized R1 and a demonstrated recovery path. Read-only capture is not permission to flash, uninstall, disable, clear, or overwrite anything.

### Separately gated — Checkpoint 4: engineering install and regression

- Install only the distinct debug application ID `com.resonolabs.voice.engineering` using the accepted install command.
- Preserve the installed CipherOS base and a recoverable launcher/system path.
- Test HOME resolution plus touch, wheel, side button, motorized camera, microphone, speaker, Wi-Fi, Bluetooth, display, sleep/wake, boot, and existing Voice behavior.
- Uninstall only the engineering package if rollback is required.

Checkpoint 4 requires successful Checkpoints 1–3, verified package identity/signing behavior, a proven rollback command, and explicit confirmation immediately before device mutation.

### Prohibited by this contract

- Modifying, cleaning, resetting, stashing, deleting, moving, or overwriting any donor/reference project.
- Copying donor `.gradle/`, `build/`, `app/build/` other than the one explicitly identified APK, or `local.properties`.
- Editing product behavior during import.
- Installing or flashing anything as part of Checkpoint 1.
- Removing/disabling CipherOS packages, changing partitions, rebuilding the OS, or starting later runtime/UI/provider work.
- Mockups, placeholders, fake states, or simulated acceptance evidence.

## Planned and affected components

| Component | Donor source | Standalone destination | Checkpoint |
|---|---|---|---|
| Coherent Android project | `app/rabbit_r1/android/` tracked/non-ignored file set | `android/` | 1 |
| Existing debug APK | `app/rabbit_r1/android/app/build/outputs/apk/debug/app-debug.apk` | `artifacts/android-baseline/ReSonoVoice-engineering-donor.apk` | 1 |
| Import metadata/hashes | donor Git and filesystem observations | `android/DONOR_IMPORT.md`, `android/DONOR_SHA256SUMS`, `artifacts/android-baseline/SHA256SUMS` | 1 |
| Build environment | copied Gradle project plus external JDK/SDK/Gradle dependencies | no vendored toolchain unless separately approved | 2 |
| Physical R1 | owner’s existing CipherOS R1 | read-only evidence first; engineering APK later | 3–4 |

The imported module boundary remains unchanged through the parity build. Cleanup and standalone adaptation require later accepted contracts.

## Required behavior and functional invariants

| ID | Invariant | Established by | Controls | Required denial/failure | Counterexample that fails |
|---|---|---|---|---|---|
| BC1-I01 | Donors remain read-only. | Owner boundary, path checks, before/after donor status and hashes | Every copy/edit operation | Stop if destination resolves outside this project or donor status changes | Copy command writes a generated manifest back into the donor |
| BC1-I02 | Import is coherent, not a hand-selected rewrite. | Exact donor tracked/non-ignored Android file list and destination comparison | Source inclusion | Fail if any selected donor file is missing, changed, or an unrecorded project file substitutes for it | App sources copy but motor-service or Gradle module configuration is omitted |
| BC1-I03 | Generated and machine-local state is not adopted as source. | Explicit exclusions and post-copy scan | Imported source boundary | Fail if caches, general build outputs, or `local.properties` appear under `android/` | Copying all 280 MB makes a donor build cache look like project source |
| BC1-I04 | The copied APK is evidence, not source or proof. | Separate artifact path, hash, and label | Claims about build/release readiness | Do not claim reproduction until Checkpoint 2 builds from copied source | APK launches, so the repository is called reproducible without building it |
| BC1-I05 | Device state is protected until independently captured and recoverable. | Checkpoint gates and explicit device-mutation confirmation | ADB install, package, HOME, and partition operations | No mutating device command before Checkpoint 3 passes | Installing first because the APK package ID appears distinct |
| BC1-I06 | Existing product behavior is preserved during parity reproduction. | Unchanged import plus build/test/physical regression evidence | Changes before later adaptation contracts | Stop and classify any parity failure; do not hide it with redesign | Fixing the UI or Vault dependency during baseline import makes comparison impossible |
| BC1-I07 | No mock evidence can satisfy a physical or build outcome. | Real build output, real device output, real hashes | Checkpoint acceptance | Simulated logs/screens/tests are rejected | A scripted sample ADB transcript is accepted without a connected R1 |

## External requirements

- Android build inputs are those declared by the imported Gradle project: Java 17, compile/target SDK 36, minimum SDK 31, Android Gradle Plugin 9.3.0, and Gradle 9.5 as used by donor scripts. These are observations to validate during reproduction, not permission to redesign the build.
- Android signing, privileged permissions, HOME behavior, and CipherOS package grants must be measured on the actual device before installation claims.
- Third-party and public-release licensing remains unresolved and is a release blocker, not an import blocker under owner-controlled private copying.

## Allowed implementation discretion

- Use a deterministic copy mechanism that preserves relative paths and file bytes.
- Store baseline artifacts below `artifacts/android-baseline/`.
- Add minimal import metadata that does not alter donor-derived build behavior.
- Replace machine-specific build-script paths only in Checkpoint 2 and only as the smallest portability correction, after byte parity is recorded.

## Assumptions and unknowns

### Narrow reversible assumptions

- The donor’s Git tracked plus non-ignored Android file set is the coherent source/configuration boundary. This is tested against `settings.gradle.kts`, module paths, and post-copy file parity.
- The existing debug APK corresponds closely enough to the current donor tree to serve as behavioral grounding. It is not treated as a reproducible match until a local build comparison and physical test establish that.

### Unresolved unknowns

- Exact relationship between the dirty donor working tree and the existing APK.
- Whether all required Android dependencies remain fetchable and compatible in a clean environment.
- Current physical R1 serial, CipherOS build, slots/partitions, signing state, HOME, grants, recovery path, and hardware behavior.
- Whether the engineering APK can coexist safely with the current installed HOME without a package/signature conflict.

These unknowns block only their dependent checkpoints.

## Material Decision Gates

### BC1-MDG-01 — Copy boundary

- **Question:** Copy isolated APK files, the entire 280 MB working directory, or the coherent non-generated Android project?
- **Authority/evidence:** OD-01, OD-02, OD-18, OD-24; F-16; accepted plan P-MDG-02; donor Gradle module graph and `.gitignore`.
- **Alternatives:** Hand-select files; copy caches/build outputs; copy exact tracked/non-ignored project files; remain blocked.
- **Selection/function:** Copy the exact tracked/non-ignored Android set. This retains the real modular build while excluding generated and machine-local state.
- **Counterexample:** The destination is smaller but cannot resolve the motor-service module, or contains donor `.gradle` caches that make it appear buildable.
- **Dependents:** Import parity, build reproduction, later APK work.
- **Result:** `CONTINUE` for Checkpoint 1.

### BC1-MDG-02 — Baseline APK treatment

- **Question:** Ignore the existing APK, overwrite source build outputs with it, or preserve it separately as hashed evidence?
- **Authority/evidence:** Owner explicitly authorized copying the APK for grounding; OD-03; protocol separates evidence from implementation.
- **Alternatives:** Omit; treat binary as product; copy separately and label limitations.
- **Selection/function:** Copy it to the standalone artifact boundary with its exact hash. It grounds comparison without masquerading as a source build.
- **Counterexample:** The binary is placed in `android/app/build/` and later mistaken for the standalone build result.
- **Dependents:** Checkpoints 1–2 and provenance claims.
- **Result:** `CONTINUE` for Checkpoint 1.

### BC1-MDG-03 — Device ordering

- **Question:** Install immediately, capture device state first, or block all progress until the device is connected?
- **Authority/evidence:** Accepted plan P-MDG-01; owner has authorized copying but not current device mutation; current device/recovery state is unknown.
- **Alternatives:** Immediate install; import while device work remains blocked; no work.
- **Selection/function:** Complete reversible repository import now. Require read-only capture and recovery proof before install.
- **Counterexample:** An install changes HOME resolution before the original state and rollback path are known.
- **Dependents:** Checkpoints 3–4.
- **Result:** `CONTINUE` for Checkpoint 1; `BLOCKED/REOPEN` for device mutation until its gates pass.

### BC1-MDG-04 — Parity before cleanup

- **Question:** Clean/refactor while copying or reproduce the donor boundary before behavioral changes?
- **Authority/evidence:** OD-02, OD-18; accepted plan slice 1; anti-drift requirement for a comparable baseline.
- **Alternatives:** Improve during import; unchanged import then reproduce; rewrite.
- **Selection/function:** Record byte parity first and defer cleanup. Later contracts can remove external Vault assumptions against known behavior.
- **Counterexample:** A “cleaner” imported app fails, but the project cannot distinguish copied defects from new changes.
- **Dependents:** Every later Android refactor and regression claim.
- **Result:** `CONTINUE`.

## Tests and acceptance evidence

### Checkpoint 1 positive tests

1. Donor revision and dirty state are recorded before copying.
2. Every selected donor path exists at the matching destination and has the same SHA-256.
3. The copied APK SHA-256 matches the donor APK.
4. `settings.gradle.kts` module includes resolve to copied directories.
5. Import metadata identifies exact donor/destination roots, selection rule, exclusions, counts, and hashes.
6. Donor Git status is byte-for-byte unchanged before and after the operation.

### Checkpoint 1 negative tests

1. No `.gradle/`, general `build/`, `app/build/`, or `local.properties` exists in imported source.
2. No import operation resolves outside the standalone destination.
3. No copied APK appears under a source build-output directory.
4. No product source differs from the donor before any later accepted modification.

### Later checkpoint evidence

- Checkpoint 2: clean build/test transcript, resulting APK hash, manifest/application ID, and comparison report.
- Checkpoint 3: real read-only device/recovery capture tied to exact serial/build identifiers.
- Checkpoint 4: real install transcript, hardware regression matrix, failures, owner observation, and rollback proof.

## Stop, rollback, and exit

- Stop the affected checkpoint on a hash mismatch, unexpected generated/secret material, donor change, unresolved identity/signing issue, unavailable recovery, or physical regression.
- Checkpoint 1 rollback removes only the newly copied `android/` and `artifacts/android-baseline/` paths from this standalone project; donor files are never touched. Because later standalone edits will build on the import, rollback is permitted only before such edits or by reverting an exact recorded change.
- Checkpoint 4 rollback uninstalls only `com.resonolabs.voice.engineering` after its identity is reverified; it does not clear or change any other package or partition.
- Checkpoint 1 exits when all import positive/negative tests pass and the import is frozen as a candidate.
- Build Contract 01 exits only when all four checkpoints and owner physical acceptance pass. Until then, report the exact completed checkpoint and remaining blockers without claiming slice completion.

## Internal review result

**Reviewer:** internal self-review, separated pass against the accepted grounding, delivery plan, full Phase 03 prompt, and donor observations.  
**Pre-execution result:** `CONTINUE` for Checkpoint 1 only.  
**Reason:** The step is explicitly owner-authorized, reversible, donor-read-only, necessary for delivery slice 1, and cannot alter device state. Local reproduction and physical-device claims remain honestly gated. The wrong-but-well-formed counterexamples above prevent a copied binary, partial source tree, cache-dependent build, or simulated device record from satisfying the outcome.

## Checkpoint 1 execution evidence

**Candidate:** `R1-ANDROID-DONOR-IMPORT-v0.1`  
**Result:** `PASS` — internal objective validation and internal self-review; no external physical validation claimed  
**Evidence:** `android/DONOR_IMPORT.md`, `android/DONOR_SHA256SUMS`, and `artifacts/android-baseline/SHA256SUMS`

- 167 selected donor source/configuration paths were copied.
- Source and destination ordered SHA-256 manifests both produced `4b7b017abd5e3b232ddb236f84d14a93bf7c67489067a034785215f03c6d783d`.
- Every per-file checksum passed from the standalone source tree.
- Path comparison returned no missing or extra donor-derived source file.
- The baseline APK passed SHA-256 verification as `352910a85eb01ff00c2152c19b4bbac844f951fe1d4e21213dcd097edec480f5`.
- No imported `.gradle/`, `build/`, `app/build/`, or `local.properties` remained under `android/`.
- Every module declared in `settings.gradle.kts` has a copied directory.
- The bounded private-key/OpenAI-key pattern scan returned no match.
- The full donor dirty-state fingerprint was `a9fc07ef788c121c533fbfb32defbcf5443f348148e46df2d3a4dee271f8f307` both before and after copying.

The initial `rsync` copy mechanism was unavailable and copied no source. The same frozen 167-path selection was then transferred with a deterministic `tar` stream and verified byte-for-byte. This environment issue did not change the selected import set or donor state.

**Post-execution review result:** `CONTINUE` to Checkpoint 2 prerequisite inspection. Checkpoint 1 is complete. Delivery slice 1 is not complete, the imported source has not yet been reproduced locally, and no device or OS claim has been validated.

## Checkpoint 2 correction record

**Finding:** The unchanged APK build passed, but 19 of 71 unit tests failed because four provisioning tests resolved `../../../../tests/fixtures/device_provisioning/protocol-v1.json`. That path was valid only at the donor repository’s old nesting depth and proved the initial Android-only test-boundary assumption incomplete.

**Classification:** Correction, not new design. The application source and behavior are unchanged.

**Material Decision Gate:**

- **Question:** Skip the failing tests, recreate the donor’s external directory depth, retain four depth-relative paths, or package the exact fixture as a normal Gradle test resource?
- **Authority/evidence:** OD-01–OD-03, OD-18, BC1-I02, BC1-I06; real `testDebugUnitTest` result; exact donor fixture SHA-256 `076071d0118d9523f0a527640b0a37e0a78191ac7b5cad48c0197eaadca04c51`.
- **Alternatives:** Skip/mark passing; create data outside the project; copy fixture and preserve brittle relative paths; copy the one fixture into test resources and use one shared loader; block.
- **Selection/function:** Copy the exact public test vector to `android/app/src/test/resources/device_provisioning/protocol-v1.json` and load it through one package-private test helper. This makes the real negative/security tests portable without changing production code.
- **Counterexample:** Tests pass only when the repository is placed at a particular filesystem depth, or use a rewritten fixture whose signatures no longer test the donor protocol vectors.
- **Dependents:** Checkpoint 2 unit-test evidence and contributor build portability.
- **Result:** `CONTINUE`; rerun the complete suite and stop if any failure remains.

## Checkpoint 2 execution evidence

**Candidate artifact:** `artifacts/android-baseline/ReSonoVoice-engineering-standalone-v0.1.apk`  
**Result:** `PASS` for local source build and unit tests; physical behavior remains unvalidated  

- Temporary isolated toolchain: Temurin JDK `17.0.20+8`, Gradle `9.5.0`, Android command-line tools `22.0`, Android platform `36`, build-tools `36.0.0`, and platform-tools/ADB `37.0.1`.
- Unchanged imported `scripts/build_debug.sh` completed `:app:assembleDebug`; first clean dependency build executed 360 tasks successfully in 31 seconds.
- The recorded fixture correction was followed by a full `testDebugUnitTest` run: **101 tests, 0 skipped, 0 failures, 0 errors** across 26 JUnit suites.
- A refreshed `:app:assembleDebug` completed successfully after the correction.
- Standalone APK: SHA-256 `725d0b4ed38449aaf018175f8d593a801b667cb5aa4730a366009c6b24380dea`, size `60,067,555` bytes.
- Donor APK: SHA-256 `352910a85eb01ff00c2152c19b4bbac844f951fe1d4e21213dcd097edec480f5`, size `60,136,313` bytes.
- Both APKs report package `com.resonolabs.voice.engineering`, version code `1`, version `0.1.0-engineering-debug`, minimum SDK `31`, target/compile SDK `36`, and the same Android debug signer certificate SHA-256 `a3390000a4b6c8bf43774cc235bd967e4c80a9dae30c0e8714c79c01a9b9836a`.
- The APKs are not byte-identical. The contract did not assume they would be, because the historical donor APK’s exact source/build-time inputs are unknown. No behavioral equivalence is claimed before physical testing.
- ADB is provisioned, but `adb devices -l` returned no attached device. Therefore Checkpoint 3 cannot yet begin and no install command was run.

**Post-execution review result:** `CONDITIONAL`. Local reproduction succeeds and the only source deviations from the frozen donor manifest are the four recorded test loaders plus one shared test helper/resource correction. Delivery slice 1 and Build Contract 01 remain incomplete until read-only device capture and physical regression pass.

## Checkpoint 3 and contract closure

**Result:** `PASS` for establishing the existing-device baseline; no replacement install or device mutation was performed.

- The connected device is the intended CipherOS R1 and already runs the exact ReSono engineering package as HOME.
- The installed APK was pulled and hashed as an exact rollback artifact.
- Package, signer, HOME, grants, slot, boot-critical partition hashes, and the installed-package inventory were captured read-only.
- Same-device records prove the successful CipherOS restore route, unlocked fastbootd state, first boot, and cold boot into the exact installed ReSono APK.
- The owner reports that current device behavior works except for the camera. Camera is recorded as failing and deferred; it is not called passing.

### BC1-MDG-05 — Redundant replacement install

- **Question:** Overwrite the already-working HOME package with the locally reproduced APK for another regression pass, or accept the exact installed APK/device state as the baseline and advance?
- **Authority/evidence:** Owner physical assessment and direction to stop camera/hardware work and move on; exact installed APK rollback copy; matching package/version/signer; current HOME capture; same-device recovery evidence.
- **Alternatives:** Overwrite/install and repeat all hardware tests; accept the existing installed baseline with its known camera defect; remain blocked.
- **Selection/function:** Accept the existing installed baseline. A redundant overwrite creates device risk and does not improve the next system-image input decision. The locally built APK remains the reproducible source candidate; the pulled APK remains exact rollback.
- **Counterexample:** The device identity or installed signer differs, no rollback/recovery evidence exists, or the owner reports another current failure material to image composition.
- **Dependents:** Delivery Slice 1 exit and Build Contract 02 entry.
- **Result:** `CONTINUE` to Delivery Slice 2. Camera remains a later defect, not a hidden pass.

**Final Build Contract 01 result:** `COMPLETE`. The repository owns a coherent buildable Android baseline and the actual same-device starting state is known. No donor was modified. No install, reboot, package change, flash, or partition write was performed by this contract.
