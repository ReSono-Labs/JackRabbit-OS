from __future__ import annotations

from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import threading
from typing import Any

from .events import RuntimeEventStream
from .routes import RuntimeRoutes
from ..security.pairing import PairingAuthority, PairingDenied
from ..providers.controller import ProviderController
from ..providers.openai import OpenAIProviderError
from ..mcp import LocalMcpServer
from ..storage.lifecycle_repository import LifecycleRepository
from ..storage.sessions import SessionTranscriptRepository
from ..agents import AgentsSdkTextRunner
from ..memory import MemoryService
from ..providers.openai import OpenAISubscription
from ..storage.profile_settings import UserProfileRepository
from .skill_routes import SkillRoutes
from .mail_routes import MailRoutes
from .calendar_routes import CalendarRoutes
from .task_routes import TaskRoutes
from .mcp_routes import McpRoutes
from .connection_routes import ConnectionRoutes
from .tool_routes import ToolRoutes
from .plugin_routes import PluginRoutes
from .creation_routes import CreationRoutes
from .handoff_routes import HandoffRoutes


HealthReader = Callable[[], dict[str, object]]
RestartRequest = Callable[[], None]


class RuntimeHttpServer:
    """Transport for the private loopback runtime API.

    Owns binding, threading, bearer authorization, and request/response
    mechanics only. Route ownership lives in ``api.routes.RuntimeRoutes``;
    new endpoints are added there, not here.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        token: str,
        health: HealthReader,
        lifecycle: LifecycleRepository,
        events: RuntimeEventStream,
        pairing: PairingAuthority | None = None,
        providers: ProviderController | None = None,
        text_runner: AgentsSdkTextRunner | None = None,
        subscription: OpenAISubscription | None = None,
        mcp: LocalMcpServer | None = None,
        profile: UserProfileRepository | None = None,
        sessions: SessionTranscriptRepository | None = None,
        memory: MemoryService | None = None,
        restart_request: RestartRequest | None = None,
        skills: SkillRoutes | None = None,
        mail: MailRoutes | None = None,
        calendar: CalendarRoutes | None = None,
        tasks: TaskRoutes | None = None,
        outbound_mcp: McpRoutes | None = None,
        tools: ToolRoutes | None = None,
        plugins: PluginRoutes | None = None,
        creations: CreationRoutes | None = None,
        connections: ConnectionRoutes | None = None,
        handoffs: HandoffRoutes | None = None,
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("private runtime API must bind to loopback")
        routes = RuntimeRoutes(
            health=health,
            lifecycle=lifecycle,
            events=events,
            pairing=pairing,
            providers=providers,
            text_runner=text_runner,
            subscription=subscription,
            mcp=mcp,
            profile=profile,
            sessions=sessions,
            memory=memory,
            restart_request=restart_request,
            skills=skills,
            mail=mail,
            calendar=calendar,
            tasks=tasks,
            outbound_mcp=outbound_mcp,
            tools=tools,
            plugins=plugins,
            creations=creations,
            connections=connections,
            handoffs=handoffs,
        )
        handler = _handler(token=token, events=events, routes=routes)
        self._server = ThreadingHTTPServer((host, port), handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="resono-runtime-http",
            daemon=True,
        )

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=3.0)


def _handler(
    *,
    token: str,
    events: RuntimeEventStream,
    routes: RuntimeRoutes,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ReSonoRuntime/0.1"

        def do_GET(self) -> None:
            if not self._authorized():
                self.respond_json(401, {"error": {"code": "unauthorized", "message": "Valid local authorization is required."}})
                return
            routes.handle_get(self)

        def do_POST(self) -> None:
            if not self._authorized():
                self.respond_json(401, {"error": {"code": "unauthorized", "message": "Valid local authorization is required."}})
                return
            routes.handle_post(self)

        def do_DELETE(self) -> None:
            if not self._authorized():
                self.respond_json(401, {"error": {"code": "unauthorized", "message": "Valid local authorization is required."}})
                return
            routes.handle_delete(self)

        def log_message(self, format: str, *args: Any) -> None:
            return

        # Route-request surface consumed by RuntimeRoutes (see api.routes.RouteRequest).

        def respond_json(
            self,
            status: int,
            payload: dict[str, object],
            *,
            headers: dict[str, str] | None = None,
        ) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def respond_empty(self, status: int, *, headers: dict[str, str] | None = None) -> None:
            self.send_response(status)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()

        def respond_bytes(self, status: int, payload: bytes, *, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def stream_events(self) -> None:
            latest, subscriber = events.subscribe()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                self.wfile.write(latest.sse_bytes())
                self.wfile.flush()
                while True:
                    event = events.next_event(subscriber)
                    self.wfile.write(event.sse_bytes() if event else b": heartbeat\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                events.unsubscribe(subscriber)

        def browser_session(
            self,
            authority: PairingAuthority,
            *,
            mutation: bool,
        ) -> object | None:
            session_token = ""
            for item in (self.headers.get("Cookie") or "").split(";"):
                name, separator, value = item.strip().partition("=")
                if separator and name == "resono_session":
                    session_token = value
                    break
            try:
                return authority.authorize(
                    session_token,
                    self.headers.get("X-ReSono-Forwarded-Origin", ""),
                    request_origin=self.headers.get("Origin"),
                    csrf_token=self.headers.get("X-CSRF-Token"),
                    mutation=mutation,
                )
            except PairingDenied:
                self.respond_json(403, {"error": {"code": "browser_session_denied", "message": "Pairing is required."}})
                return None

        def request_json(self, *, max_bytes: int = 4096) -> dict[str, object] | None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0 or length > max_bytes:
                self.respond_json(400, {"error": {"code": "invalid_request", "message": "Request body is invalid."}})
                return None
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.respond_json(400, {"error": {"code": "invalid_json", "message": "Request body must be JSON."}})
                return None
            if not isinstance(payload, dict):
                self.respond_json(400, {"error": {"code": "invalid_json", "message": "Request body must be an object."}})
                return None
            return payload

        def request_bytes(self, *, max_bytes: int) -> bytes | None:
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                length = -1
            if length < 0 or length > max_bytes:
                self.respond_json(400, {"error": {"code": "invalid_request", "message": "Request body is invalid."}})
                return None
            return self.rfile.read(length)

        def provider_error(self, error: OpenAIProviderError) -> None:
            payload: dict[str, object] = {"code": error.code, "message": str(error)}
            if error.details:
                payload["details"] = error.details
            self.respond_json(error.status, {"error": payload})

        def _authorized(self) -> bool:
            header = (self.headers.get("Authorization") or "").strip()
            supplied = header[7:].strip() if header.lower().startswith("bearer ") else ""
            return bool(supplied) and hmac.compare_digest(supplied, token)

    return Handler
