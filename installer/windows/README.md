# Windows installer package

Download `jackrabbit-current-v0.2.zip` from the
[public Google Drive folder](https://drive.google.com/drive/folders/1iteItXoQ3cVqyN4DhChQ3EOBlv68f8wM?usp=drive_link),
then extract the complete ZIP. Do not move this host directory away from the
extracted bundle's sibling `release/` directory.

`install.cmd` opens the prompt-driven Windows installer. Its host directory
contains `jackrabbit-installer.exe`, Android Platform Tools `fastboot.exe`, and
the two reviewed upstream driver packages. It uses the bundle's one shared
top-level `release/images/` directory:

- Rabbit's signed MediaTek Preloader USB VCOM installer for Windows 10/11.
- Google's USB Driver r13, whose signed INF explicitly owns fastbootd identity
  `USB\\VID_18D1&PID_4EE0`.

The first prompt offers to install or repair both driver layers using the normal
Windows administrator consent dialog. The CLI itself then runs as the normal
user. Driver installation completes before any R1 partition write.

Double-click `install.cmd` and follow the prompts. The package never asks the
user to type a partition name, image path, or raw fastboot command.

Read `INSTALL.md` for the complete stock-R1 installation flow and bundled image
layout. Read `TROUBLESHOOTING.md` before retrying after an error. Both files are
included at the root of every public package.
