from __future__ import annotations

from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import threading
from typing import Any

from .events import RuntimeEventStream
from ..security.pairing import PairingAuthority, PairingDenied
from ..providers.controller import ProviderController
from ..providers.openai import OpenAIProviderError
from ..mcp import LocalMcpServer
from ..storage.lifecycle_repository import LifecycleRepository
from ..agents import AgentsSdkTextRunner
from ..providers.openai import OpenAISubscription
from ..storage.profile_settings import UserProfileRepository


HealthReader = Callable[[], dict[str, object]]
RestartRequest = Callable[[], None]


class RuntimeHttpServer:
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
        restart_request: RestartRequest | None = None,
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("private runtime API must bind to loopback")
        handler = _handler(
            token=token,
            health=health,
            lifecycle=lifecycle,
            events=events,
            pairing=pairing,
            providers=providers,
            text_runner=text_runner,
            subscription=subscription,
            mcp=mcp,
            profile=profile,
            restart_request=restart_request,
        )
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
    health: HealthReader,
    lifecycle: LifecycleRepository,
    events: RuntimeEventStream,
    pairing: PairingAuthority | None,
    providers: ProviderController | None,
    text_runner: AgentsSdkTextRunner | None,
    subscription: OpenAISubscription | None,
    mcp: LocalMcpServer | None,
    profile: UserProfileRepository | None,
    restart_request: RestartRequest | None,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ReSonoRuntime/0.1"

        def do_GET(self) -> None:
            if not self._authorized():
                self._json(401, {"error": {"code": "unauthorized", "message": "Valid local authorization is required."}})
                return
            path = self.path.split("?", 1)[0]
            if path == "/v1/health":
                self._json(200, health())
                return
            if path == "/v1/lifecycle-records/runtime.start_count":
                try:
                    record = lifecycle.get("runtime.start_count")
                except KeyError:
                    self._json(404, {"error": {"code": "record_not_found", "message": "Lifecycle record not found."}})
                    return
                self._json(200, {"key": record.key, "value": record.value, "updatedAt": record.updated_at})
                return
            if path == "/v1/events":
                self._events()
                return
            if path == "/v1/management/pairing" and pairing is not None:
                code = pairing.current_code()
                self._json(200, {"code": code.value, "expiresAt": code.expires_at})
                return
            if path == "/v1/management/status" and pairing is not None:
                session = self._browser_session(pairing, mutation=False)
                if session is None:
                    return
                self._json(200, {**health(), "csrfToken": session.csrf_token})
                return
            if path == "/v1/management/openai" and pairing is not None and providers is not None:
                if self._browser_session(pairing, mutation=False) is None:
                    return
                try:
                    self._json(200, providers.status(refresh=False))
                except OpenAIProviderError as error:
                    self._provider_error(error)
                return
            if path == "/v1/management/openai/subscription" and pairing is not None and subscription is not None:
                if self._browser_session(pairing, mutation=False) is None:
                    return
                self._json(200, subscription.status())
                return
            if path == "/v1/management/profile" and pairing is not None and profile is not None:
                if self._browser_session(pairing, mutation=False) is None:
                    return
                self._json(200, {"displayName": profile.profile().display_name})
                return
            self._json(404, {"error": {"code": "not_found", "message": "Not found."}})

        def do_POST(self) -> None:
            if not self._authorized():
                self._json(401, {"error": {"code": "unauthorized", "message": "Valid local authorization is required."}})
                return
            path = self.path.split("?", 1)[0]
            if path == "/v1/mcp" and mcp is not None:
                payload = self._request_json(max_bytes=65_536)
                if payload is None:
                    return
                result = mcp.handle(
                    payload,
                    session_id=self.headers.get("Mcp-Session-Id"),
                    protocol_version=self.headers.get("MCP-Protocol-Version"),
                )
                headers = {"Mcp-Session-Id": result.session_id} if result.session_id else None
                if result.payload is None:
                    self._empty(result.status, headers=headers)
                else:
                    self._json(result.status, result.payload, headers=headers)
                return
            if path == "/v1/voice/calls" and providers is not None:
                payload = self._request_json(max_bytes=300_000)
                if payload is None:
                    return
                try:
                    call = providers.create_realtime_call(str(payload.get("sdp", "")))
                    self._json(
                        200,
                        {
                            "sdp": call.sdp,
                            "connectGreetingEvent": call.connect_greeting_event,
                        },
                    )
                except OpenAIProviderError as error:
                    self._provider_error(error)
                return
            if path == "/v1/management/text/turns" and text_runner is not None:
                if pairing is None or self._browser_session(pairing, mutation=True) is None:
                    return
                payload = self._request_json(max_bytes=20_000)
                if payload is None:
                    return
                try:
                    result = text_runner.run(str(payload.get("input", "")))
                    self._json(200, {"text": result.text, "model": result.model})
                except OpenAIProviderError as error:
                    self._provider_error(error)
                return
            if path.startswith("/v1/management/openai/subscription/") and subscription is not None:
                if pairing is None or self._browser_session(pairing, mutation=True) is None:
                    return
                payload = self._request_json()
                if payload is None:
                    return
                try:
                    if path == "/v1/management/openai/subscription/start":
                        started = subscription.start_auth()
                        result = {
                            "authSessionId": started.auth_session_id,
                            "verificationUrl": started.verification_url,
                            "userCode": started.user_code,
                            "expiresAt": started.expires_at,
                            "pollIntervalSeconds": started.poll_interval_seconds,
                            "status": "auth_pending",
                        }
                    elif path == "/v1/management/openai/subscription/poll":
                        result = subscription.poll_auth(str(payload.get("authSessionId", "")))
                        if result.get("status") == "completed" and providers is not None:
                            providers.select_access_path("subscription")
                    elif path == "/v1/management/openai/subscription/disconnect":
                        result = (
                            providers.disconnect_subscription()
                            if providers is not None
                            else subscription.disconnect()
                        )
                    else:
                        self._json(404, {"error": {"code": "not_found", "message": "Not found."}})
                        return
                    self._json(200, result)
                except OpenAIProviderError as error:
                    self._provider_error(error)
                return
            if path == "/v1/management/pair" and pairing is not None:
                payload = self._request_json()
                if payload is None:
                    return
                try:
                    session = pairing.pair(
                        str(payload.get("code", "")),
                        self.headers.get("X-ReSono-Forwarded-Origin", ""),
                        self.headers.get("Origin"),
                    )
                except PairingDenied:
                    self._json(403, {"error": {"code": "pairing_denied", "message": "Pairing code is invalid or expired."}})
                    return
                cookie = (
                    f"resono_session={session.token}; Path=/; Max-Age=1800; "
                    "Secure; HttpOnly; SameSite=Strict"
                )
                self._json(
                    200,
                    {"csrfToken": session.csrf_token, "expiresAt": session.expires_at},
                    headers={"Set-Cookie": cookie},
                )
                return
            if path == "/v1/management/restart" and pairing is not None:
                if self._browser_session(pairing, mutation=True) is None:
                    return
                if restart_request is None:
                    self._json(503, {"error": {"code": "restart_unavailable", "message": "Runtime restart is unavailable."}})
                    return
                self._json(202, {"status": "restarting"})
                restart_request()
                return
            if path == "/v1/management/profile" and pairing is not None and profile is not None:
                if self._browser_session(pairing, mutation=True) is None:
                    return
                payload = self._request_json()
                if payload is None:
                    return
                try:
                    saved = profile.save(_optional_string(payload.get("displayName")))
                    self._json(200, {"displayName": saved.display_name})
                except ValueError as error:
                    self._json(400, {"error": {"code": "invalid_profile", "message": str(error)}})
                return
            if path.startswith("/v1/management/openai/") and pairing is not None and providers is not None:
                if self._browser_session(pairing, mutation=True) is None:
                    return
                payload = self._request_json()
                if payload is None:
                    return
                try:
                    if path == "/v1/management/openai/connect":
                        result = providers.connect_platform(str(payload.get("apiKey", "")))
                    elif path == "/v1/management/openai/disconnect":
                        result = providers.disconnect_platform()
                    elif path == "/v1/management/openai/models":
                        result = providers.select_models(
                            text_model=_optional_string(payload.get("textModel")),
                            realtime_model=_optional_string(payload.get("realtimeModel")),
                            reasoning_effort=_optional_string(payload.get("reasoningEffort")),
                        )
                    elif path == "/v1/management/openai/refresh":
                        result = providers.status(refresh=True)
                    elif path == "/v1/management/openai/access":
                        result = providers.select_access_path(str(payload.get("accessPath", "")))
                    else:
                        self._json(404, {"error": {"code": "not_found", "message": "Not found."}})
                        return
                    self._json(200, result)
                except (ValueError, OpenAIProviderError) as error:
                    if isinstance(error, OpenAIProviderError):
                        self._provider_error(error)
                    else:
                        self._json(400, {"error": {"code": "invalid_request", "message": str(error)}})
                return
            self._json(404, {"error": {"code": "not_found", "message": "Not found."}})

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _authorized(self) -> bool:
            header = (self.headers.get("Authorization") or "").strip()
            supplied = header[7:].strip() if header.lower().startswith("bearer ") else ""
            return bool(supplied) and hmac.compare_digest(supplied, token)

        def _browser_session(
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
                self._json(403, {"error": {"code": "browser_session_denied", "message": "Pairing is required."}})
                return None

        def _request_json(self, *, max_bytes: int = 4096) -> dict[str, object] | None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0 or length > max_bytes:
                self._json(400, {"error": {"code": "invalid_request", "message": "Request body is invalid."}})
                return None
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._json(400, {"error": {"code": "invalid_json", "message": "Request body must be JSON."}})
                return None
            if not isinstance(payload, dict):
                self._json(400, {"error": {"code": "invalid_json", "message": "Request body must be an object."}})
                return None
            return payload

        def _provider_error(self, error: OpenAIProviderError) -> None:
            self._json(error.status, {"error": {"code": error.code, "message": str(error)}})

        def _empty(self, status: int, *, headers: dict[str, str] | None = None) -> None:
            self.send_response(status)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()

        def _events(self) -> None:
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

        def _json(
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

    return Handler


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None
