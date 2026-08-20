"""Authenticated management routes for outbound MCP connections."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from ..agents import AgentAudience
from ..mcp.client import McpConnectionError
from ..mcp.lifecycle import McpLifecycle
from ..mcp.imports import McpDocumentImport
from ..security.pairing import PairingAuthority

if TYPE_CHECKING:
    from .routes import RouteRequest


class McpRoutes:
    def __init__(self, lifecycle: McpLifecycle) -> None:
        self._lifecycle = lifecycle
        self._imports = McpDocumentImport(lifecycle)

    def handle_get(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if path != "/v1/management/mcp/connections" and not path.startswith("/v1/management/mcp/connections/"):
            return False
        if not _session(request, pairing, mutation=False):
            return True
        if path == "/v1/management/mcp/connections":
            request.respond_json(200, {"connections": [_view(item, self._lifecycle) for item in self._lifecycle.list()]})
            return True
        connection_id = path.split("/")[5]
        item = self._lifecycle.get(connection_id)
        if item is None:
            _error(request, 404, "mcp_connection_not_found", "MCP connection not found.")
        else:
            request.respond_json(200, _view(item, self._lifecycle))
        return True

    def handle_post(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if not path.startswith("/v1/management/mcp/"):
            return False
        if not _session(request, pairing, mutation=True):
            return True
        try:
            if path == "/v1/management/mcp/imports/preflight":
                payload_bytes = request.request_bytes(max_bytes=1024 * 1024)
                if payload_bytes is None: return True
                result = self._imports.preflight(payload_bytes, audience=AgentAudience(request.headers.get("X-ReSono-Agent-Audience", "")))
                request.respond_json(200, {"state": result.state, "preflightToken": result.token, "servers": [server.name for server in result.payload.servers], "contentHash": result.candidate_hash})
                return True
            payload = request.request_json(max_bytes=32_768)
            if payload is None: return True
            if path == "/v1/management/mcp/imports/confirm":
                items = self._imports.confirm(str(payload.get("preflightToken", "")), replace=payload.get("replace") is True, changed_by="management-api", reason="confirmed mcp.json import")
                request.respond_json(201, {"connections": [_view(item, self._lifecycle) for item in items]})
                return True
            if path == "/v1/management/mcp/connections":
                raise ValueError("Import an industry-standard mcp.json document before configuring credentials.")
            parts = path.split("/")
            if len(parts) != 7:
                raise ValueError("MCP action path is invalid.")
            connection_id, action = parts[5], parts[6]
            if action == "discover":
                item = self._lifecycle.discover(connection_id, changed_by="management-api", reason="discovered MCP tools")
            elif action == "enable":
                item = self._lifecycle.set_enabled(connection_id, True, changed_by="management-api", reason="enabled MCP connection")
            elif action == "disable":
                item = self._lifecycle.set_enabled(connection_id, False, changed_by="management-api", reason="disabled MCP connection")
            elif action == "grant":
                self._lifecycle.grant_tool(
                    connection_id,
                    _required_string(payload, "toolName"),
                    enabled=payload.get("enabled") is True,
                    effect_class=payload.get("effect") if isinstance(payload.get("effect"), str) else None,
                )
                item = self._lifecycle.get(connection_id)
            elif action == "credentials":
                headers = payload.get("credentialHeaders")
                if not isinstance(headers, dict):
                    raise ValueError("credentialHeaders must be an object.")
                self._lifecycle.set_credentials(connection_id, headers)
                item = self._lifecycle.get(connection_id)
            else:
                raise ValueError("MCP action is unsupported.")
            request.respond_json(200, _view(item, self._lifecycle))
        except McpConnectionError as error:
            _error(request, 502, "mcp_connection_failed", str(error))
        except (ValueError, TypeError) as error:
            _error(request, 409, "mcp_connection_conflict", str(error))
        return True

    def handle_delete(self, request: "RouteRequest", pairing: PairingAuthority | None) -> bool:
        path = request.path.split("?", 1)[0]
        if not path.startswith("/v1/management/mcp/connections/"):
            return False
        if not _session(request, pairing, mutation=True):
            return True
        connection_id = path.rsplit("/", 1)[-1]
        if self._lifecycle.remove(connection_id, changed_by="management-api", reason="removed MCP connection"):
            request.respond_json(200, {"connectionId": connection_id, "deleted": True})
        else:
            _error(request, 404, "mcp_connection_not_found", "MCP connection not found.")
        return True


def _view(item: object, lifecycle: McpLifecycle) -> dict[str, object]:
    return {
        "connectionId": item.connection_id,
        "displayName": item.display_name,
        "transport": item.transport,
        "endpoint": item.endpoint,
        "state": item.lifecycle_state,
        "healthDetail": item.health_detail,
        "protocolVersion": item.protocol_version,
        "serverName": item.server_name,
        "serverVersion": item.server_version,
        "lastDiscoveredAt": item.last_discovered_at,
        "tools": [
            {"name": tool.tool_name, "exposedName": tool.exposed_name, "description": tool.description, "enabled": tool.enabled, "effect": tool.effect_class}
            for tool in lifecycle.tools(item.connection_id)
        ],
    }


def _required_string(payload: dict[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required.")
    return value.strip()


def _session(request: "RouteRequest", pairing: PairingAuthority | None, *, mutation: bool) -> bool:
    if pairing is None:
        _error(request, 503, "management_unavailable", "Management pairing is unavailable.")
        return False
    return request.browser_session(pairing, mutation=mutation) is not None


def _error(request: "RouteRequest", status: int, code: str, message: str) -> None:
    request.respond_json(status, {"error": {"code": code, "message": message}})
