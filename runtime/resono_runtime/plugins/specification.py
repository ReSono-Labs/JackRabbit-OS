"""Exact Agent Plugins 1.0.0 manifest and MCP component validation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from jsonschema import Draft202012Validator


PLUGIN_SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
_SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "standards" / "agent_plugins"


class PluginSpecificationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StandardPluginManifest:
    name: str
    version: str | None
    description: str | None


@dataclass(frozen=True, slots=True)
class StandardMcpServer:
    name: str
    configuration: dict[str, object]


@dataclass(frozen=True, slots=True)
class StandardMcpDocument:
    servers: tuple[StandardMcpServer, ...]
    invalid_servers: tuple[tuple[str, str], ...]


def parse_plugin_manifest(source: Path) -> StandardPluginManifest:
    value = _read_object(source, "plugin.json")
    _validate(value, _schema("plugin.schema.json"), "plugin.json")
    return StandardPluginManifest(
        name=value["name"],
        version=value.get("version"),
        description=value.get("description"),
    )


def parse_mcp_document(source: Path) -> StandardMcpDocument:
    value = _read_object(source, "mcp.json")
    return parse_mcp_value(value)


def parse_mcp_bytes(payload: bytes) -> StandardMcpDocument:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PluginSpecificationError("mcp.json must be valid UTF-8 JSON.") from error
    if not isinstance(value, dict):
        raise PluginSpecificationError("mcp.json must be a JSON object.")
    return parse_mcp_value(value)


def parse_mcp_value(value: dict[str, object]) -> StandardMcpDocument:
    schema = _schema("mcp.schema.json")
    if value.get("$schema") != MCP_SCHEMA_ID or set(value) - {"$schema", "mcpServers"}:
        raise PluginSpecificationError("mcp.json does not match the Agent Plugins 1.0.0 root contract.")
    servers = value.get("mcpServers")
    if not isinstance(servers, dict):
        raise PluginSpecificationError("mcp.json mcpServers must be an object.")
    server_validator = Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": "#/$defs/server",
            "$defs": schema["$defs"],
        }
    )
    valid: list[StandardMcpServer] = []
    invalid: list[tuple[str, str]] = []
    for name, configuration in servers.items():
        if not isinstance(name, str) or not name:
            invalid.append((str(name), "server name must be a non-empty string"))
            continue
        errors = sorted(server_validator.iter_errors(configuration), key=lambda item: list(item.path))
        if errors:
            invalid.append((name, errors[0].message))
            continue
        valid.append(StandardMcpServer(name, configuration))
    return StandardMcpDocument(tuple(valid), tuple(invalid))


def _read_object(source: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PluginSpecificationError(f"{label} must be valid UTF-8 JSON.") from error
    if not isinstance(value, dict):
        raise PluginSpecificationError(f"{label} must be a JSON object.")
    return value


def _schema(filename: str) -> dict[str, object]:
    try:
        value = json.loads((_SCHEMA_ROOT / filename).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Pinned Agent Plugins schema is unavailable: {filename}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"Pinned Agent Plugins schema is invalid: {filename}")
    return value


def _validate(value: object, schema: dict[str, object], label: str) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.path))
    if errors:
        raise PluginSpecificationError(f"{label} is invalid: {errors[0].message}")
