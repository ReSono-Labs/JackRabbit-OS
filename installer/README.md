# JackRabbit Installer

This directory contains the complete prompt-driven installer source and the
metadata for the current image set. Downloadable releases contain the images
once and four small host launchers: Linux x64, Windows x64, macOS Apple Silicon,
and macOS Intel.

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
