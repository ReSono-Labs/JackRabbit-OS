# Images

`RELEASE.json` lists the exact 12 image files, sizes, and SHA-256 hashes used by
the current installer. The multi-gigabyte `.img` files are distributed in the
[complete Google Drive bundle](https://drive.google.com/drive/folders/1iteItXoQ3cVqyN4DhChQ3EOBlv68f8wM?usp=drive_link)
under `release/images/`; they are not stored as Git blobs.

`HOST-DEPENDENCIES.json` pins the Platform Tools and Windows drivers packaged
with each host launcher. `PROMPTS.json` contains the physical R1 instructions
embedded in every native installer executable.
