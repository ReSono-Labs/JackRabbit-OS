# Contracts

Canonical, versioned installer data contracts belong here. Web and CLI code
will consume these definitions and must not create adapter-local alternatives.

Contracts use JSON Schema draft 2020-12. Detached Ed25519 signatures cover the
exact release-manifest bytes; consumers verify the signature and SHA-256 before
parsing or trusting manifest metadata.

Build Contract 03 defines only offline validation and planning. These schemas
do not make a release, device, host, profile, or operation supported.

`preparation-prompts-v1.json` is the one web/CLI physical-guidance source. Its
schema fixes stable IDs, reasons, actions, observable outcomes, warnings,
verification ownership, cancellation behavior, reviewed links, and next states.

`current-release-v0.2.json` is the neutral CLI/package image inventory. Host
packaging and release verification consume it directly; no web-installer module
owns the distributable image set.
