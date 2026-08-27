"""Bounded MCP 2025-11-25 Streamable HTTP client for outbound connections."""

from __future__ import annotations

import http.client
import json
import os
import queue
import socket
import ssl
import subprocess
import threading
import time
from collections import deque
from typing import Protocol
from urllib.parse import urlsplit

from resono_runtime.security.outbound import resolve_public_host

from .connections import McpConnectionConfiguration


PROTOCOL_VERSION = "2025-11-25"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024

SUPPORTED_TRANSPORTS = frozenset({"streamable-http", "sse", "stdio"})


class McpTransportClient(Protocol):
    """The outbound MCP client surface shared by every transport."""

    def initialize(self) -> dict[str, object]: ...
    def discover_tools(self) -> object: ...
    def call_tool(self, name: str, arguments: dict[str, object]) -> object: ...
    def close(self) -> None: ...


class McpConnectionError(RuntimeError):
    pass


class StreamableHttpMcpClient:
    def __init__(self, configuration: McpConnectionConfiguration, *, credential_headers: dict[str, str] | None = None) -> None:
        if configuration.transport != "streamable-http" or configuration.endpoint is None:
            raise ValueError("Streamable HTTP configuration is required.")
        parsed = urlsplit(configuration.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("MCP endpoint is invalid.")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if parsed.scheme == "http":
            if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Non-loopback MCP endpoints require HTTPS.")
            addresses = (parsed.hostname,)
        else:
            _, addresses = resolve_public_host(parsed.hostname, port)
        self._parsed = parsed
        self._addresses = addresses
        self._headers = {**dict(configuration.headers), **(credential_headers or {})}
        self._session_id: str | None = None
        self._next_id = 1
        self._initialized = False

    def initialize(self) -> dict[str, object]:
        result = self._request(
            "initialize",
            {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "resono-r1", "version": "0.1.0"}},
        )
        if not isinstance(result, dict) or result.get("protocolVersion") != PROTOCOL_VERSION:
            raise McpConnectionError("MCP server negotiated an unsupported protocol version.")
        self._notify("notifications/initialized", {})
        self._initialized = True
        return result

    def discover_tools(self) -> object:
        if not self._initialized:
            self.initialize()
        result = self._request("tools/list", {})
        if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
            raise McpConnectionError("MCP tools/list response is invalid.")
        return result["tools"]

    def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        if not self._initialized:
            self.initialize()
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if not isinstance(result, dict):
            raise McpConnectionError("MCP tools/call response is invalid.")
        return result

    def close(self) -> None:
        if self._session_id is None:
            return
        connection = self._connection()
        try:
            connection.request("DELETE", self._path(), headers={"Mcp-Session-Id": self._session_id, "MCP-Protocol-Version": PROTOCOL_VERSION})
            response = connection.getresponse()
            response.read(MAX_RESPONSE_BYTES + 1)
        finally:
            connection.close()
            self._session_id = None
            self._initialized = False

    def _request(self, method: str, params: dict[str, object]) -> object:
        request_id = self._next_id
        self._next_id += 1
        payload = self._post({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0" or payload.get("id") != request_id or "error" in payload:
            raise McpConnectionError("MCP server returned an invalid response.")
        return payload.get("result")

    def _notify(self, method: str, params: dict[str, object]) -> None:
        self._post({"jsonrpc": "2.0", "method": method, "params": params}, response_optional=True)

    def _post(self, value: dict[str, object], *, response_optional: bool = False) -> object:
        connection = self._connection()
        headers = {**self._headers, "Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": PROTOCOL_VERSION}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        try:
            connection.request("POST", self._path(), body=json.dumps(value, separators=(",", ":")).encode(), headers=headers)
            response = connection.getresponse()
            if 300 <= response.status < 400:
                raise McpConnectionError("MCP redirects are not followed.")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise McpConnectionError("MCP response exceeded the size limit.")
            if response.status >= 400:
                raise McpConnectionError("MCP server rejected the request.")
            self._session_id = response.getheader("Mcp-Session-Id") or self._session_id
            if not raw and response_optional:
                return None
            content_type = (response.getheader("Content-Type") or "").split(";", 1)[0].strip().casefold()
            if content_type == "application/json":
                return json.loads(raw)
            if content_type == "text/event-stream":
                return _sse_json(raw)
            raise McpConnectionError("MCP response content type is unsupported.")
        except (OSError, json.JSONDecodeError) as error:
            raise McpConnectionError("MCP connection failed.") from error
        finally:
            connection.close()

    def _connection(self) -> http.client.HTTPConnection:
        port = self._parsed.port or (443 if self._parsed.scheme == "https" else 80)
        if self._parsed.scheme == "https":
            return _PinnedHttpsConnection(self._parsed.hostname, port, self._addresses[0], timeout=10)
        return http.client.HTTPConnection(self._parsed.hostname, port, timeout=10)

    def _path(self) -> str:
        path = self._parsed.path or "/"
        return path + (f"?{self._parsed.query}" if self._parsed.query else "")


def _sse_json(raw: bytes) -> object:
    data_lines: list[str] = []
    for line in raw.decode("utf-8").splitlines():
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif not line and data_lines:
            break
    if not data_lines:
        raise McpConnectionError("MCP event stream contained no response event.")
    return json.loads("\n".join(data_lines))


class _PinnedHttpsConnection(http.client.HTTPSConnection):
    """Connect to the validated address while retaining hostname TLS checks."""

    def __init__(self, host: str, port: int, address: str, *, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._validated_address = address

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._validated_address, self.port),
            self.timeout,
            self.source_address,
        )
        if self._tunnel_host:
            self._tunnel()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


class SseMcpClient:
    """MCP 2025-11-25 SSE transport outbound client.

    Opens a persistent GET event stream, learns the POST message endpoint from the
    ``endpoint`` event, and exchanges JSON-RPC over the POST endpoint. Responses
    are read either directly from the POST reply (hybrid servers) or from the
    event stream (classic SSE servers).
    """

    RESPONSE_TIMEOUT = 30.0

    def __init__(
        self,
        configuration: McpConnectionConfiguration,
        *,
        credential_headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> None:
        if configuration.transport != "sse" or configuration.endpoint is None:
            raise ValueError("SSE MCP configuration is required.")
        parsed = urlsplit(configuration.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("MCP endpoint is invalid.")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if parsed.scheme == "http":
            if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Non-loopback MCP endpoints require HTTPS.")
            addresses = (parsed.hostname,)
        else:
            _, addresses = resolve_public_host(parsed.hostname, port)
        self._parsed = parsed
        self._addresses = addresses
        self._headers = {**dict(configuration.headers), **(credential_headers or {})}
        self._timeout = timeout or self.RESPONSE_TIMEOUT
        self._next_id = 1
        self._initialized = False
        self._session_id: str | None = None
        self._message_url: str | None = None
        self._closed = False
        self._stream_conn: http.client.HTTPConnection | None = None
        self._pending: dict[int, "queue.Queue[object]"] = {}
        self._pending_lock = threading.Lock()
        self._stream_lock = threading.Lock()
        self._endpoint_event = threading.Event()
        self._endpoint_error: McpConnectionError | None = None
        self._open_stream()

    def initialize(self) -> dict[str, object]:
        result = self._request(
            "initialize",
            {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "resono-r1", "version": "0.1.0"}},
        )
        if not isinstance(result, dict) or result.get("protocolVersion") != PROTOCOL_VERSION:
            raise McpConnectionError("MCP server negotiated an unsupported protocol version.")
        self._notify("notifications/initialized", {})
        self._initialized = True
        return result

    def discover_tools(self) -> object:
        if not self._initialized:
            self.initialize()
        result = self._request("tools/list", {})
        if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
            raise McpConnectionError("MCP tools/list response is invalid.")
        return result["tools"]

    def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        if not self._initialized:
            self.initialize()
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if not isinstance(result, dict):
            raise McpConnectionError("MCP tools/call response is invalid.")
        return result

    def _wait_for_message_url(self, timeout: float = 5.0) -> None:
        self._endpoint_event.wait(timeout=min(timeout, self._timeout))
        if self._message_url is not None:
            return
        if self._endpoint_error is not None:
            raise self._endpoint_error
        raise McpConnectionError("MCP SSE endpoint event was not received.")

    def close(self) -> None:
        self._closed = True
        if self._endpoint_error is None:
            self._endpoint_error = McpConnectionError("MCP SSE stream is closed.")
        self._endpoint_event.set()
        connection = self._stream_conn
        self._stream_conn = None
        if connection is not None:
            try:
                connection.close()
            except OSError:
                pass
        thread = getattr(self, "_stream_thread", None)
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3)
        self._fail_pending(McpConnectionError("MCP SSE stream is closed."))

    def _open_stream(self) -> None:
        connection = self._connection()
        headers = {
            **self._headers,
            "Accept": "text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        try:
            connection.request("GET", self._stream_path(), headers=headers)
            response = connection.getresponse()
        except OSError as error:
            connection.close()
            raise McpConnectionError("MCP SSE stream connection failed.") from error
        if response.status >= 400:
            connection.close()
            raise McpConnectionError("MCP server rejected the SSE stream request.")
        self._stream_conn = connection
        self._stream_thread = threading.Thread(target=self._read_stream, args=(response,), daemon=True)
        self._stream_thread.start()

    def _ensure_stream(self) -> None:
        if self._closed or self._stream_conn is not None:
            return
        with self._stream_lock:
            if self._closed or self._stream_conn is not None:
                return
            try:
                self._open_stream()
            except McpConnectionError:
                pass

    def _read_stream(self, response: http.client.HTTPResponse) -> None:
        event_name: str | None = None
        data_lines: list[str] = []
        try:
            while not self._closed:
                line = response.readline()
                if line is None:
                    continue
                if line == b"":
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\r\n")
                if text == "":
                    event = event_name or ("message" if data_lines else None)
                    if event == "endpoint":
                        self._handle_endpoint("\n".join(data_lines))
                    elif event == "message" and data_lines:
                        self._handle_message("\n".join(data_lines))
                    event_name = None
                    data_lines = []
                elif text.startswith("event:"):
                    event_name = text[6:].strip()
                elif text.startswith("data:"):
                    data_lines.append(text[5:].lstrip())
        except (OSError, ValueError):
            pass
        finally:
            self._stream_conn = None
            try:
                response.close()
            except OSError:
                pass
            if not self._closed:
                if self._message_url is None and self._endpoint_error is None:
                    self._raise_stream_error("MCP SSE stream closed before the endpoint event.")
                self._ensure_stream()

    def _handle_endpoint(self, data: str) -> None:
        if self._message_url is not None or not data:
            return
        parsed = urlsplit(data)
        if parsed.scheme:
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                self._raise_stream_error("MCP SSE endpoint event is invalid.")
                return
            self._message_url = data
        elif data.startswith("/"):
            self._message_url = f"{self._parsed.scheme}://{self._parsed.netloc}{data}"
        else:
            self._raise_stream_error("MCP SSE endpoint event must be an absolute URL or root path.")
            return
        self._endpoint_event.set()

    def _handle_message(self, data: str) -> None:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError as error:
            raise McpConnectionError("MCP SSE message event is invalid.") from error
        if not isinstance(payload, dict) or "id" not in payload:
            return
        self._deliver(payload)

    def _raise_stream_error(self, message: str) -> None:
        if self._endpoint_error is None:
            self._endpoint_error = McpConnectionError(message)
        self._endpoint_event.set()
        self._fail_pending(self._endpoint_error)

    def _request(self, method: str, params: dict[str, object]) -> object:
        request_id = self._next_id
        self._next_id += 1
        waiting: "queue.Queue[object]" = queue.Queue(maxsize=1)
        with self._pending_lock:
            if self._closed:
                raise McpConnectionError("MCP SSE client is closed.")
            self._pending[request_id] = waiting
        try:
            try:
                raw = self._post({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
            except McpConnectionError:
                with self._pending_lock:
                    self._pending.pop(request_id, None)
                raise
            if raw is None:
                payload = waiting.get(timeout=self._timeout)
            else:
                waiting.put_nowait(raw)
                payload = waiting.get(timeout=self._timeout)
        except queue.Empty as error:
            raise McpConnectionError("MCP SSE response timed out.") from error
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)
        if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0" or payload.get("id") != request_id or "error" in payload:
            raise McpConnectionError("MCP server returned an invalid response.")
        return payload.get("result")

    def _notify(self, method: str, params: dict[str, object]) -> None:
        self._post({"jsonrpc": "2.0", "method": method, "params": params}, response_optional=True)

    def _post(self, value: dict[str, object], *, response_optional: bool = False) -> object | None:
        self._ensure_stream()
        message_url = self._message_url
        if message_url is None:
            self._wait_for_message_url()
            message_url = self._message_url
        parsed = urlsplit(message_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise McpConnectionError("MCP SSE message endpoint is invalid.")
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), timeout=10)
        headers = {
            **self._headers,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        try:
            connection.request("POST", parsed.path or "/", body=json.dumps(value, separators=(",", ":")).encode(), headers=headers)
            response = connection.getresponse()
        except OSError as error:
            raise McpConnectionError("MCP SSE connection failed.") from error
        try:
            if response.status >= 400:
                raise McpConnectionError("MCP server rejected the request.")
            self._session_id = response.getheader("Mcp-Session-Id") or self._session_id
            if response.status in {202, 204}:
                return None
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            content_type = (response.getheader("Content-Type") or "").split(";", 1)[0].strip().casefold()
            if content_type == "application/json":
                return json.loads(raw)
            if content_type == "text/event-stream":
                return _sse_json(raw)
            return None
        except (OSError, json.JSONDecodeError) as error:
            raise McpConnectionError("MCP SSE connection failed.") from error
        finally:
            connection.close()

    def _deliver(self, payload: dict[str, object]) -> None:
        request_id = payload.get("id")
        if not isinstance(request_id, int):
            return
        with self._pending_lock:
            waiting = self._pending.get(request_id)
        if waiting is not None:
            waiting.put_nowait(payload)

    def _fail_pending(self, error: McpConnectionError) -> None:
        with self._pending_lock:
            pending = list(self._pending.values())
            self._pending.clear()
        for waiting in pending:
            waiting.put_nowait({"jsonrpc": "2.0", "id": -1, "error": {"code": -32000, "message": str(error)}})

    def _stream_path(self) -> str:
        path = self._parsed.path or "/"
        return path + (f"?{self._parsed.query}" if self._parsed.query else "")

    def _connection(self) -> http.client.HTTPConnection:
        port = self._parsed.port or (443 if self._parsed.scheme == "https" else 80)
        if self._parsed.scheme == "https":
            return _PinnedHttpsConnection(self._parsed.hostname, port, self._addresses[0], timeout=10)
        return http.client.HTTPConnection(self._parsed.hostname, port, timeout=10)


def client_for(
    configuration: McpConnectionConfiguration,
    *,
    credential_headers: dict[str, str] | None = None,
) -> McpTransportClient:
    """Transport-agnostic outbound MCP client factory."""
    if configuration.transport == "streamable-http":
        return StreamableHttpMcpClient(configuration, credential_headers=credential_headers)
    if configuration.transport == "sse":
        return SseMcpClient(configuration, credential_headers=credential_headers)
    if configuration.transport == "stdio":
        return StdioMcpClient(configuration, credential_headers=credential_headers)
    raise McpConnectionError(
        f"Unsupported MCP transport {configuration.transport!r}."
    )

_STDIO_STREAM_END = object()


class StdioMcpClient:
    """MCP stdio transport outbound client.

    Spawns the configured command and exchanges newline-delimited JSON-RPC over
    stdin/stdout. Stderr is captured (capped) for diagnostics. The process is
    always killed and reaped on timeout or close.
    """

    def __init__(
        self,
        configuration: McpConnectionConfiguration,
        *,
        credential_headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> None:
        if configuration.transport != "stdio" or configuration.command is None:
            raise ValueError("stdio MCP configuration is required.")
        if credential_headers:
            raise ValueError("stdio MCP connections cannot carry credential headers.")
        environment = dict(os.environ)
        for key, value in configuration.env:
            environment[key] = value
        self._timeout = timeout or 30.0
        self._next_id = 1
        self._initialized = False
        self._closed = False
        self._responses: "queue.Queue[object]" = queue.Queue(maxsize=128)
        self._stderr_lines: deque[str] = deque(maxlen=64)
        self._stderr_lock = threading.Lock()
        try:
            self._process = subprocess.Popen(
                (configuration.command, *configuration.args),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=configuration.cwd,
                env=environment,
                text=True,
                bufsize=1,
            )
        except OSError as error:
            raise McpConnectionError(f"stdio MCP command failed to start: {error}") from error
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def initialize(self) -> dict[str, object]:
        result = self._request(
            "initialize",
            {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "resono-r1", "version": "0.1.0"}},
        )
        if not isinstance(result, dict) or result.get("protocolVersion") != PROTOCOL_VERSION:
            raise McpConnectionError("MCP server negotiated an unsupported protocol version.")
        self._notify("notifications/initialized", {})
        self._initialized = True
        return result

    def discover_tools(self) -> object:
        if not self._initialized:
            self.initialize()
        result = self._request("tools/list", {})
        if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
            raise McpConnectionError("MCP tools/list response is invalid.")
        return result["tools"]

    def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        if not self._initialized:
            self.initialize()
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if not isinstance(result, dict):
            raise McpConnectionError("MCP tools/call response is invalid.")
        return result

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._kill()
        self._stdout_thread.join(timeout=3)
        self._stderr_thread.join(timeout=3)

    def diagnostics(self) -> str:
        with self._stderr_lock:
            return "".join(self._stderr_lines)

    def _request(self, method: str, params: dict[str, object], timeout: float | None = None) -> object:
        request_id = self._next_id
        self._next_id += 1
        line = json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
            separators=(",", ":"),
        )
        try:
            stdin = self._process.stdin
            if stdin is None:
                raise McpConnectionError("stdio MCP process is not writable.")
            stdin.write(line + "\n")
            stdin.flush()
        except (OSError, ValueError) as error:
            raise McpConnectionError("stdio MCP write failed.") from error
        deadline = time.monotonic() + (timeout or self._timeout)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._kill()
                raise McpConnectionError("stdio MCP response timed out.")
            try:
                item = self._responses.get(timeout=remaining)
            except queue.Empty:
                continue
            if item is _STDIO_STREAM_END:
                raise McpConnectionError("stdio MCP process closed its output.")
            if not isinstance(item, dict) or item.get("id") != request_id:
                continue
            if "error" in item:
                error = item["error"]
                detail = error.get("message") if isinstance(error, dict) else None
                raise McpConnectionError(f"stdio MCP request failed: {detail or 'unknown error'}")
            return item.get("result")

    def _notify(self, method: str, params: dict[str, object]) -> None:
        line = json.dumps({"jsonrpc": "2.0", "method": method, "params": params}, separators=(",", ":"))
        try:
            stdin = self._process.stdin
            if stdin is None:
                return
            stdin.write(line + "\n")
            stdin.flush()
        except (OSError, ValueError):
            pass

    def _read_stdout(self) -> None:
        stdout = self._process.stdout
        if stdout is None:
            return
        try:
            for line in stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict) and "id" in payload:
                    self._responses.put(payload)
        except (OSError, ValueError):
            pass
        finally:
            try:
                self._responses.put_nowait(_STDIO_STREAM_END)
            except queue.Full:
                pass

    def _read_stderr(self) -> None:
        stderr = self._process.stderr
        if stderr is None:
            return
        try:
            for line in stderr:
                with self._stderr_lock:
                    self._stderr_lines.append(line)
        except (OSError, ValueError):
            pass

    def _kill(self) -> None:
        process = getattr(self, "_process", None)
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
