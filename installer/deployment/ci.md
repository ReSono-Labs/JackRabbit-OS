# Installer CI boundary

The repository-root `installer-ci.yml` is path-scoped to this independent
installer build. It pins Node 24.14.1, Rust 1.85.0, and every referenced action
to an immutable commit.

The Ubuntu job proves the isolated source/web/CLI build and dependency gates.
The platform matrix compiles and unit-tests the CLI on GitHub's documented
Ubuntu 24.04 x64, Windows 2025 x64, macOS 15 arm64, and macOS 15 Intel runners.
Each successful runner retains its native executable for 14 days as
`jackrabbit-native-PLATFORM`.

A green matrix proves the native binaries but does not physically exercise USB,
sign/notarize code, or make a host tuple supported. Download the four artifacts
into one directory without renaming their artifact directories, then assemble
the complete packages on the release host:

```sh
./scripts/assemble-host-packages.sh NATIVE_ARTIFACT_DIRECTORY VERIFIED_RELEASE_DIRECTORY
```

The assembly command requires all four native artifacts before writing output,
verifies all 12 release images, stages the pinned Platform Tools and Windows
drivers, builds all four package directories, and compares their source files,
executables, and image hashes. Physical R1 acceptance remains a separate gate.
