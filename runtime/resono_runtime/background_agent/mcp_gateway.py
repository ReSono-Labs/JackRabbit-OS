"""Per-run MCP servers backed by immutable BackgroundToolSupply projections."""

from __future__ import annotations

import threading

from ..agents.audience import AgentKind
from ..mcp.server import LocalMcpServer, McpHttpResult
from ..tools.catalog import ToolCatalog
from ..storage.agent_runs import AgentRunRepository
from .run_contract import AgentRunRequest
from .tool_supply import BackgroundToolGrant, BackgroundToolSupply


class BackgroundMcpGateway:
    def __init__(self, *, health, catalog: ToolCatalog, allowed_names,
                 runs: AgentRunRepository) -> None:
        self._health = health
        self._catalog = catalog
        self._allowed_names = allowed_names
        self._runs = runs
        self._servers: dict[str, LocalMcpServer] = {}
        self._lock = threading.Lock()

    def open(self, request: AgentRunRequest) -> str:
        supply = BackgroundToolSupply(
            self._catalog,
            BackgroundToolGrant(request.autonomy, frozenset(self._allowed_names()),
                                request.limits.max_tool_calls),
            activity=lambda event, detail: self._runs.record_event(request.run_id, event, detail),
        )
        server = LocalMcpServer(self._health, catalog=supply, agent=AgentKind.TEXT)
        with self._lock:
            if request.run_id in self._servers:
                raise RuntimeError("run MCP server already exists")
            self._servers[request.run_id] = server
        return request.run_id

    def close(self, run_id: str) -> None:
        with self._lock:
            self._servers.pop(run_id, None)

    def handle(self, run_id: str, message: dict[str, object], **context) -> McpHttpResult:
        with self._lock:
            server = self._servers.get(run_id)
        if server is None:
            return McpHttpResult(404, {"error": {"code": "run_not_found", "message": "Run tool session is unavailable."}})
        return server.handle(message, execution_id=run_id, **context)
