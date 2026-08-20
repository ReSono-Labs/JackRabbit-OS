"""Normalizes discovered MCP tools without granting them to an agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiscoveredMcpTool:
    connection_id: str
    name: str
    description: str
    input_schema: dict[str, object]
    annotations: dict[str, object]


def normalize_tools(connection_id: str, payload: object) -> tuple[DiscoveredMcpTool, ...]:
    if not isinstance(payload, list):
        raise ValueError("MCP tools/list result must contain a tool list.")
    result: list[DiscoveredMcpTool] = []
    names: set[str] = set()
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"]:
            raise ValueError("MCP tool name is invalid.")
        if item["name"] in names or not isinstance(item.get("description", ""), str) or not isinstance(item.get("inputSchema"), dict) or not isinstance(item.get("annotations", {}), dict):
            raise ValueError("MCP tool definition is invalid.")
        names.add(item["name"])
        result.append(DiscoveredMcpTool(connection_id, item["name"], item.get("description", "")[:2048], item["inputSchema"], item.get("annotations", {})))
    return tuple(result)
