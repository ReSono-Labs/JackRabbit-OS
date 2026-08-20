# Build Contract 03 — Clean Standalone HOME APK Baseline

**Candidate:** `R1-BUILD-CONTRACT-03-v0.1`  
**Grounding:** `GROUNDING-BASELINE-v0.4` with owner decisions through OD-29  
**Delivery plan:** `R1-STANDALONE-DELIVERY-PLAN-v0.3`  
**Status:** Owner accepted 2026-08-14; architecture/reference checkpoints pass; visual Checkpoint 3 reopened under OD-28  
**Predecessor:** Build Contract 02 and Delivery Slice 2 accepted 2026-08-14

## Exact success scenario

The repository preserves the reproduced Voice-platform Android tree as a clearly labeled, buildable reference and contains one new clean standalone Android product tree. The clean APK installs on the accepted early ReSono image, is selected as HOME, boots without ReSono Admin or external Vault state, and proves real touch, R1 button/wheel navigation, fullscreen/power policy, and minimum device settings behavior. Its native 480×640 presentation is the responsive R1 form of New Browser Voice; side-by-side comparison should reveal only screen/input adaptations, not a separate design.

This contract does not claim Voice, runtime, browser management, providers, or personal-data features. It creates the clean physical HOME boundary they will enter through later real vertical contracts. It does not display disconnected controls or placeholder product states for those future capabilities. The temporary settings-only composition is architectural evidence, not the product HOME: the first real product page will be Voice and the second Cards as those real verticals land.

## Dependency-ordered checkpoints

1. **Freeze and preserve the Android reference.**
   - Verify and permanently preserve the exact original donor APK `artifacts/android-baseline/ReSonoVoice-engineering-donor.apk` at SHA-256 `352910a85eb01ff00c2152c19b4bbac844f951fe1d4e21213dcd097edec480f5`.
   - Verify and separately preserve the tested gate-free reference APK `artifacts/android-baseline/ReSonoVoice-engineering-reference-v0.1.2.apk` at SHA-256 `c16cb0df537eb91672b6aa8590e72e48b15c756461aded70e8d10a347a4ff1f0`.
   - Record the exact current reference-source differences, test result, and physical evidence.
   - Move the current imported `android/` tree intact to `reference/android-voice-platform/`.
   - Verify source counts/hashes and buildability after the move.
   - Do not modify or delete any external donor/reference project.

2. **Freeze the first product import set.**
   - Trace the smallest exact donor/reference file set needed for HOME, native design tokens, R1 input routing, navigation, display/power policy, boot handoff, and real settings actions.
   - Record file-level source and destination paths, retained behavior, excluded hosted behavior, dependencies, and tests before copying.
   - Hosted enrollment, authorization, claim, serialization, Platform pairing, Vault relay/control, edge sync, and Cloud bootstrap are prohibited imports.

### Checkpoint 2 frozen file-level import set

The following is the complete donor-derived product import for this contract. Build files and the clean app composition are new standalone-owned files. No other reference source may enter the product tree under this contract.

| Function | Exact reference source below `reference/android-voice-platform/` | Product destination | Treatment |
|---|---|---|---|
| New Browser Voice-derived native tokens | `core/design/src/main/java/com/resonolabs/ui/design/ReSonoTheme.java` | same relative path below `android/` | Copy exact |
| R1 key/wheel mapping | `core/input/src/main/java/com/resonolabs/ui/input/HardwareInputRouter.java`; `UiInputIntent.java`; `UiInputTarget.java` | same relative paths below `android/` | Copy exact |
| R1 input regression | `core/input/src/test/java/com/resonolabs/ui/input/HardwareInputRouterTest.java` | same relative path below `android/` | Copy exact |
| R1 display/power policy | `core/power/src/main/java/com/resonolabs/ui/power/DisplayPolicy.java` | same relative path below `android/` | Copy exact |
| Display regression | `core/power/src/test/java/com/resonolabs/ui/power/DisplayPolicyTest.java` | same relative path below `android/` | Copy exact |
| Real device settings | `feature/settings/src/main/java/com/resonolabs/feature/settings/SettingsPanelView.java`; `WifiNetworkScanner.java`; `SettingsInputPolicy.java` | same relative paths below `android/` | Copy, then narrow only hosted/irrelevant wording and unsupported rows |
| Settings regression | `feature/settings/src/test/java/com/resonolabs/feature/settings/SettingsInputPolicyTest.java` | same relative path below `android/` | Copy exact unless narrowed row names require correction |
| Fullscreen app theme | `app/src/main/res/values/styles.xml` | same relative path below `android/` | Copy exact |

