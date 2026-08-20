"""Outbound MCP connection lifecycle and live tool-catalog projection."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import json
import re
from uuid import UUID

from ..agents import AgentAudience, AgentAudienceRouter
from ..agents.audience import AudienceResource, AudienceResourceKind
from ..connections.records import ConnectionRepository
from ..security.credentials import ConnectionCredentialEnvelopes
from ..storage.connection_credentials import ConnectionCredentialRepository
from ..storage.mcp_connections import McpConnectionRepository, StoredMcpConnection, StoredMcpTool
from ..tools import ToolCatalog, ToolDefinition, ToolInvocationResult
from .client import McpConnectionError, StreamableHttpMcpClient
from .connections import McpConnectionConfiguration, validate_connection_configuration
from .tool_adapter import normalize_tools


class McpLifecycle:
    """Owns configured outbound MCP servers; it does not own credentials or plugins."""

    def __init__(
        self,
        repository: McpConnectionRepository,
        connections: ConnectionRepository,
        audiences: AgentAudienceRouter,
        tools: ToolCatalog,
        credential_repository: ConnectionCredentialRepository,
        credential_envelopes: ConnectionCredentialEnvelopes,
    ) -> None:
        self._repository = repository
        self._connections = connections
        self._audiences = audiences
        self._tools = tools
        self._credential_repository = credential_repository
        self._credential_envelopes = credential_envelopes

    def restore(self) -> None:
        for connection in self._repository.list():
            self._project(connection)

    def list(self) -> tuple[StoredMcpConnection, ...]:
        return self._repository.list()

    def get(self, connection_id: str) -> StoredMcpConnection | None:
        return self._repository.get(connection_id)

    def tools(self, connection_id: str) -> tuple[StoredMcpTool, ...]:
        return self._repository.tools(connection_id)

    def set_credentials(self, connection_id: str, headers: dict[str, str]) -> None:
        self._required(connection_id)
        plaintext = json.dumps(_credential_headers(headers), sort_keys=True, separators=(",", ":"))
        self._credential_repository.put_envelope(
            connection_id,
            self._credential_envelopes.seal(connection_id, plaintext),
        )

    def install(
        self,
        *,
        connection_id: str,
        display_name: str,
        configuration: dict[str, object],
        audience: AgentAudience,
        changed_by: str,
        reason: str,
        source_owner: str | None = None,
        credential_headers: dict[str, str] | None = None,
    ) -> StoredMcpConnection:
        UUID(connection_id)
        if not display_name.strip() or len(display_name) > 100:
            raise ValueError("MCP display name is invalid.")
        parsed = validate_connection_configuration(configuration)
        sealed_credential = None
        if credential_headers is not None:
            sealed_credential = self._credential_envelopes.seal(
                connection_id,
                json.dumps(_credential_headers(credential_headers), sort_keys=True, separators=(",", ":")),
            )
        digest = hashlib.sha256(_canonical(configuration)).hexdigest()
        supported = parsed.transport == "streamable-http"
        record = StoredMcpConnection(
            connection_id=connection_id,
            display_name=display_name.strip(),
            transport=parsed.transport,
            endpoint=parsed.endpoint,
            command=(parsed.command, *parsed.args) if parsed.command else None,
            configuration_hash=digest,
            lifecycle_state="disabled" if supported else "failed",
            configuration=configuration,
            health_detail=None if supported else "Transport is not supported by this build.",
        )
        saved = self._repository.save(record, action="install", changed_by=changed_by, reason=reason)
        if sealed_credential is not None:
            self._credential_repository.put_envelope(connection_id, sealed_credential)
        self._connections.save(
            connection_id=connection_id,
            kind="mcp",
            label=saved.display_name,
            enabled=False,
            health_state="disabled" if supported else "failed",
            health_detail=saved.health_detail,
            source_owner=source_owner,
        )
        self._audiences.set_audience(self._resource(connection_id), audience, changed_by=changed_by, reason=reason)
        self._project(saved)
        return saved

    def discover(self, connection_id: str, *, changed_by: str, reason: str) -> StoredMcpConnection:
        record = self._required(connection_id)
        configuration = validate_connection_configuration(record.configuration)
        if configuration.transport != "streamable-http":
            raise ValueError("Only Streamable HTTP MCP discovery is supported.")
        client = self._client(connection_id, configuration)
        try:
            initialized = client.initialize()
            discovered = normalize_tools(connection_id, client.discover_tools())
        except McpConnectionError as error:
            failed = self._state(record, "failed", str(error))
            self._repository.save(failed, action="discover_failed", changed_by=changed_by, reason=reason)
            self._save_connection_projection(record, enabled=False, health_state="failed", health_detail=str(error))
            self._project(failed)
            raise
        finally:
            client.close()
        stored = tuple(
            StoredMcpTool(
                connection_id=connection_id,
                tool_name=tool.name,
                exposed_name=_exposed_name(connection_id, tool.name),
                description=tool.description,
                input_schema=tool.input_schema,
                annotations=tool.annotations,
            )
            for tool in discovered
        )
        self._repository.replace_tools(connection_id, stored)
        server_info = initialized.get("serverInfo", {})
        updated = replace(
            record,
            lifecycle_state="configured",
            protocol_version=str(initialized.get("protocolVersion")),
            server_name=str(server_info.get("name")) if isinstance(server_info, dict) and server_info.get("name") else None,
            server_version=str(server_info.get("version")) if isinstance(server_info, dict) and server_info.get("version") else None,
            last_discovered_at=datetime.now(UTC).isoformat(),
            health_detail=None,
        )
        saved = self._repository.save(updated, action="discover", changed_by=changed_by, reason=reason)
        self._save_connection_projection(record, enabled=False, health_state="ready")
        self._project(saved)
        return saved

    def grant_tool(self, connection_id: str, tool_name: str, *, enabled: bool, effect_class: str | None) -> StoredMcpTool:
        granted = self._repository.grant_tool(connection_id, tool_name, enabled=enabled, effect_class=effect_class)
        self._project(self._required(connection_id))
        return granted

    def set_enabled(self, connection_id: str, enabled: bool, *, changed_by: str, reason: str) -> StoredMcpConnection:
        record = self._required(connection_id)
        if enabled and record.transport != "streamable-http":
            raise ValueError("This MCP transport is not supported by this build.")
        state = "connected" if enabled else "disabled"
        saved = self._repository.save(self._state(record, state, None), action=state, changed_by=changed_by, reason=reason)
        self._save_connection_projection(
            record,
            enabled=enabled,
            health_state="ready" if enabled else "disabled",
        )
        self._project(saved)
        return saved

    def remove(self, connection_id: str, *, changed_by: str, reason: str) -> bool:
        removed = self._repository.remove(connection_id, changed_by=changed_by, reason=reason)
        if removed:
            self._tools.remove_source(self._source(connection_id))
            self._audiences.remove_resource(self._resource(connection_id), changed_by=changed_by, reason=reason)
            self._connections.remove(connection_id)
            self._credential_repository.delete(connection_id)
        return removed

    def _save_connection_projection(
        self,
        record: StoredMcpConnection,
        *,
        enabled: bool,
        health_state: str,
        health_detail: str | None = None,
    ) -> None:
        existing = self._connections.get(record.connection_id)
        self._connections.save(
            connection_id=record.connection_id,
            kind="mcp",
            label=record.display_name,
            enabled=enabled,
            health_state=health_state,
            health_detail=health_detail,
            source_owner=existing.source_owner if existing is not None else None,
        )

    def _project(self, connection: StoredMcpConnection) -> None:
        definitions: list[ToolDefinition] = []
        if connection.lifecycle_state == "connected":
            for tool in self._repository.tools(connection.connection_id):
                if tool.enabled:
                    definitions.append(self._definition(connection, tool))
        self._tools.replace_source(self._source(connection.connection_id), tuple(definitions))

    def _definition(self, connection: StoredMcpConnection, tool: StoredMcpTool) -> ToolDefinition:
        def invoke(arguments: dict[str, object]) -> ToolInvocationResult:
            client = self._client(connection.connection_id, validate_connection_configuration(connection.configuration))
            try:
                result = client.call_tool(tool.tool_name, arguments)
                return _tool_result(result)
            except McpConnectionError as error:
                return ToolInvocationResult(str(error), is_error=True)
            finally:
                client.close()
        return ToolDefinition(
            tool_id=f"mcp:{connection.connection_id}:{tool.tool_name}",
            name=tool.exposed_name,
            description=tool.description,
            input_schema=tool.input_schema,
            handler=invoke,
            effect_class=tool.effect_class or "read",
            audience_resource=self._resource(connection.connection_id),
        )

    def _client(self, connection_id: str, configuration: McpConnectionConfiguration) -> StreamableHttpMcpClient:
        envelope = self._credential_repository.get_envelope(connection_id)
        headers: dict[str, str] | None = None
        if envelope is not None:
            plaintext = self._credential_envelopes.open(connection_id, envelope)
            value = json.loads(plaintext)
            headers = _credential_headers(value)
        return StreamableHttpMcpClient(configuration, credential_headers=headers)

    def _required(self, connection_id: str) -> StoredMcpConnection:
        record = self._repository.get(connection_id)
        if record is None:
            raise ValueError("MCP connection was not found.")
        return record

    @staticmethod
    def _state(record: StoredMcpConnection, state: str, detail: str | None) -> StoredMcpConnection:
        return StoredMcpConnection(
            connection_id=record.connection_id, display_name=record.display_name,
            transport=record.transport, endpoint=record.endpoint, command=record.command,
            configuration_hash=record.configuration_hash, lifecycle_state=state,
            configuration=record.configuration, protocol_version=record.protocol_version,
            server_name=record.server_name, server_version=record.server_version,
            last_discovered_at=record.last_discovered_at, health_detail=detail,
        )

    @staticmethod
    def _resource(connection_id: str) -> AudienceResource:
        return AudienceResource(AudienceResourceKind.MCP_CONNECTION, connection_id)

    @staticmethod
    def _source(connection_id: str) -> str:
        return f"mcp:{connection_id}"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _exposed_name(connection_id: str, tool_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", tool_name.casefold()).strip("_") or "tool"
    return f"mcp__{connection_id.replace('-', '')[:12]}__{slug}"[:64]


def _tool_result(value: object) -> ToolInvocationResult:
    if not isinstance(value, dict):
        return ToolInvocationResult("MCP server returned an invalid tool result.", is_error=True)
    content = value.get("content", [])
    text = "\n".join(str(item.get("text")) for item in content if isinstance(item, dict) and item.get("type") == "text")
    structured = value.get("structuredContent")
    return ToolInvocationResult(text or "MCP tool completed.", structured if isinstance(structured, dict) else None, bool(value.get("isError")))


def _credential_headers(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not value or len(value) > 8:
        raise ValueError("MCP credentials must be a non-empty header object.")
    result: dict[str, str] = {}
    forbidden = {"connection", "content-length", "host", "mcp-protocol-version", "mcp-session-id", "transfer-encoding"}
    for name, item in value.items():
        if not isinstance(name, str) or not isinstance(item, str) or not name.strip() or not item or "\n" in name + item or "\r" in name + item:
            raise ValueError("MCP credential header is invalid.")
        if name.casefold() in forbidden:
            raise ValueError("MCP credential header is reserved.")
        result[name] = item
    return result
