# Install JackRabbit on a stock Rabbit R1

This guide starts with a stock Rabbit R1 and ends with the current complete
JackRabbit image. The guided installer handles FASTBOOT entry, the locked or
unlocked bootloader branch, every required image write, userdata erasure, slot
selection, and reboot.

Installation erases all user data on the R1. Back up anything needed before
starting. Keep the R1 charged, use a reliable data-capable USB cable, and do not
unplug it while an image transfer is active.

## Choose the package for the computer

Download and extract exactly one complete package:

| Computer | Package directory | Start it with |
|---|---|---|
| Linux x64 | `jackrabbit-linux-x64-current-v0.1` | `./install.sh` |
| macOS Apple Silicon | `jackrabbit-macos-arm64-current-v0.1` | Double-click `install.command`, or run `./install.sh` |
| macOS Intel | `jackrabbit-macos-x64-current-v0.1` | Double-click `install.command`, or run `./install.sh` |
| Windows x64 | `jackrabbit-windows-x64-current-v0.1` | Double-click `install.cmd` |

Do not run an installer from inside the ZIP file. Extract the entire package
first and keep its files and directories together.

## Do not select or move image files

The package already contains every required image. The normal launcher always
uses its own `release/` directory. A user does not select an image directory,
partition, or individual `.img` file.

The required internal layout is:

```text
PACKAGE_DIRECTORY/
├── install.sh                         Linux and macOS
├── install.command                    macOS only
├── install.cmd                        Windows only
├── install.ps1                        Windows only
├── bin/
│   └── jackrabbit-installer[.exe]
└── release/
    ├── tools/
    │   └── fastboot[.exe]
    └── images/
        ├── stock/
        │   ├── boot.img
        │   ├── super.img
        │   ├── vbmeta.img
        │   ├── vbmeta_system.img
        │   └── vbmeta_vendor.img
        ├── jackrabbit/
        │   ├── system.img
        │   └── product.img
        └── cipheros/
            ├── system_ext.img
            ├── vendor.img
            ├── vbmeta.img
            ├── vbmeta_system.img
            └── vbmeta_vendor.img
```

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
to `scripts/stage-host-package.sh` must be the complete verified directory whose
root contains `images/` in the exact layout shown above. It is not an individual
image and not the package directory itself. The staging script places that
directory at `PACKAGE_DIRECTORY/release/` and adds the matching native CLI,
Platform Tools, launchers, host drivers, and these user documents.

The four native executables are built by the installer CI matrix. After
downloading its four `jackrabbit-native-PLATFORM` artifact directories, use
`scripts/assemble-host-packages.sh` to require the complete set and assemble all
four OS packages from one verified release directory.
