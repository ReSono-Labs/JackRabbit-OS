"""In-process fake MCP SSE server for transport tests (stdlib only)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from queue import Queue

PROTOCOL_VERSION = "2025-11-25"


class FakeSseMcpServer:
    """Serves a minimal MCP SSE transport.

    GET /sse streams an `endpoint` event then `message` events.
    POST /messages accepts JSON-RPC requests. Responses are either returned directly
    on the POST (modern/hybrid servers) or queued back over the SSE stream
    (classic SSE servers), selected by `respond_via_stream`.
    """

    def __init__(self, *, send_endpoint_event: bool = True, respond_via_stream: bool = False,
                 protocol_version: str = PROTOCOL_VERSION) -> None:
        self._send_endpoint_event = send_endpoint_event
        self._respond_via_stream = respond_via_stream
        self._protocol_version = protocol_version
        self._responses: Queue = Queue()
        self._messages: Queue = Queue()
        self._streams: list = []
        self._lock = threading.Lock()
        self.session_id: str | None = None
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._make_handler())
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._running = False

    def _make_handler(self):
        impl = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path.split("?")[0] != "/sse":
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                with impl._lock:
                    impl._streams.append(self.wfile)
                try:
                    if impl._send_endpoint_event:
                        self.wfile.write(b"event: endpoint\ndata: /messages\n\n")
                        self.wfile.flush()
                    while impl._running:
                        item = impl._responses.get(timeout=0.5)
                        if item is None:
                            break
                        payload, session_hint = item
                        if session_hint and impl.session_id is None:
                            impl.session_id = session_hint
                        self.wfile.write(
                            f"event: message\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n".encode()
                        )
                        self.wfile.flush()
                except Exception:
                    pass
                finally:
                    with impl._lock:
                        if self.wfile in impl._streams:
                            impl._streams.remove(self.wfile)

            def do_POST(self):
                if self.path.split("?")[0] != "/messages":
                    self.send_error(404)
                    return
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                session_header = self.headers.get("Mcp-Session-Id")
                if session_header:
                    impl.session_id = session_header
                request = json.loads(body)
                impl._messages.put(request)
                request_id = request.get("id")
                if request_id is None:
                    self.send_response(202)
                    self.end_headers()
                    return
                response = impl._dispatch(request_id, request.get("method"), request.get("params", {}))
                if impl._respond_via_stream:
                    impl._responses.put((response, "sess-123" if request_id == 1 else None))
                    self.send_response(202)
                    if request_id == 1:
                        self.send_header("Mcp-Session-Id", "sess-123")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                if request_id == 1:
                    self.send_header("Mcp-Session-Id", "sess-123")
                self.end_headers()
                self.wfile.write(json.dumps(response, separators=(",", ":")).encode())

        return Handler

    def _dispatch(self, request_id, method, params):
        base = {"jsonrpc": "2.0", "id": request_id}
        if method == "initialize":
            return {**base, "result": {
                "protocolVersion": self._protocol_version,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake-sse", "version": "1.0.0"},
            }}
        if method == "tools/list":
            return {**base, "result": {"tools": [
                {"name": "echo", "description": "Echo text back.",
                 "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
                {"name": "add", "description": "Add two numbers.",
                 "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}},
            ]}}
        if method == "tools/call":
            args = params.get("arguments", {})
            return {**base, "result": {"content": [{"type": "text", "text": json.dumps(args)}], "isError": False}}
        return {**base, "error": {"code": -32601, "message": "method not found"}}

    def wait_for_message(self, timeout: float = 5.0) -> dict:
        return self._messages.get(timeout=timeout)

    def start(self) -> None:
        self._running = True
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=3)

    @property
    def host_port(self):
        return self._server.server_address

    @property
    def url(self) -> str:
        host, port = self.host_port
        return f"http://{host}:{port}/sse"
