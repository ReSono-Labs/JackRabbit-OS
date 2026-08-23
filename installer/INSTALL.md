# Install JackRabbit on a stock Rabbit R1

This guide starts with a stock Rabbit R1 and ends with the current complete
JackRabbit image. The guided installer handles FASTBOOT entry, the locked or
unlocked bootloader branch, every required image write, userdata erasure, slot
selection, and reboot.

Installation erases all user data on the R1. Back up anything needed before
starting. Keep the R1 charged, use a reliable data-capable USB cable, and do not
unplug it while an image transfer is active.

## Download and extract the complete bundle

1. Open the [public JackRabbit Google Drive folder](https://drive.google.com/drive/folders/1iteItXoQ3cVqyN4DhChQ3EOBlv68f8wM?usp=drive_link).
2. Download the file named exactly `jackrabbit-current-v0.2.zip`. Do not
   download individual `.img` files or an individual OS folder.
3. Confirm the downloaded ZIP is exactly `2,179,959,244` bytes. Its SHA-256 is
   `5bdd9c63d3390783c4722d7a877806222f5370171b15b2b4b1880f1ff1c54207`.
4. Make sure the computer has at least 8 GB free on the disk used for the
   download and extraction.
5. Extract the complete ZIP in any convenient local directory. Do not run it
   from inside the ZIP.
6. Open the extracted `jackrabbit-current-v0.2` folder. It must directly
   contain `START-HERE.md`, `release/`, and `hosts/`.

The ZIP does not need to be moved to a special installer directory. The
installers are already inside it. The `hosts/PLATFORM` launchers locate images
at `../../release` relative to themselves. Keep the extracted `hosts/` and
`release/` directories together exactly as provided; moving either one breaks
that verified path and causes installation to stop before writing.

Optional checksum commands:

```text
Linux:   sha256sum jackrabbit-current-v0.2.zip
macOS:   shasum -a 256 jackrabbit-current-v0.2.zip
Windows: Get-FileHash .\jackrabbit-current-v0.2.zip -Algorithm SHA256
```

## Choose the installer for the computer

Inside the extracted `jackrabbit-current-v0.2` folder, choose the host directory
matching the computer:

| Computer | Package directory | Start it with |
|---|---|---|
| Linux x64 | `hosts/linux-x64` | `./install.sh` |
| macOS Apple Silicon | `hosts/macos-arm64` | Double-click `install.command`, or run `./install.sh` |
| macOS Intel | `hosts/macos-x64` | Double-click `install.command`, or run `./install.sh` |
| Windows x64 | `hosts/windows-x64` | Double-click `install.cmd` |

The image files must be present on the local computer while flashing; fastboot
cannot write them directly from Google Drive or another remote site. Downloading and extracting the complete
bundle puts them in the correct location automatically. After installation has
completed successfully and the R1 has booted, the extracted bundle may be
deleted from the computer.

## Do not select or move image files

The bundle contains every required image once. Every OS launcher automatically
uses the same top-level `release/` directory. A user does not select an image
directory, partition, or individual `.img` file.

The required internal layout is:

```text
BUNDLE_DIRECTORY/
├── release/
│   └── images/
│       ├── stock/
│       │   ├── boot.img
│       │   ├── super.img
│       │   ├── vbmeta.img
│       │   ├── vbmeta_system.img
│       │   └── vbmeta_vendor.img
│       ├── jackrabbit/
│       │   ├── system.img
│       │   └── product.img
│       └── cipheros/
│           ├── system_ext.img
│           ├── vendor.img
│           ├── vbmeta.img
│           ├── vbmeta_system.img
│           └── vbmeta_vendor.img
└── hosts/
    ├── linux-x64/
    ├── macos-arm64/
    ├── macos-x64/
    └── windows-x64/
```

Each host directory contains only its launcher, native installer executable,
matching `tools/fastboot`, required host driver files, and documentation. It
does not contain another copy of `release/images/`.

If any file is missing, moved, renamed, changed, or from a different release,
the installer stops before device access or writing.

## Prepare the R1

1. Open Rabbithole in a browser and select the R1.
2. Open **Settings → Developer → Device modification**.
3. Enable **r1 bootloader unlock**. The setting takes effect immediately when
   Rabbithole shows it enabled.
4. Back up anything needed from the R1.
5. Follow the installer screen. It will tell you when the R1 must be powered
   off, disconnected, or connected.

Do not use Rabbit's **Flash Stock ROM** action. The JackRabbit package performs
its own complete fixed installation route.

## Run the installer

### Linux

Open a terminal in the extracted package directory:

```sh
./install.sh
```

The first run may request administrator approval to install one narrow R1 USB
access rule. The flash program itself continues as the normal desktop user.

### macOS

Double-click `install.command`. If macOS requires a terminal launch, open a
terminal in the extracted package directory and run:

```sh
./install.sh
```

No separate R1 driver is required on macOS. Close Android tools or browser
flashers that may already own the R1 USB interface.

### Windows

Double-click `install.cmd`. Accept the driver-setup prompt unless the packaged
Rabbit MediaTek and Google fastboot drivers are already installed and working.
Windows may show an administrator-consent dialog for driver installation; the
JackRabbit flash program itself does not run as Administrator.

## What the guided flow does

The installer:

1. Verifies the size and SHA-256 of all 12 packaged images.
2. Detects an R1 already in bootloader FASTBOOT or fastbootd. If neither is
   present, it waits for the powered-off preloader and sends the reviewed R1
   FASTBOOT-entry command.
3. Verifies the exact R1 product, mode, slot, and unlock state.
4. If locked, asks for an explicit erase/unlock confirmation, runs the two R1
   unlock commands, waits for on-device confirmation, verifies the result, and
   rejoins the main installation flow.
5. Writes both boot slots and the required verified-boot metadata.
6. Enters fastbootd, resets stock `super`, creates the CipherOS
   `system_ext_a` partition, and writes the JackRabbit/CipherOS logical images.
7. Returns to bootloader FASTBOOT, activates the final verified-boot metadata,
   erases userdata, selects slot A, and reboots.

The R1 display can go blank while `super.img` is being written and can remain
blank during early first boot. This is expected. Keep the cable connected and
follow the terminal while a transfer is still running.

## Successful completion

The terminal must report:

```text
Image transfer complete.
```

After that message, keep the R1 powered and allow the first boot to finish. A
successful transfer and a successful Android first boot are separate events.

If the installer returns an error code instead, use
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md). Do not improvise partition commands.

## Release-builder input

This section is for project release builders, not end users. The third argument
to `scripts/stage-host-package.sh` must be the bundle's complete verified
`release/` directory. It is not an individual image. The staging script adds
only the matching native CLI, Platform Tools, launchers, host drivers, and user
documents under `hosts/PLATFORM/`.

The four native executables are built by the installer CI matrix. After
downloading its four `jackrabbit-native-PLATFORM` artifact directories, use
`scripts/assemble-host-packages.sh` to require the complete set and assemble all
four OS packages from one verified release directory.
