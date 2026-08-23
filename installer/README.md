# JackRabbit Installer

This directory contains the complete prompt-driven installer source and the
metadata for the current image set. Downloadable releases contain the images
once and four small host launchers: Linux x64, Windows x64, macOS Apple Silicon,
and macOS Intel.

Download the complete `jackrabbit-current-v0.2.zip` from the
[public Google Drive folder](https://drive.google.com/drive/folders/1iteItXoQ3cVqyN4DhChQ3EOBlv68f8wM?usp=drive_link).
Extract the entire ZIP and keep its `release/` and `hosts/` directories together.
See [`INSTALL.md`](INSTALL.md) for the verified download size, SHA-256, exact
layout, and OS-specific start command.

- `images/` — exact image and host-dependency manifests
- `cli/` — the shared Rust flashing program
- `linux-macos/` — Unix launchers and Linux USB rule
- `windows/` — Windows launcher and driver setup
- `scripts/` — release assembly only
- `INSTALL.md` — stock R1 through first boot
- `TROUBLESHOOTING.md` — recovery and error guidance

The installer verifies all 12 images before device access, detects or enters
FASTBOOT, unlocks a locked bootloader with confirmation, flashes the complete
fixed image route, erases userdata, selects slot A, and reboots.

JackRabbit is source-available only for noncommercial community use under the
repository's [PolyForm Noncommercial License 1.0.0](../LICENSE). Commercial use,
commercial licensing, and monetized distribution are not permitted or offered.