Explicit exclusions include the reference app composition, enrollment/provisioning package, claim feature, Voice/Vault controllers, `PlatformPairingClient`, `DeviceRuntimeCoordinator`, `BootstrapConfig`, edge sync, camera/motor code, personal-data features, and all future feature modules. Native WebRTC remains frozen in the reference and enters only with the first real Voice producer/consumer.

3. **Build the clean product APK.**
   - Create one Gradle product tree at `android/` with only the modules required by Checkpoint 2.
   - Use a direct HOME lifecycle and a narrowly named Android system-setup/boot handoff only where the accepted image requires it.
   - Apply the complete New Browser Voice design system—not only its colors—to the real HOME/settings surface without adding future feature controls. Preserve its hierarchy, wording, typography, icon language, gradients, glass/card construction, spacing, radii, borders, shadows, controls, navigation, states, and motion, scaled for 480×640 and R1 hardware input.
   - Build and run unit/source-boundary tests.

4. **Physical product proof.**
   - Preserve the accepted image and version-code-3 reference APK rollback paths.
   - Install only the reviewed clean engineering APK on the test R1 after immediate owner authorization.
   - Verify cold HOME launch, reboot, touch, side button, wheel, navigation, fullscreen/display policy, real settings actions, package identity/signing/grants, absence of hosted gates, and rollback.
   - Camera remains deferred and is not touched.

## Scope

### Required now

- Reference preservation with exact provenance.
- One clean Android product composition.
- HOME lifecycle on the accepted ReSono image.
- Real R1 touch/button/wheel input and navigation.
- Real display/fullscreen/power policy.
- Minimum real device settings needed to operate the engineering R1.
- New Browser Voice visual tokens applied only to implemented surfaces.
- Build, boundary, regression, physical, and rollback evidence.

### Explicitly outside this contract

- On-device Python/runtime packaging.
- Browser management or pairing.
- OpenAI authentication, model selection, Agents SDK execution, or Realtime Voice.
- WebRTC source import before a real Voice producer/consumer exists.
- Mail, Calendar, Contacts, Reminders, memory, Skills, Plugins, MCP, A2A, Hermes, External AI, or ChatGPT integration.
- Camera work.
- Image package removal or partition changes.
- Mock screens, disabled future buttons, sample data, fake health, or facade endpoints.

These capabilities remain required by grounding and later delivery slices. Their exclusion here is sequencing, not feature removal.

## Functional invariants

