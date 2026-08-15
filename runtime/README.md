# On-device runtime

This directory owns trusted Python runtime behavior. Android process lifecycle and Keystore bridging live in `android/runtime-host`; Android presentation code communicates with the runtime through the local API.

Dependency direction:

```text
entrypoint -> application -> api + agents + providers + MCP + storage
api + agents + providers + MCP -> storage interfaces
storage -> Python standard library SQLite
```

Run the host-side lifecycle tests:

```bash
PYTHONPATH=runtime python3.13 -m unittest discover -s tests/runtime
```

The runtime is intentionally small. Additional domains enter this package only when their real device-facing behavior and tests are implemented.
