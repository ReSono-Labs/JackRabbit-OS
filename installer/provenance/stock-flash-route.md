# Stock R1 flashing route provenance

## Rabbit-owned entry and authorization

Rabbit's developer-mode article and hosted flasher were reviewed, not copied.
They establish the user-owned Rabbithole developer/unlock step and the R1
preloader transition: Web Serial selects `0e8d:2000` and sends the eight bytes
`FASTBOOT`; WebUSB then selects Fastboot `0e8d:201c`.

`web/src/preloader/enter-r1-fastboot.mjs` retains only that exact entry behavior.
It omits Rabbit's stock flashing, relock, generic device detection, UI, logging,
and recovery copy. Its byte-level tests are in
`web/tests/enter-r1-fastboot.test.mjs`.

## CipherOS partition transition

- Source revision: `14b1ee3a1ee62dbed1a79ac49764c5dd22b0547b`
- Source path: `scripts/flash-cipheros.sh`
- License: Apache-2.0
- Destination: `cli/src/install.rs`, `cli/src/fastboot.rs`, and
  `cli/src/release.rs`

Retained behavior is the stock `boot.img` requirement, six initial VBMeta
writes with verification disabled, bootloader-Fastboot to Fastbootd transition,
clean stock `super.img`, exact `system_ext_a` size `559304704`, four logical
partition writes, return to bootloader Fastboot, userdata erase, slot A, and
reboot. JackRabbit replaces only the source `system.img` and `product.img` with
the project's frozen accepted images.

Rabbit's hosted `stock-flash.js` also establishes the locked-stock sequence:
after Rabbithole authorization it sends `flashing unlock` and then
`flashing unlock_critical`. The destination exposes those commands only inside
the guided install's locked-device branch with an exact data-erasure
confirmation. It verifies `unlocked: yes` and rejoins the same install flow.

Omitted behavior includes the donor's terminal colors, root/module changes,
arbitrary input directories, optional unverified stock-boot pause, generic
post-install shell commands, and any bootloader lock. The destination adds
exact file hashes, exact R1 product/mode/slot/unlock gates, one-device
selection, a fixed native-fastboot adapter, the Linux fastbootd USB identity
and udev rule, the physically observed blank-screen warning, and an exact
destructive confirmation.

Tests validate the CLI's closed command surface, exact release inventory,
destructive confirmation, missing-release-before-device gate, udev identities,
and repository boundary suite. Raw fastboot, partition, URL, and file commands
remain unavailable.

## Fastboot transports

`kdrag0n/fastboot.js` revision `5b613332aa9d66cca5bebb49f147cd084a76c464`
is adopted through the exact MIT-licensed `android-fastboot@1.1.3` package. It
provides WebUSB payload transfer, sparse conversion/splitting, partition flash,
commands, and reboot operations. `web/src/fastboot/flash-stock-r1.mjs` closes it
behind the exact R1 product/slot/unlock/mode gates and the same fixed partition
order as the CLI. `web/src/release/stock-r1-release.mjs` pins every selected
image's byte size and SHA-256; the browser verifies the complete selected
package before enabling the destructive install action.

The development CLI uses native fastboot from `PATH` when no packaged binary is
present. A public host package must include or securely obtain one exact pinned
platform fastboot binary. Those binaries are generated release output and are
not committed. Public distribution must resolve Google's redistribution terms
or download and verify the official tool on the user's machine.