| ID | Invariant | Observable control and required failure | Wrong-but-well-formed counterexample |
|---|---|---|---|
| BC3-I01 | Reference and product are unambiguous. | Reference lives only below `reference/android-voice-platform/`; product builds only from `android/`. CI/source checks fail if product depends on reference source paths. | Both trees compile into the APK, so old enrollment code remains reachable. |
| BC3-I02 | Donors remain read-only. | Before/after donor status and hashes must match; stop before any operation resolving outside this repository. | A convenient rename or cleanup occurs in the Voice donor. |
| BC3-I03 | Product startup is standalone. | HOME reaches its real implemented surface without network, ReSono Admin, Cloud bootstrap, claim, serial, or external Vault state. Any such dependency fails acceptance. | Enrollment overlay is renamed “setup” but still contacts the hosted API. |
| BC3-I04 | Reuse is selective and proven. | Every copied file has recorded provenance, retained function, excluded function, dependency reason, and test. Unmapped files fail the import gate. | The whole donor `app/` module is copied because it already builds. |
| BC3-I05 | No future feature is mocked. | Only implemented HOME/settings behaviors are visible. Future Voice/runtime/plugin/provider controls are absent until connected to real behavior. | A polished Voice button displays “coming soon” or fake activity. |
| BC3-I06 | Hardware behavior is physical, not structural. | Real device input events navigate real surfaces; unsupported/unrecognized events do not escape into vendor fallback. Unit mappings alone cannot pass. | Input-router tests pass while the wheel does nothing on the R1. |
| BC3-I07 | The accepted image remains recoverable. | Exact reference APK and image rollback hashes/commands pass before install. Stop if package signer/identity or recovery differs. | Clean APK is installed after overwriting the only known-good artifact. |
| BC3-I08 | Deferred capabilities remain traceable. | WebRTC and every accepted feature keep exact donor references and later delivery ownership; none may be marked implemented here. | Excluding WebRTC now is misreported as removing Voice from the product. |
| BC3-I09 | Known-good APK evidence is permanent. | The exact original donor and tested version-code-3 reference APK hashes must pass before reference relocation, clean builds, and physical install. These artifacts are never overwritten by build output. | A new `app-debug.apk` is copied over the only APK known to have working wheel/button/motor/Voice wiring. |
| BC3-I10 | Native R1 and Browser Voice are one visual product. | A component/state inventory traces each implemented native surface to the exact Browser Voice component, CSS rule group, icon, wording, and interaction state. Owner side-by-side physical acceptance controls exit. | The APK copies blue colors but keeps the old native typography, text glyph icons, flat cards, spacing, navigation, or language. |
| BC3-I11 | Product navigation starts Voice, then Cards. | The real Voice vertical owns launch/HOME position one; the real locally backed Cards vertical owns position two. Until then, the settings-only clean shell is not presented as final HOME and no fake pages are drawn. | A generic settings launcher remains the released HOME, or polished empty Voice/Cards facades are added before their behavior. |

## Material Decision Gates

### BC3-MDG-01 — Reference versus continued cleanup

- **Question:** Continue deleting hosted behavior from the imported tree, rewrite proven components, or preserve it and create one clean product composition?
- **Authority/evidence:** OD-01–OD-03, OD-18, OD-22–OD-26; working version-code-3 reference APK; owner instruction to build the APK from the ground up while reusing proven WebRTC/hardware behavior.
- **Alternatives:** Endless donor cleanup; total rewrite; preserved reference plus selective ports; blocked.
- **Selection/function:** Preserve the imported tree under `reference/` and build one clean product tree. This keeps known-working evidence while preventing hosted architecture from defining the standalone product.
- **Counterexample:** Product `MainActivity` still implements Platform/Vault enrollment or pairing interfaces.
- **Dependents:** Repository structure and every later Android import.
- **Result:** `CONTINUE` after owner accepts this contract.

### BC3-MDG-02 — First clean APK behavior

- **Question:** Copy every future feature immediately, show a product shell with placeholders, or prove only the smallest real native operating surface?
- **Authority/evidence:** OD-01–OD-03, no-mockups rule, accepted dependency order.
- **Alternatives:** Broad port; placeholder shell; real HOME/input/power/settings vertical; blocked.
- **Selection/function:** Real HOME/input/power/settings only. It proves the clean APK and physical device boundary without dead feature code or fake UI.
- **Counterexample:** The interface includes provider/model/Voice controls that cannot complete their named action.
- **Dependents:** Checkpoints 2–4 and the next runtime/Voice contracts.
- **Result:** `CONTINUE` after owner accepts this contract.

### BC3-MDG-03 — WebRTC timing

- **Question:** Port native WebRTC now as unused code, rewrite it later, or port the proven implementation with the first real Voice session?
- **Authority/evidence:** OD-03, OD-18; donor `NativeVoicePeer` is proven but its current orchestration is coupled to Platform/Vault flows.
- **Alternatives:** Dead early import; rewrite; exact later port with real provider/runtime consumers.
- **Selection/function:** Preserve its exact reference now and port it in the real Voice vertical. No rewrite is authorized.
- **Counterexample:** Contract 03 ships a Voice UI without a working Realtime session, or a later contract invents a replacement peer without first testing the proven implementation.
- **Dependents:** Android module size now and Delivery Slice 4 later.
- **Result:** `CONTINUE`.

### BC3-MDG-04 — Physical install

