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
- `mcp/client.py` — outbound MCP clients for `streamable-http`, `sse`, and `stdio` transports plus the transport-agnostic `client_for` factory.
- `mcp/lifecycle.py` — `McpLifecycle` owns MCP install, discover, enable, remove, tool projection, and per-audience connection routing.
- `providers/compatible.py` — OpenAI-compatible third-party provider backend (key validation via `GET /models`, live model listing).
- `providers/access.py` — the provider-neutral key/base-URL/API-style resolver every text-agent consumer uses; OpenAI's platform/subscription paths are unchanged.

Run the host-side runtime tests:

```bash
.venv/bin/python -m pytest tests -q
```

The runtime is intentionally small. Additional domains enter this package only when their real device-facing behavior and tests are implemented.
