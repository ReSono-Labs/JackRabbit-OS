# JackRabbit Installer

This is the independent installer project for ReSono Labs R1 Voice. It will
provide a hosted web installer and a guided command-line fallback from the same
versioned contracts and conformance cases.

This foundation contains no installer UI, device transport, flashing command,
or simulated device behavior. Those capabilities remain gated by the accepted
installer plan and later build contracts.

## Ownership

| Path | Owns | Must not own |
|---|---|---|
| `contracts/` | Versioned release, operation, recovery, journal, and error contracts | Browser or native transport implementations |
| `conformance/` | Shared black-box cases every adapter must pass | Adapter-specific policy |
| `web/` | Hosted browser adapter and presentation | Canonical install/recovery policy |
| `cli/` | Guided fallback adapter and physical-world prompts | Canonical install/recovery policy |
| `deployment/` | Installer-site deployment and security configuration | Product image construction |
| `provenance/` | Reviewed external protocol, dependency, and browser-API identities | Vendored third-party implementation |
| `scripts/` | Installer-local development and release automation | Product build automation |
| `tests/` | Installer boundary and integration tests | Product runtime tests |
| `dist/` | Ignored generated installer output | Source or authoritative release inputs |

The installer must build and test when this directory is copied out of the
monorepo. It may consume published, verified release artifacts through its
contracts; it may not import or read implementation files from sibling product,
image, artifact, reference, or internal planning trees.

## Foundation check

From the repository root:

```sh
bash installer/tests/test-boundaries.sh
```

The checker is intentionally language-neutral. A later accepted toolchain may
add language-aware checks without weakening this boundary.
