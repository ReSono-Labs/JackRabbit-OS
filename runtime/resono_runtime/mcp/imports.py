"""Official mcp.json import with exact-state overwrite confirmation."""
from __future__ import annotations

import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from ..agents import AgentAudience
from ..imports import ImportPreflightError, ImportPreflightRegistry
from ..plugins.specification import StandardMcpDocument, parse_mcp_bytes
from .lifecycle import McpLifecycle


class McpDocumentImport:
    def __init__(self, lifecycle: McpLifecycle) -> None:
        self._lifecycle = lifecycle
        self._preflights: ImportPreflightRegistry[StandardMcpDocument] = ImportPreflightRegistry()

    def preflight(self, payload: bytes, *, audience: AgentAudience):
        document = parse_mcp_bytes(payload)
        if document.invalid_servers or not document.servers:
            raise ValueError("mcp.json must contain at least one valid MCP server and no invalid servers.")
        identity = ",".join(sorted(server.name for server in document.servers))
        candidate_hash = _document_hash(document)
        return self._preflights.issue(identity=identity, candidate_hash=candidate_hash, current_hash=self._current_hash(document), audience=audience, payload=document)

    def confirm(self, token: str, *, replace: bool, changed_by: str, reason: str):
        try:
            preview = self._preflights.peek(token)
            record = self._preflights.consume(token, current_hash=self._current_hash(preview.payload), replace=replace)
        except ImportPreflightError as error:
            raise ValueError(str(error)) from error
        return tuple(
            self._lifecycle.install(
                connection_id=_connection_id(server.name),
                display_name=server.name,
                configuration=server.configuration,
                audience=record.audience,
                changed_by=changed_by,
                reason=reason,
            )
            for server in record.payload.servers
        )

    def _current_hash(self, document: StandardMcpDocument) -> str | None:
        values = []
        any_installed = False
        for server in document.servers:
            current = self._lifecycle.get(_connection_id(server.name))
            any_installed = any_installed or current is not None
            values.append((server.name, current.configuration_hash if current is not None else None))
        if not any_installed:
            return None
        return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _connection_id(server_name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"resono:mcp:{server_name}"))


def _document_hash(document: StandardMcpDocument) -> str:
    values = [
        (
            server.name,
            hashlib.sha256(json.dumps(server.configuration, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        )
        for server in document.servers
    ]
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
