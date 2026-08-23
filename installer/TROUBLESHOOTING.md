# JackRabbit installer troubleshooting

Use the stable `JR-...` code printed at the beginning of the terminal error.
Keep the complete code and message when reporting a problem.

## First decide whether a transfer is still active

- If the terminal is still showing transfer progress and has not returned to a
  command prompt, do not unplug the R1. A blank R1 display during the stock
  `super` write is expected.
- If the installer printed a `JR-...` error and returned to the command prompt,
  it stopped before starting the next operation. Leave the R1 connected if it
  still shows FASTBOOT or fastbootd.
- To recover after a stopped write, run the corrected package launcher again.
  It detects bootloader FASTBOOT or fastbootd, returns to the reviewed starting
  mode when necessary, verifies the package and device again, and restarts the
  complete fixed route. It does not guess where a partial write stopped.

Never use an arbitrary internet command or manually choose a partition to work
around an installer failure.

## Common situations

### The R1 already shows FASTBOOT or fastbootd

Leave it connected and start the package launcher. The installer detects both
modes. An R1 found in fastbootd is verified and returned to bootloader FASTBOOT
before the guided route restarts.

### The installer is waiting for the R1

Connect exactly one R1 with a data-capable cable. The wait accepts an R1 already
showing FASTBOOT, an R1 in fastbootd, or the exact powered-off R1 preloader.
Close Rabbit's web flasher, other WebUSB pages, `adb`, and other `fastboot`
processes so only this installer owns the USB device.

### Linux reports permission denied or `no permissions`

Run the package's `./install.sh`, not the binary inside `bin/`. Allow it to
install `drivers/51-jackrabbit-r1.rules`, then reconnect the R1 when prompted.
The rule covers the preloader, bootloader FASTBOOT, and fastbootd USB identities.
Do not run the JackRabbit installer binary with `sudo`.

### Windows cannot see the R1 after its mode changes

Run `install.cmd` again and choose the included driver install/repair path.
Approve the Rabbit MediaTek preloader driver and Google fastboot driver prompts.
Windows treats the preloader, bootloader FASTBOOT, and fastbootd as different
USB interfaces, so one working mode does not prove the next driver is installed.

### macOS cannot open the R1 USB connection

Close every browser flasher and Android tool that could own the R1, disconnect
and reconnect the cable, and rerun `install.command`. macOS needs no packaged
R1 driver.

### An entry was typed incorrectly

The installer asks whether to cancel. Type `Y` only to cancel; otherwise press
Enter to return to the same prompt. Destructive confirmation phrases must match
the displayed phrase exactly.

## CLI error reference

