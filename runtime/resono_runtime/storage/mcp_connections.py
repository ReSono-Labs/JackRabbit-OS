from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json

from .database import RuntimeDatabase


@dataclass(frozen=True, slots=True)
class StoredMcpConnection:
    connection_id: str
    display_name: str
    transport: str
    endpoint: str | None
    command: tuple[str, ...] | None
    configuration_hash: str
    lifecycle_state: str
    configuration: dict[str, object]
    protocol_version: str | None = None
    server_name: str | None = None
    server_version: str | None = None
    last_discovered_at: str | None = None
    health_detail: str | None = None


@dataclass(frozen=True, slots=True)
class StoredMcpTool:
    connection_id: str
    tool_name: str
    exposed_name: str
    description: str
    input_schema: dict[str, object]
    annotations: dict[str, object]
    enabled: bool = False
    effect_class: str | None = None


class McpConnectionRepository:
    def __init__(self, database: RuntimeDatabase) -> None:
        self._database = database

    def get(self, connection_id: str) -> StoredMcpConnection | None:
        with self._database.connect() as connection:
            row = connection.execute(
                """SELECT connection_id, display_name, transport, endpoint, command_json,
                          configuration_hash, lifecycle_state, configuration_json,
                          protocol_version, server_name, server_version, last_discovered_at,
                          health_detail
                   FROM mcp_connections WHERE connection_id = ?""",
                (connection_id,),
            ).fetchone()
        return _connection(row)

    def list(self) -> tuple[StoredMcpConnection, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """SELECT connection_id, display_name, transport, endpoint, command_json,
                          configuration_hash, lifecycle_state, configuration_json,
                          protocol_version, server_name, server_version, last_discovered_at,
                          health_detail
                   FROM mcp_connections ORDER BY display_name, connection_id"""
            ).fetchall()
        return tuple(item for row in rows if (item := _connection(row)) is not None)

    def save(self, item: StoredMcpConnection, *, action: str, changed_by: str, reason: str) -> StoredMcpConnection:
        previous = self.get(item.connection_id)
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO mcp_connections(
                       connection_id, display_name, transport, endpoint, command_json,
                       configuration_hash, lifecycle_state, created_at, updated_at,
                       configuration_json, protocol_version, server_name, server_version,
                       last_discovered_at, health_detail
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(connection_id) DO UPDATE SET
                       display_name = excluded.display_name,
                       transport = excluded.transport,
                       endpoint = excluded.endpoint,
                       command_json = excluded.command_json,
                       configuration_hash = excluded.configuration_hash,
                       lifecycle_state = excluded.lifecycle_state,
                       updated_at = excluded.updated_at,
                       configuration_json = excluded.configuration_json,
                       protocol_version = excluded.protocol_version,
                       server_name = excluded.server_name,
                       server_version = excluded.server_version,
                       last_discovered_at = excluded.last_discovered_at,
                       health_detail = excluded.health_detail""",
                (
                    item.connection_id, item.display_name, item.transport, item.endpoint,
                    json.dumps(item.command) if item.command else None,
                    item.configuration_hash, item.lifecycle_state, now, now,
                    json.dumps(item.configuration, sort_keys=True), item.protocol_version,
                    item.server_name, item.server_version, item.last_discovered_at,
                    item.health_detail,
                ),
            )
            connection.execute(
                """INSERT INTO mcp_connection_audit(
                       connection_id, action, previous_hash, current_hash,
                       changed_at, changed_by, change_reason
                   ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    item.connection_id, action,
                    previous.configuration_hash if previous else None,
                    item.configuration_hash, now, changed_by, reason,
                ),
            )
            connection.commit()
        return item

    def replace_tools(self, connection_id: str, tools: tuple[StoredMcpTool, ...]) -> None:
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = {
                row["tool_name"]: (bool(row["enabled"]), row["effect_class"])
                for row in connection.execute(
                    "SELECT tool_name, enabled, effect_class FROM mcp_discovered_tools WHERE connection_id = ?",
                    (connection_id,),
                )
            }
            connection.execute("DELETE FROM mcp_discovered_tools WHERE connection_id = ?", (connection_id,))
            connection.executemany(
                """INSERT INTO mcp_discovered_tools(
                       connection_id, tool_name, exposed_name, description, input_schema_json,
                       discovered_at, annotations_json, enabled, effect_class
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        tool.connection_id, tool.tool_name, tool.exposed_name, tool.description,
                        json.dumps(tool.input_schema, sort_keys=True), now,
                        json.dumps(tool.annotations, sort_keys=True),
                        int(previous.get(tool.tool_name, (False, None))[0]),
                        previous.get(tool.tool_name, (False, None))[1],
                    )
                    for tool in tools
                ],
            )
            connection.commit()

    def tools(self, connection_id: str) -> tuple[StoredMcpTool, ...]:
        with self._database.connect() as connection:
            rows = connection.execute(
                """SELECT connection_id, tool_name, exposed_name, description,
                          input_schema_json, annotations_json, enabled, effect_class
                   FROM mcp_discovered_tools WHERE connection_id = ? ORDER BY tool_name""",
                (connection_id,),
            ).fetchall()
        return tuple(
            StoredMcpTool(
                row[0], row[1], row[2], row[3], json.loads(row[4]),
                json.loads(row[5]), bool(row[6]), row[7],
            )
            for row in rows
        )

    def grant_tool(self, connection_id: str, tool_name: str, *, enabled: bool, effect_class: str | None) -> StoredMcpTool:
        if enabled and effect_class not in {"read", "local_write", "external_write", "destructive"}:
            raise ValueError("An enabled MCP tool requires an explicit effect classification.")
        with self._database.connect() as connection:
            cursor = connection.execute(
                "UPDATE mcp_discovered_tools SET enabled = ?, effect_class = ? WHERE connection_id = ? AND tool_name = ?",
                (int(enabled), effect_class, connection_id, tool_name),
            )
            connection.commit()
        if cursor.rowcount != 1:
            raise ValueError("Discovered MCP tool was not found.")
        return next(tool for tool in self.tools(connection_id) if tool.tool_name == tool_name)

    def remove(self, connection_id: str, *, changed_by: str, reason: str) -> bool:
        previous = self.get(connection_id)
        if previous is None:
            return False
        now = datetime.now(UTC).isoformat()
        with self._database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM mcp_connections WHERE connection_id = ?", (connection_id,))
            connection.execute(
                """INSERT INTO mcp_connection_audit(
                       connection_id, action, previous_hash, current_hash,
                       changed_at, changed_by, change_reason
                   ) VALUES (?, 'remove', ?, NULL, ?, ?, ?)""",
                (connection_id, previous.configuration_hash, now, changed_by, reason),
            )
            connection.commit()
        return True


def _connection(row: object) -> StoredMcpConnection | None:
    if row is None:
        return None
    return StoredMcpConnection(
        connection_id=row[0], display_name=row[1], transport=row[2], endpoint=row[3],
        command=tuple(json.loads(row[4])) if row[4] else None,
        configuration_hash=row[5], lifecycle_state=row[6],
        configuration=json.loads(row[7]), protocol_version=row[8],
        server_name=row[9], server_version=row[10], last_discovered_at=row[11],
        health_detail=row[12],
    )

