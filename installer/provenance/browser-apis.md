# Browser API map

| Concern | Runtime evidence | Required user gesture | Current disposition |
|---|---|---|---|
| Secure origin | `window.isSecureContext === true` | No | Required before any device action |
| Web Serial availability | `"serial" in navigator` | No | Capability only; not host support |
| Preloader selection | `navigator.serial.requestPort()` with exact USB filter | Yes | Disabled until protocol and physical matrix pass |
| WebUSB availability | `"usb" in navigator` | No | Capability only; not host support |
| Fastboot selection | `navigator.usb.requestDevice()` with exact reviewed filter | Yes | Read-only adapter remains gated |
| Prior USB authorization | `navigator.usb.getDevices()` | No | Cannot substitute for live identity/preflight |
| USB re-enumeration | WebUSB connect/disconnect events plus live re-probe | Sometimes; tuple-dependent | Must be physically proved per tuple |

The capability gate must deny a missing API before requesting a device. It must
not infer operating-system version, driver correctness, USB permissions,
fastboot mode, device identity, or installation support merely from API
presence or user-agent text.

## Reviewed Rabbit entry sequence

The 2026-08-22 live Rabbit reference used:

1. Web Serial filter USB VID `0x0e8d`, PID `0x2000`.
2. Port open at 115200 baud.
3. One UTF-8/ASCII `FASTBOOT` write (seven bytes).
4. Writer release and deterministic port close.
5. A separate physical-screen check and WebUSB selection using VID `0x0e8d`,
   PID `0x201c`.

This is evidence for an independent implementation candidate, not permission
to copy Rabbit's wrapper or a claim that the sequence works on any unproved
host.
