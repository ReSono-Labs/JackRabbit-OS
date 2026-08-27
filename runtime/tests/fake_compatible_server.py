"""In-process fake OpenAI-compatible provider server for slice 2 tests."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VALID_KEY = "test-key"
MODELS = ("deepseek-v4-pro", "deepseek-v4-flash", "glm-5.2")


class FakeCompatibleServer:
    """Serves GET /models and POST /v1/chat/completions (echo)."""

    def __init__(self, *, require_key: bool = True) -> None:
        self.require_key = require_key
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._make_handler())
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._running = False
        self.chat_requests: list[dict] = []

    def _make_handler(self):
        impl = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _authorized(self) -> bool:
                return (not impl.require_key) or self.headers.get("Authorization") == f"Bearer {VALID_KEY}"

            def do_GET(self):
                if self.path.split("?")[0].endswith("/models"):
                    if not self._authorized():
                        self.send_response(401)
                        self.end_headers()
                        return
                    body = json.dumps({"data": [{"id": model_id} for model_id in MODELS]}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_error(404)

            def do_POST(self):
                if self.path.endswith("/chat/completions"):
                    length = int(self.headers.get("Content-Length") or 0)
                    request = json.loads(self.rfile.read(length))
                    impl.chat_requests.append(request)
                    if not self._authorized():
                        self.send_response(401)
                        self.end_headers()
                        return
                    user_message = request["messages"][-1]["content"]
                    model = request.get("model", "")
                    if request.get("stream"):
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.end_headers()
                        chunks = [
                            {"id": "chatcmpl-fake", "object": "chat.completion.chunk", "created": 1,
                             "model": model, "choices": [{"index": 0, "delta": {"role": "assistant", "content": f"echo:{user_message}"}, "finish_reason": None}]},
                            {"id": "chatcmpl-fake", "object": "chat.completion.chunk", "created": 1,
                             "model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
                        ]
                        for chunk in chunks:
                            self.wfile.write(f"data: {json.dumps(chunk, separators=(',', ':'))}\n\n".encode())
                            self.wfile.flush()
                        self.wfile.write(b"data: [DONE]\n\n")
                        self.wfile.flush()
                        return
                    body = json.dumps({
                        "id": "chatcmpl-fake",
                        "object": "chat.completion",
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "message": {"role": "assistant", "content": f"echo:{user_message}"},
                            "finish_reason": "stop",
                        }],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    }).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_error(404)

        return Handler

    def start(self) -> None:
        self._running = True
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=3)

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/v1"
