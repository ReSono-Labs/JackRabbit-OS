# Shared CLI engine

The Rust command-line utility is the primary installer engine shared by the
Linux/macOS and Windows packages. It gives explicit prompts for every external
and on-device action and consumes the canonical contracts and conformance cases.

The CLI is implemented in Rust as one runtime-independent executable per
accepted host tuple. Its commands are `version`, `prepare`, fixed read-only
`diagnose`, and `install RELEASE_DIRECTORY`. Running it without arguments opens
a prompt-based menu. There is no arbitrary fastboot, partition, file, or URL
surface.

`install` verifies all twelve current-release image sizes and SHA-256 hashes
before device access, walks the stock-R1 preparation prompts, enters FASTBOOT
through only the exact `0e8d:2000` MediaTek preloader serial identity when the
device is not already there, and then runs the physically accepted 22-operation
stock-R1 route as the web installer: locked devices branch through Rabbit's
two-command unlock and rejoin the flow; bootloader FASTBOOT and fastbootd are
reverified after every transition; the stock super reset, `system_ext_a`
creation, four final logical images, prepared VBMeta bytes, userdata erase,
slot-A selection, and reboot are automatic. The CLI warns that the display may
go blank during the super write and identifies Linux fastbootd USB permission
failures explicitly.

Native fastboot output is treated as failed if either its process status fails
or its protocol output contains `FAILED`; some Platform Tools queries return a
zero process status alongside a remote failure. The one expected missing
`system_ext_a` response after the stock-super reset is classified explicitly
and causes the fixed-size logical partition to be created. Every other remote
failure stops the route before the next operation.

Preparation renders as one short terminal screen per physical action and clears
the previous action on interactive terminals. Device discovery runs before
those instructions: an R1 already in bootloader FASTBOOT is left connected and
the irrelevant power-cycle/entry steps are omitted. An R1 in fastbootd is
verified, returned to bootloader FASTBOOT automatically, re-verified, and then
given the same state-specific preparation flow. If the R1 is connected only
after preparation, the entry wait watches native FASTBOOT, fastbootd, and the
exact powered-off preloader concurrently instead of assuming only one state.
An incorrect response never exits a live prompt: the CLI asks whether to cancel
and otherwise returns to that same prompt. Explicit `q`/cancel choices still
stop before the next mutation.

The read-only diagnostic transport remains built into the executable. The
install transport invokes only structured, fixed commands through the pinned
native fastboot binary included in every public host package. PATH fallback is
development-only.

Development checks:

```sh
cargo test --manifest-path cli/Cargo.toml
cargo build --release --manifest-path cli/Cargo.toml
```

Linux packages include `linux-macos/drivers/51-jackrabbit-r1.rules` for the R1
preloader, bootloader FASTBOOT, and fastbootd USB identities. Windows packages
include Rabbit's official signed MediaTek preloader driver and Google's signed
USB driver for fastbootd. macOS requires no packaged USB driver. Host driver or
udev setup completes before device writes; the installer itself never runs as
root or Administrator.
