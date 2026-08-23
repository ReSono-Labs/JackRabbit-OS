# Linux and macOS installer package

Download `jackrabbit-current-v0.2.zip` from the
[public Google Drive folder](https://drive.google.com/drive/folders/1iteItXoQ3cVqyN4DhChQ3EOBlv68f8wM?usp=drive_link),
then extract the complete ZIP. Do not move this host directory away from the
extracted bundle's sibling `release/` directory.

`install.sh` is the prompt-driven launcher shared by Linux and macOS. Each host
directory contains this launcher, its native `jackrabbit-installer` binary, and
the matching Android Platform Tools `fastboot` binary. All host directories use
the bundle's one shared top-level `release/images/` directory.

Linux requires one administrator-approved host setup before the first install:
the package installs `drivers/51-jackrabbit-r1.rules` into
`/etc/udev/rules.d`. The rule grants the logged-in desktop user access only to
the three reviewed R1 USB identities. The installer and `fastboot` continue to
run as the normal user.

macOS uses the same installer engine and launcher without a driver or udev
installation. `install.command` is the Finder-friendly entry point and delegates
to `install.sh`. Release packages provide separate native CLI builds for Apple
Silicon (`macos-arm64`) and Intel (`macos-x64`); Google's bundled `fastboot` is
universal.

From the matching extracted host directory, run:

```sh
./install.sh
```

The launcher performs host setup before any device write, then invokes the
closed guided installer against the bundle's shared `release/` directory.

Read `INSTALL.md` for the complete stock-R1 installation flow and bundled image
layout. Read `TROUBLESHOOTING.md` before retrying after an error. Both files are
included at the root of every public package.
