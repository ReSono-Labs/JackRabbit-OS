# Web adapter

The hosted HTTPS web installer is retained as a non-primary adapter. The public
install path is the packaged prompt-driven CLI because native host USB access
can carry the complete bootloader/fastbootd transition without browser claim
and user-gesture failures. This adapter uses Web Serial for
the exact R1 preloader FASTBOOT entry and WebUSB for the fixed bootloader
FASTBOOT (`0e8d:201c`) and fastbootd (`18d1:4ee0`) identities, unlock,
image-write, mode-transition, erase, slot, and reboot route.

Both device branches converge: an already-unlocked R1 proceeds directly to
package verification; a locked R1 runs Rabbit's two-command unlock sequence,
machine-verifies `unlocked: yes`, and then rejoins that same package step. The
user selects the extracted current release directory. All twelve image files
must match the sizes and SHA-256 values pinned in
`src/release/stock-r1-release.mjs` before the install button is enabled.

For the current local build, select this entire top-level directory when the
browser opens the package-folder chooser:

```text
installer/dist/releases/jackrabbit-stock-r1-current-v0.1
```

Select `jackrabbit-stock-r1-current-v0.1` itself. Do not select its `images`
subdirectory or an individual image file.

The release contains the complete current HOME, runtime, management UI, and
platform-signed motor service. There is no ADB post-install step. Prepared
VBMeta bytes are package inputs and are never modified in the browser.

`android-fastboot@1.1.3` is pinned for payload transfer and sparse splitting.
`src/fastboot/flash-stock-r1.mjs` owns the closed stock-R1 operation route and
re-verifies product, slot, unlock state, and mode after both USB reconnects.
Each reconnect has a visible button because browser device selection requires a
fresh user gesture. During the stock `super` write the R1 screen may go blank;
the page tells the user to keep the cable connected and follow transfer status.

## Host USB setup

- Linux requires a one-time administrator installation of the packaged
  `linux-macos/drivers/51-jackrabbit-r1.rules`. The browser and installer continue to
  run as the normal user; root is not used for flashing.
- Windows requires the R1 bootloader and fastbootd interfaces to use a
  WinUSB-compatible driver. The page identifies this requirement if access is
  denied.
- macOS has no Linux udev step. Competing adb, fastboot, or browser sessions
  must still be closed because only one process can claim the USB interface.

If access fails during a USB mode transition, the installer keeps the same
reconnect step and error visible. After the host permission or driver is fixed,
the user selects the R1 again and the installation resumes at that mode gate;
it does not silently discard the active flow.
