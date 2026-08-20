"""Standards-based MCP connection configuration validation without connection I/O."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


class McpConnectionConfigurationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class McpConnectionConfiguration:
    transport: str
    endpoint: str | None = None
    command: str | None = None
    args: tuple[str, ...] = ()
    headers: tuple[tuple[str, str], ...] = ()
    env: tuple[tuple[str, str], ...] = ()
    cwd: str | None = None


def validate_connection_configuration(value: object) -> McpConnectionConfiguration:
    if not isinstance(value, dict):
        raise McpConnectionConfigurationError("MCP connection configuration must be an object.")
    transport = value.get("type")
    if transport in {"streamable-http", "sse"}:
        if set(value) - {"type", "url", "headers"}:
            raise McpConnectionConfigurationError("Remote MCP configuration has unsupported fields.")
        url = value.get("url")
        _remote_url(url)
        if not _string_map(value.get("headers", {})):
            raise McpConnectionConfigurationError("MCP headers must map strings to strings.")
        headers = value.get("headers", {})
        folded = [name.casefold() for name in headers]
        if len(set(folded)) != len(folded):
            raise McpConnectionConfigurationError("MCP header names cannot be duplicated by case.")
        if any(name in {"authorization", "cookie", "proxy-authorization", "x-api-key"} for name in folded):
            raise McpConnectionConfigurationError("Credentials must use the separate Connection credential owner.")
        return McpConnectionConfiguration(
            transport=transport,
            endpoint=url,
            headers=tuple(sorted(headers.items())),
        )
    if transport == "stdio":
        if set(value) - {"type", "command", "args", "env", "cwd"}:
            raise McpConnectionConfigurationError("stdio MCP configuration has unsupported fields.")
        command = value.get("command")
        if not isinstance(command, str) or not command or any(character.isspace() for character in command):
            raise McpConnectionConfigurationError("stdio command must be one executable token.")
        args = value.get("args", [])
        if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
            raise McpConnectionConfigurationError("stdio args must be strings.")
        if not _string_map(value.get("env", {})):
            raise McpConnectionConfigurationError("stdio environment must map strings to strings.")
        env = value.get("env", {})
        cwd = value.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise McpConnectionConfigurationError("stdio cwd must be a string.")
        if "PLUGIN_ROOT" in env or "PLUGIN_DATA" in env:
            raise McpConnectionConfigurationError("Reserved Plugin environment variables cannot be supplied.")
        return McpConnectionConfiguration(
            transport=transport,
            command=command,
            args=tuple(args),
            env=tuple(sorted(env.items())),
            cwd=cwd,
        )
    raise McpConnectionConfigurationError("MCP transport must be streamable-http, sse, or stdio.")


def _remote_url(value: object) -> None:
    if not isinstance(value, str):
        raise McpConnectionConfigurationError("MCP URL is required.")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise McpConnectionConfigurationError("MCP URL must be an absolute HTTP(S) URL without credentials or fragments.")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise McpConnectionConfigurationError("Remote MCP connections require HTTPS.")


def _string_map(value: object) -> bool:
    return isinstance(value, dict) and all(isinstance(key, str) and isinstance(item, str) for key, item in value.items())