- **Question:** Install while composing, test only off-device, or freeze/test the clean candidate and rollback before one gated install?
- **Authority/evidence:** Accepted image/recovery evidence and Phase 03 physical-mutation rules.
- **Selection/function:** Offline Checkpoints 1–3 first; immediate owner authorization before exact Checkpoint 4 install.
- **Counterexample:** A partially built clean app replaces HOME before signer, rollback, and direct-start behavior are known.
- **Dependents:** Checkpoint 4.
- **Result:** `BLOCKED/REOPEN` for device mutation; `CONTINUE` for offline work after contract acceptance.

### BC3-MDG-05 — Meaning of “match New Browser Voice”

- **Question:** Match only colors, create an R1-specific inspired theme, embed a desktop WebView, or implement the same visual system natively and responsively?
- **Authority/evidence:** OD-22, OD-23, OD-28; owner clarification that Browser Voice should be shrunk to the R1 and the difference should be barely perceptible.
- **Alternatives:** Palette match; separate native theme; desktop WebView; responsive native implementation of the same system; blocked.
- **Selection/function:** Responsive native implementation of the complete Browser Voice system. The R1 keeps native lifecycle and physical input, while appearance, wording, component identity, state language, and motion remain Browser Voice.
- **Counterexample:** A screenshot uses similar colors but a reviewer immediately identifies it as the old R1 UI rather than Browser Voice.
- **Dependents:** Native design primitives, HOME/settings rendering, visual tests, physical acceptance, and every later R1 feature surface.
- **Result:** `CONTINUE`; the palette-only internal APK is rejected and Checkpoint 3 visual implementation is reopened.

## Tests and evidence

### Positive

- Reference move preserves the recorded source set and builds from its new location.
- Clean project has a deterministic build command and contains only approved modules/files.
- Source-boundary tests prove no product dependency on the reference tree or prohibited hosted packages/classes/URLs.
- Unit tests prove input mapping, navigation state, boot intent handling, and settings actions.
- APK inspection proves expected package, signer, HOME activity, permissions, and absence of prohibited components.
- Physical tests prove real touch/button/wheel, HOME/reboot, display policy, settings, and rollback.

### Negative

- Build fails if product imports or includes enrollment, claim, serialization, Platform pairing, Vault relay/control, edge sync, Cloud bootstrap, or the hosted provisioning URL.
- No future feature control or mock state appears.
- Unknown or unused module imports fail review.
- Wrong signer/application ID, unavailable rollback, device mismatch, or hardware regression stops install/acceptance.
- Donor before/after state differs: stop and restore only standalone work; never “fix” the donor.

## Stop, rollback, and exit

- Checkpoints stop on provenance mismatch, donor mutation, ambiguous dependency, prohibited hosted code, fake/disconnected UI, build/test failure, signer mismatch, missing rollback, or physical regression.
- Before physical install, reversal is the exact standalone directory move plus removal of newly created product files if the owner requests rollback.
- Physical rollback reinstalls the preserved version-code-3 reference APK; image rollback remains the accepted Build Contract 02 route.
- Contract exit requires objective build/boundary evidence, real R1 behavior, rollback proof, separated implementation review, and owner physical acceptance.
- Passing this contract does not claim runtime or Voice completion.

## Current authorization

The owner accepted this contract with the instruction “continue” on 2026-08-14. Offline Checkpoints 1–3 are authorized. Checkpoint 4 requires a second immediate owner confirmation for the exact tested APK installation.

## Interim visual review finding

The first clean APK proved the five-module architecture, build, signer, hosted-code exclusion, and focused unit tests. Review against the actual Browser Voice source found that its visible HOME/settings composition retained the older native presentation and treated theme equivalence too narrowly. Artifact `artifacts/android-candidates/ReSonoR1-clean-home-v0.2.0.apk` is retained as internal failure evidence only. It is not an install candidate and cannot satisfy Checkpoint 3. The visual implementation is reopened under OD-28; architectural and reference-preservation evidence remains valid.

Owner clarification OD-29 fixes the product page order as Voice first and Cards second. Visual work now establishes the shared native design primitives, but the two pages cannot be exposed as product UI until their real vertical behavior is connected. Pixel-level fine tuning may follow broader product completion; structural fidelity and the no-mockups boundary apply immediately.