| Code | Meaning | Resolution |
|---|---|---|
| `JR-CLI-COMMAND` | The requested CLI command is not part of the guided interface. | Start the package launcher, or use only `install`, `prepare`, `diagnose`, or `version` as shown by `--help`. |
| `JR-CLI-ARGUMENT` | A supported CLI command received the wrong number of arguments. | Start the package launcher. For a manual invocation, pass exactly one complete `release/` directory to `install`. |
| `JR-CLI-RELEASE-MISSING` | A required packaged image is absent. | Extract the complete package again. Do not copy images individually. |
| `JR-CLI-RELEASE-SIZE` | A packaged image has the wrong byte size. | Replace the entire package with an unmodified copy of the same release. |
| `JR-CLI-RELEASE-HASH` | A packaged image does not match its required SHA-256. | Delete that extracted package and obtain a clean complete release. Do not continue. |
| `JR-CLI-RELEASE-READ` | The installer could not read an image. | Check extraction, file permissions, available storage, and filesystem errors; then extract a clean package. |
| `JR-CLI-FASTBOOT-MISSING` | The packaged native fastboot program is missing or cannot run. | Extract the complete package for the correct operating system and architecture. |
| `JR-CLI-DEVICE-COUNT` | Zero or more than one R1 is visible in native FASTBOOT. | Connect exactly one R1; close competing USB tools and check the cable/drivers. |
| `JR-CLI-USB-PERMISSION` | Linux denied access to an R1 USB identity. | Run `./install.sh`, allow the udev-rule setup, reconnect when prompted, and retry the same flow. |
| `JR-CLI-FASTBOOT-ENTRY-TIMEOUT` | No supported R1 preloader, FASTBOOT, or fastbootd identity appeared within 60 seconds. | Confirm the R1 is powered off or already in a supported fastboot mode, use a data cable, connect exactly when prompted, and rerun. |
| `JR-CLI-PRELOADER-ENUMERATE` | The host could not enumerate serial devices. | Close competing serial tools, check the OS driver/permission setup, reconnect, and rerun. |
| `JR-CLI-PRELOADER-COUNT` | More than one exact R1 preloader appeared. | Disconnect all R1 devices except the intended one. |
| `JR-CLI-PRELOADER-OPEN` | The exact R1 preloader port could not be opened. | Close Rabbit's flasher and serial tools; on Linux rerun `install.sh`; on Windows repair the packaged drivers. |
| `JR-CLI-PRELOADER-WRITE` | The eight-byte R1 FASTBOOT-entry command could not be sent. | Reconnect the powered-off R1 with a reliable data cable and rerun the package. |
| `JR-CLI-PRODUCT` | The connected fastboot device is not the reviewed R1 product. | Stop. Connect only the Rabbit R1 intended for installation. |
| `JR-CLI-SLOT` | The R1 did not report the required slot A starting contract. | Stop and preserve the exact output. Do not manually change slots; report the code for installer review. |
| `JR-CLI-MODE` | The R1 did not reach the expected bootloader FASTBOOT or fastbootd mode. | Leave it connected, close competing tools, and rerun the package so mode normalization starts again. |
| `JR-CLI-MODE-TIMEOUT` | The R1 did not reconnect in the requested mode within 90 seconds. | Check the screen, cable, and mode-specific host driver/permission, then rerun the complete package flow. |
| `JR-CLI-LOCKED` | A write gate found the bootloader still locked. | Confirm **r1 bootloader unlock** is enabled in Rabbithole, follow the on-device unlock confirmation, and rerun. |
| `JR-CLI-UNLOCK` | The two unlock commands completed without the R1 reporting unlocked. | Stop. Recheck Rabbithole authorization and preserve the complete terminal output before retrying. |
| `JR-CLI-FASTBOOT-VALUE` | The R1 did not return a required identity/state value. | Close competing tools, reconnect, and retry. If repeated, preserve the full output and stop. |
| `JR-CLI-FASTBOOT-FAILED` | Native fastboot reported a remote or host failure. | Preserve the complete message. Check USB stability and host access, then rerun the complete package. Any expected absent `system_ext_a` response is handled automatically and should not surface as this error. |
| `JR-CLI-SYSTEM-EXT` | `system_ext_a` exists with an unexpected layout after the stock-super reset. | Stop and preserve the output. Rerun only with the corrected complete package; if it repeats, report it rather than issuing manual partition commands. |
| `JR-CLI-CANCELLED` | The user chose to stop before the next mutation or during a safe wait. | Restart the package when ready. If the R1 shows FASTBOOT or fastbootd, leave it in that state. |
| `JR-CLI-PROMPT-CONTRACT` | The executable's embedded physical instruction contract is invalid or unsupported. | Replace the entire package with a clean official build. Do not continue with that executable. |
| `JR-CLI-IO` | Terminal input/output failed. | Open a normal interactive terminal and rerun the package launcher. |

The separate read-only `diagnose` command can also report
`JR-CLI-DEVICE-MISSING`, `JR-CLI-DEVICE-MULTIPLE`, `JR-CLI-USB`,
`JR-CLI-FASTBOOT-TIMEOUT`, `JR-CLI-FASTBOOT-REJECTED`, or
`JR-CLI-FASTBOOT-VALUE`. These mean the diagnostic could not obtain one complete
read-only R1 snapshot. They do not indicate that a partition was written.

## What to include in an issue report

Include:

- operating system and architecture;
- package directory name;
- the complete `JR-...` code and message;
- the last numbered operation shown;
- whether the R1 screen says FASTBOOT, fastbootd, is blank, or has booted;
- whether the terminal returned to its command prompt; and
- whether the cable was disconnected or the host slept during the attempt.

Do not publish the R1 serial number or account information.
