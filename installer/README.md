# JackRabbit Installer

This is the independent installer project for ReSono Labs R1 Voice. Its primary
delivery is a prompt-driven command-line package split by host operating system:
`linux-macos/` and `windows/`. Both packages use the same closed Rust installer
engine, exact release verification, locked/unlocked branch, fixed
JackRabbit/CipherOS image-transfer route, and reboot. The current product is
complete inside the flashed images; there is no ADB post-install step.

The hosted web adapter remains source-reviewed but is not the primary public
install route. The packaged CLI now owns stock-to-FASTBOOT entry too: it accepts
only the exact R1 MediaTek preloader identity and sends the same reviewed
eight-byte `FASTBOOT` command before native fastboot verification.

The current complete Linux package is generated at
`installer/dist/packages/jackrabbit-linux-x64-current-v0.1`. Run its
`install.sh`; users do not select an image directory or individual partition
file. Release builders produce the matching `macos-arm64`, `macos-x64`, and
`windows-x64` directories with `scripts/stage-host-package.sh` after compiling
the native CLI on the matching host runner.

Public user documentation:

- [`INSTALL.md`](INSTALL.md) — stock R1 through first boot, OS-specific launch,
  and the exact bundled image layout.
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — device-state recovery, host USB
  setup, stable CLI error codes, and what to include in an issue report.

## Ownership

| Path | Owns | Must not own |
|---|---|---|
| `contracts/` | Versioned release, operation, recovery, journal, and error contracts | Browser or native transport implementations |
| `conformance/` | Shared black-box cases every adapter must pass | Adapter-specific policy |
| `web/` | Hosted browser adapter and presentation | Canonical install/recovery policy |
| `cli/` | Primary guided engine and physical-world prompts | Host driver installation or release-image construction |
| `linux-macos/` | Shared Unix launcher and Linux-only R1 USB access rule | Flash policy or release images |
| `windows/` | Windows launcher and signed upstream driver installation | Flash policy or release images |
| `deployment/` | Installer-site deployment and security configuration | Product image construction |
| `provenance/` | Reviewed external protocol, dependency, and browser-API identities | Vendored third-party implementation |
| `scripts/` | Installer-local development and release automation | Product build automation |
| `tests/` | Installer boundary and integration tests | Product runtime tests |
| `dist/` | Ignored generated installer output | Source or authoritative release inputs |

The installer must build and test when this directory is copied out of the
monorepo. It may consume published, verified release artifacts through its
contracts; it may not import or read implementation files from sibling product,
image, artifact, reference, or internal planning trees.

## Checks

From the repository root:

```sh
cd installer
npm test
npm run build
npm run check:boundaries
npm run check:provenance
```

Generated dependencies, build output, and release packages remain outside the
source boundary enforced by the explicit copy allowlist.
