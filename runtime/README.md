# On-device runtime

This directory owns trusted Python runtime behavior. Android process lifecycle and Keystore bridging live in `android/runtime-host`; Android presentation code communicates with the runtime through the local API.

Dependency direction:

```text
entrypoint -> application -> api + agents + providers + MCP + storage
api + agents + providers + MCP -> storage interfaces
storage -> Python standard library SQLite
```

Module ownership:

- `api/http_server.py` — transport only (bind, threads, bearer auth, request/response mechanics). Routes live in `api/routes.py` (`RuntimeRoutes`); new endpoints are added there.
- `providers/openai/access.py` — the single access-path → credential/base-URL decision every OpenAI consumer (agents, embeddings, future agents) must use.
- `agents/sdk_runner.py` — the single Agents SDK execution path every agent runner uses.

Run the host-side lifecycle tests:

```bash
PYTHONPATH=runtime python3.13 -m unittest discover -s tests/runtime
```

The runtime is intentionally small. Additional domains enter this package only when their real device-facing behavior and tests are implemented.
