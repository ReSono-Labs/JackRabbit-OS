# CLI USB transport review

The read-only CLI adapter uses `fastboot-protocol` 0.4.0 at source revision
`c84eee005cfadef7baa80a6cdbebb966de5f03e0`, with `nusb` 0.2.7 at revision
`bdc148c123c102785cd1d506b77bfeeb794ffeb1`. Cargo registry archive hashes,
licenses, and the executor dependency are pinned in `sources.json` and
`Cargo.lock`.

Retained behavior in the built-in read-only diagnostic is limited by
JackRabbit-owned code to:

- enumerate USB devices exposing a fastboot-class interface;
- accept only USB vendor `0x0e8d` and product `0x201c`;
- require exactly one matching R1;
- open its bulk fastboot interface; and
- query the six fixed variables owned by `cli/src/diagnose.rs`.

The guided `install RELEASE_DIRECTORY` path does not expose those dependency
APIs or a raw command surface. It uses a separately packaged native fastboot
binary through a JackRabbit-owned structured adapter. The adapter accepts only
the fixed stock-to-current-JackRabbit commands, exact hash-verified release
paths, and the one machine-selected R1 serial. Users cannot provide a command,
partition, image path, URL, or fastboot variable.

The install adapter owns the physically accepted bootloader/fastbootd sequence,
including `0e8d:201c` to `18d1:4ee0` mode changes, Linux udev denial guidance,
the blank-screen warning during the `super` write, unlock convergence, final
userdata erase, slot-A selection, and reboot. Public host packages must pin and
verify their bundled platform-specific fastboot binary and publish its license
and SBOM entry.

The crates are consumed as dependencies; no source was copied. The dual
MIT/Apache-2.0 dependency terms are compatible with the open-source installer,
subject to publishing the final generated notices/SBOM before a public binary.

An attempted local read-only run on 2026-08-22 returned
`JR-CLI-DEVICE-MISSING`; no R1 was visible to the process at that moment. That
is a tested fail-closed result, not physical USB acceptance. Windows, macOS,
Linux permission/driver behavior and live R1 reads remain separately gated.
