from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import parse_qs

from ..agents import AgentsSdkTextRunner
from ..core.logging import runtime_logger
from ..mcp import LocalMcpServer
from ..memory.service import MemoryService
from ..providers.controller import ProviderController
from ..providers.openai import OpenAIProviderError, OpenAISubscription
from ..security.pairing import PairingAuthority, PairingDenied
from ..storage.lifecycle_repository import LifecycleRepository
from ..storage.profile_settings import UserProfileRepository
from ..storage.sessions import SessionTranscriptRepository
from .events import RuntimeEventStream
from .skill_routes import SkillRoutes
from .mail_routes import MailRoutes
from .calendar_routes import CalendarRoutes
from .task_routes import TaskRoutes
from .mcp_routes import McpRoutes
from .tool_routes import ToolRoutes
from .plugin_routes import PluginRoutes
from .creation_routes import CreationRoutes
from .connection_routes import ConnectionRoutes
from .background_agent_routes import BackgroundAgentRoutes

if TYPE_CHECKING:
    from .http_server import HealthReader, RestartRequest

_LOG = runtime_logger()


class RouteRequest(Protocol):
    """Transport surface the router needs from the HTTP request handler."""

    path: str
    headers: Any

    def respond_json(
        self,
        status: int,
        payload: dict[str, object],
        *,
        headers: dict[str, str] | None = None,
    ) -> None: ...

    def respond_empty(self, status: int, *, headers: dict[str, str] | None = None) -> None: ...
    def respond_bytes(self, status: int, payload: bytes, *, content_type: str) -> None: ...

    def stream_events(self) -> None: ...

    def browser_session(self, authority: PairingAuthority, *, mutation: bool) -> object | None: ...

    def request_json(self, *, max_bytes: int = 4096) -> dict[str, object] | None: ...

    def request_bytes(self, *, max_bytes: int) -> bytes | None: ...

    def provider_error(self, error: OpenAIProviderError) -> None: ...


class RuntimeRoutes:
    """Owns the private runtime API route table.

    One method per HTTP verb; routes keep their exact match order and guards.
    ``http_server`` owns transport (bind, threads, auth, body/response
    mechanics); this class owns which path does what. New endpoints are added
    here, not to the transport handler.
    """

    def __init__(
        self,
        *,
        health: HealthReader,
        lifecycle: LifecycleRepository,
        events: RuntimeEventStream,
        pairing: PairingAuthority | None,
        providers: ProviderController | None,
        text_runner: AgentsSdkTextRunner | None,
        subscription: OpenAISubscription | None,
        mcp: LocalMcpServer | None,
        profile: UserProfileRepository | None,
        sessions: SessionTranscriptRepository | None,
        memory: MemoryService | None,
        restart_request: RestartRequest | None,
        skills: SkillRoutes | None = None,
        mail: MailRoutes | None = None,
        calendar: CalendarRoutes | None = None,
        tasks: TaskRoutes | None = None,
        outbound_mcp: McpRoutes | None = None,
        tools: ToolRoutes | None = None,
        plugins: PluginRoutes | None = None,
        creations: CreationRoutes | None = None,
        connections: ConnectionRoutes | None = None,
        background_agent: BackgroundAgentRoutes | None = None,
    ) -> None:
        self._health = health
        self._lifecycle = lifecycle
        self._events_stream = events
        self._pairing = pairing
        self._providers = providers
        self._text_runner = text_runner
        self._subscription = subscription
        self._mcp = mcp
        self._profile = profile
        self._sessions = sessions
        self._memory = memory
        self._restart_request = restart_request
        self._skills = skills
        self._mail = mail
        self._calendar = calendar
        self._tasks = tasks
        self._outbound_mcp = outbound_mcp
        self._tools = tools
        self._plugins = plugins
        self._creations = creations
        self._connections = connections
        self._background_agent = background_agent

    def handle_get(self, req: RouteRequest) -> None:
        path = req.path.split("?", 1)[0]
        pairing = self._pairing
        providers = self._providers
        subscription = self._subscription
        profile = self._profile
        memory = self._memory
        skills = self._skills
        mail = self._mail
        calendar = self._calendar
        tasks = self._tasks
        outbound_mcp = self._outbound_mcp
        tools = self._tools
        plugins = self._plugins
        creations = self._creations
        connections = self._connections
        background_agent = self._background_agent
        if background_agent is not None and background_agent.handle_get(req, pairing): return
        if skills is not None and skills.handle_get(req, pairing):
            return
        if mail is not None and mail.handle_get(req, pairing):
            return
        if calendar is not None and calendar.handle_get(req, pairing):
            return
        if tasks is not None and tasks.handle_get(req):
            return
        if outbound_mcp is not None and outbound_mcp.handle_get(req, pairing):
            return
        if tools is not None and tools.handle_get(req, pairing):
            return
        if plugins is not None and plugins.handle_get(req, pairing):
            return
        if creations is not None and creations.handle_get(req, pairing): return
        if connections is not None and connections.handle_get(req, pairing): return
        if path == "/v1/health":
            req.respond_json(200, self._health())
            return
        if path == "/v1/lifecycle-records/runtime.start_count":
            try:
                record = self._lifecycle.get("runtime.start_count")
            except KeyError:
                req.respond_json(404, {"error": {"code": "record_not_found", "message": "Lifecycle record not found."}})
                return
            req.respond_json(200, {"key": record.key, "value": record.value, "updatedAt": record.updated_at})
            return
        if path == "/v1/events":
            req.stream_events()
            return
        if path == "/v1/management/pairing" and pairing is not None:
            code = pairing.current_code()
            req.respond_json(200, {"code": code.value, "expiresAt": code.expires_at})
            return
        if path == "/v1/management/status" and pairing is not None:
            session = req.browser_session(pairing, mutation=False)
            if session is None:
                return
            req.respond_json(200, {**self._health(), "csrfToken": session.csrf_token})
            return
        if path == "/v1/management/openai" and pairing is not None and providers is not None:
            if req.browser_session(pairing, mutation=False) is None:
                return
            try:
                req.respond_json(200, providers.status(refresh=False))
            except OpenAIProviderError as error:
                req.provider_error(error)
            return
        if path == "/v1/host/openai" and providers is not None:
            try:
                req.respond_json(200, providers.status(refresh=False))
            except OpenAIProviderError as error:
                req.provider_error(error)
            return
        if path == "/v1/management/openai/subscription" and pairing is not None and subscription is not None:
            if req.browser_session(pairing, mutation=False) is None:
                return
            req.respond_json(200, subscription.status())
            return
        if path == "/v1/management/profile" and pairing is not None and profile is not None:
            if req.browser_session(pairing, mutation=False) is None:
                return
            req.respond_json(200, {"displayName": profile.profile().display_name})
            return
        if path == "/v1/management/memory/sessions" and pairing is not None and memory is not None:
            if req.browser_session(pairing, mutation=False) is None:
                return
            sessions_view = []
            for session_id in memory.list_sessions():
                summary = memory.session_summary(session_id)
                sessions_view.append(_session_view(session_id, summary))
            req.respond_json(200, {"sessions": sessions_view})
            return
        if path.startswith("/v1/management/memory/sessions/") and pairing is not None and memory is not None:
            if req.browser_session(pairing, mutation=False) is None:
                return
            session_id = path.rsplit("/", 1)[-1]
            entries = memory.session_entries(session_id)
            req.respond_json(
                200,
                {
                    "sessionId": session_id,
                    "entries": [_entry_view(entry) for entry in entries],
                    "summary": _summary_view(memory.session_summary(session_id)),
                },
            )
            return
        if path == "/v1/management/memory" and pairing is not None and memory is not None:
            if req.browser_session(pairing, mutation=False) is None:
                return
            req.respond_json(
                200,
                {"memories": [_memory_view(m) for m in memory.list_memories()]},
            )
            return
        if path.startswith("/v1/management/memory/search") and pairing is not None and memory is not None:
            if req.browser_session(pairing, mutation=False) is None:
                return
            query_params = parse_qs(req.path.split("?", 1)[1] if "?" in req.path else "")
            query = (query_params.get("q", [""])[0]).strip()
            if not query:
                req.respond_json(400, {"error": {"code": "invalid_request", "message": "A search query is required."}})
                return
            result = memory.search(query)
            req.respond_json(
                200,
                {"matches": list(result.matches), "embeddingsAvailable": result.embeddings_available},
            )
            return
        req.respond_json(404, {"error": {"code": "not_found", "message": "Not found."}})

    def handle_post(self, req: RouteRequest) -> None:
        path = req.path.split("?", 1)[0]
        pairing = self._pairing
        providers = self._providers
        text_runner = self._text_runner
        subscription = self._subscription
        mcp = self._mcp
        profile = self._profile
        sessions = self._sessions
        memory = self._memory
        skills = self._skills
        mail = self._mail
        calendar = self._calendar
        outbound_mcp = self._outbound_mcp
        plugins = self._plugins
        creations = self._creations
        background_agent = self._background_agent
        if background_agent is not None and background_agent.handle_post(req, pairing): return
        if skills is not None and skills.handle_post(req, pairing):
            return
        if mail is not None and mail.handle_post(req, pairing):
            return
        if calendar is not None and calendar.handle_post(req, pairing):
            return
        if outbound_mcp is not None and outbound_mcp.handle_post(req, pairing):
            return
        if plugins is not None and plugins.handle_post(req, pairing):
            return
        if creations is not None and creations.handle_post(req, pairing): return
        if path == "/v1/mcp" and mcp is not None:
            payload = req.request_json(max_bytes=65_536)
            if payload is None:
                return
            result = mcp.handle(
                payload,
                session_id=req.headers.get("Mcp-Session-Id"),
                protocol_version=req.headers.get("MCP-Protocol-Version"),
                voice_session_id=req.headers.get("X-ReSono-Voice-Session"),
                tool_call_id=req.headers.get("X-ReSono-Tool-Call"),
                user_utterance=_decoded_header(req.headers.get("X-ReSono-Voice-Utterance-B64")),
                user_utterance_id=_positive_integer_header(req.headers.get("X-ReSono-Voice-Utterance-Id")),
            )
            headers = {"Mcp-Session-Id": result.session_id} if result.session_id else None
            if result.payload is None:
                req.respond_empty(result.status, headers=headers)
            else:
                req.respond_json(result.status, result.payload, headers=headers)
            return
        if path == "/v1/voice/calls" and providers is not None:
            payload = req.request_json(max_bytes=300_000)
            if payload is None:
                return
            try:
                call = providers.create_realtime_call(str(payload.get("sdp", "")))
                req.respond_json(
                    200,
                    {
                        "sdp": call.sdp,
                        "connectGreetingEvent": call.connect_greeting_event,
                        "sessionId": call.session_id,
                        "live": call.live,
                        "transport": call.transport,
                        "greetingText": call.greeting_text,
                    },
                )
            except OpenAIProviderError as error:
                req.provider_error(error)
            return
        if path == "/v1/voice/sessions/finalize" and sessions is not None and memory is not None:
            payload = req.request_json(max_bytes=300_000)
            if payload is None:
                return
            session_id = str(payload.get("sessionId", "")).strip()
            raw_entries = payload.get("entries", [])
            if not session_id or not isinstance(raw_entries, list):
                req.respond_json(400, {"error": {"code": "invalid_request", "message": "sessionId and entries are required."}})
                return
            if providers is not None: providers.close_realtime_session(session_id)
            appended = 0
            for item in raw_entries:
                if not isinstance(item, dict):
                    continue
                role = str(item.get("role", "")).strip()
                event_type = str(item.get("eventType", "")).strip()
                text = str(item.get("text", "")).strip()
                if not role or not event_type or not text:
                    continue
                try:
                    sessions.append(
                        session_id=session_id,
                        role=role,
                        event_type=event_type,
                        text_content=text,
                    )
                    appended += 1
                except ValueError:
                    continue
            if appended == 0:
                req.respond_json(409, {"error": {"code": "nothing_to_review", "message": "No transcript entries were captured."}})
                return
            try:
                finalized = memory.finalize(session_id)
            except ValueError as error:
                req.respond_json(409, {"error": {"code": "nothing_to_review", "message": str(error)}})
                return
            except OpenAIProviderError as error:
                req.provider_error(error)
                return
            except Exception:
                _LOG.exception(
                    "voice.session.finalize_failed",
                    extra={"sessionId": session_id},
                )
                req.respond_json(500, {"error": {"code": "finalize_failed", "message": "The session could not be finalized."}})
                return
            _LOG.info(
                "voice.session.finalize",
                extra={
                    "sessionId": session_id,
                    "entryCount": appended,
                    "memoryCount": finalized.memory_count,
                    "embeddedCount": finalized.embedded_count,
                },
            )
            req.respond_json(200, _finalize_view(finalized))
            return
        if path == "/v1/management/text/turns" and text_runner is not None:
            if pairing is None or req.browser_session(pairing, mutation=True) is None:
                return
            payload = req.request_json(max_bytes=20_000)
            if payload is None:
                return
            user_input = str(payload.get("input", ""))
            session_id = None
            if sessions is not None:
                session_id = str(payload.get("sessionId", "")).strip() or sessions.new_session_id()
            try:
                result = text_runner.run(user_input)
            except OpenAIProviderError as error:
                req.provider_error(error)
                return
            if sessions is not None:
                sessions.append(
                    session_id=session_id,
                    role="user",
                    event_type="text.turn.input",
                    text_content=user_input,
                )
                sessions.append(
                    session_id=session_id,
                    role="assistant",
                    event_type="text.turn.output",
                    text_content=result.text,
                )
            req.respond_json(200, {"text": result.text, "model": result.model, "sessionId": session_id})
            return
        if path.startswith("/v1/management/openai/subscription/") and subscription is not None:
            if pairing is None or req.browser_session(pairing, mutation=True) is None:
                return
            payload = req.request_json()
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
                    req.respond_json(404, {"error": {"code": "not_found", "message": "Not found."}})
                    return
                req.respond_json(200, result)
            except OpenAIProviderError as error:
                req.provider_error(error)
            return
        if path == "/v1/management/pair" and pairing is not None:
            payload = req.request_json()
            if payload is None:
                return
            try:
                session = pairing.pair(
                    str(payload.get("code", "")),
                    req.headers.get("X-ReSono-Forwarded-Origin", ""),
                    req.headers.get("Origin"),
                )
            except PairingDenied:
                req.respond_json(403, {"error": {"code": "pairing_denied", "message": "Pairing code is invalid or expired."}})
                return
            cookie = (
                f"resono_session={session.token}; Path=/; Max-Age=1800; "
                "Secure; HttpOnly; SameSite=Strict"
            )
            req.respond_json(
                200,
                {"csrfToken": session.csrf_token, "expiresAt": session.expires_at},
                headers={"Set-Cookie": cookie},
            )
            return
        if path == "/v1/management/restart" and pairing is not None:
            if req.browser_session(pairing, mutation=True) is None:
                return
            if self._restart_request is None:
                req.respond_json(503, {"error": {"code": "restart_unavailable", "message": "Runtime restart is unavailable."}})
                return
            req.respond_json(202, {"status": "restarting"})
            self._restart_request()
            return
        if path == "/v1/management/profile" and pairing is not None and profile is not None:
            if req.browser_session(pairing, mutation=True) is None:
                return
            payload = req.request_json()
            if payload is None:
                return
            try:
                saved = profile.save(_optional_string(payload.get("displayName")))
                req.respond_json(200, {"displayName": saved.display_name})
            except ValueError as error:
                req.respond_json(400, {"error": {"code": "invalid_profile", "message": str(error)}})
            return
        if path.startswith("/v1/management/memory/sessions/") and pairing is not None and memory is not None:
            if req.browser_session(pairing, mutation=True) is None:
                return
            session_id = path.rsplit("/", 1)[-1]
            if path.endswith("/finalize"):
                try:
                    finalized = memory.finalize(session_id)
                    req.respond_json(200, _finalize_view(finalized))
                except ValueError as error:
                    req.respond_json(409, {"error": {"code": "nothing_to_review", "message": str(error)}})
                except OpenAIProviderError as error:
                    req.provider_error(error)
                except Exception:
                    _LOG.exception(
                        "memory.session.finalize_failed",
                        extra={"sessionId": session_id},
                    )
                    req.respond_json(500, {"error": {"code": "finalize_failed", "message": "The session could not be finalized."}})
                return
            req.respond_json(404, {"error": {"code": "not_found", "message": "Not found."}})
            return
        if path == "/v1/management/memory/reindex" and pairing is not None and memory is not None:
            if req.browser_session(pairing, mutation=True) is None:
                return
            count = memory.reindex()
            req.respond_json(200, {"reindexedCount": count})
            return
        if path.startswith("/v1/management/openai/") and pairing is not None and providers is not None:
            if req.browser_session(pairing, mutation=True) is None:
                return
            payload = req.request_json()
            if payload is None:
                return
            try:
                if path == "/v1/management/openai/connect":
                    result = providers.connect_platform(str(payload.get("apiKey", "")))
                elif path == "/v1/management/openai/disconnect":
                    result = providers.disconnect_platform()
                elif path == "/v1/management/openai/provider":
                    result = providers.select_provider(str(payload.get("provider", "")))
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
                    req.respond_json(404, {"error": {"code": "not_found", "message": "Not found."}})
                    return
                req.respond_json(200, result)
            except (ValueError, OpenAIProviderError) as error:
                if isinstance(error, OpenAIProviderError):
                    req.provider_error(error)
                else:
                    req.respond_json(400, {"error": {"code": "invalid_request", "message": str(error)}})
            return
        if path.startswith("/v1/host/openai/") and providers is not None:
            payload = req.request_json()
            if payload is None:
                return
            try:
                if path == "/v1/host/openai/connect":
                    result = providers.connect_platform(str(payload.get("apiKey", "")))
                elif path == "/v1/host/openai/disconnect":
                    result = providers.disconnect_platform()
                elif path == "/v1/host/openai/provider":
                    result = providers.select_provider(str(payload.get("provider", "")))
                elif path == "/v1/host/openai/models":
                    result = providers.select_models(
                        text_model=_optional_string(payload.get("textModel")),
                        realtime_model=_optional_string(payload.get("realtimeModel")),
                        reasoning_effort=_optional_string(payload.get("reasoningEffort")),
                    )
                elif path == "/v1/host/openai/refresh":
                    result = providers.status(refresh=True)
                elif path == "/v1/host/openai/access":
                    result = providers.select_access_path(str(payload.get("accessPath", "")))
                else:
                    req.respond_json(404, {"error": {"code": "not_found", "message": "Not found."}})
                    return
                req.respond_json(200, result)
            except (ValueError, OpenAIProviderError) as error:
                if isinstance(error, OpenAIProviderError):
                    req.provider_error(error)
                else:
                    req.respond_json(400, {"error": {"code": "invalid_request", "message": str(error)}})
            return
        req.respond_json(404, {"error": {"code": "not_found", "message": "Not found."}})

    def handle_delete(self, req: RouteRequest) -> None:
        path = req.path.split("?", 1)[0]
        pairing = self._pairing
        memory = self._memory
        skills = self._skills
        mail = self._mail
        calendar = self._calendar
        outbound_mcp = self._outbound_mcp
        plugins = self._plugins
        creations = self._creations
        background_agent = self._background_agent
        if background_agent is not None and background_agent.handle_delete(req, pairing): return
        if skills is not None and skills.handle_delete(req, pairing):
            return
        if mail is not None and mail.handle_delete(req, pairing):
            return
        if calendar is not None and calendar.handle_delete(req, pairing):
            return
        if outbound_mcp is not None and outbound_mcp.handle_delete(req, pairing):
            return
        if plugins is not None and plugins.handle_delete(req, pairing):
            return
        if creations is not None and creations.handle_delete(req, pairing): return
        if path.startswith("/v1/management/memory/sessions/") and pairing is not None and memory is not None:
            if req.browser_session(pairing, mutation=True) is None:
                return
            session_id = path.rsplit("/", 1)[-1]
            deleted_memories = memory.delete_session(session_id)
            req.respond_json(200, {"sessionId": session_id, "deletedMemoryCount": deleted_memories})
            return
        if path.startswith("/v1/management/memory/") and pairing is not None and memory is not None:
            if req.browser_session(pairing, mutation=True) is None:
                return
            memory_id = path.rsplit("/", 1)[-1]
            if memory.delete_memory(memory_id):
                req.respond_json(200, {"memoryId": memory_id, "deleted": True})
            else:
                req.respond_json(404, {"error": {"code": "not_found", "message": "Memory was not found."}})
            return
        req.respond_json(404, {"error": {"code": "not_found", "message": "Not found."}})


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def _decoded_header(value: str | None) -> str | None:
    if not value:
        return None
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8").strip()
    except (ValueError, UnicodeDecodeError):
        return None
    return decoded[:500] or None


def _positive_integer_header(value: str | None) -> int | None:
    try:
        parsed = int(value or "")
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _finalize_view(finalized: object) -> dict[str, object]:
    return {
        "sessionId": finalized.session_id,
        "summary": finalized.summary,
        "memoryCount": finalized.memory_count,
        "embeddedCount": finalized.embedded_count,
        "model": finalized.model,
        "embeddingsAvailable": finalized.embeddings_available,
    }


def _entry_view(entry: object) -> dict[str, object]:
    return {
        "entryIndex": entry.entry_index,
        "role": entry.role,
        "eventType": entry.event_type,
        "textContent": entry.text_content,
        "createdAt": entry.created_at,
    }


def _summary_view(summary: object | None) -> dict[str, object] | None:
    if summary is None:
        return None
    return {
        "status": summary.summary_status,
        "summarizerModelKey": summary.summarizer_model_key,
        "summaryText": summary.summary_text,
        "extractedMemoryCount": summary.extracted_memory_count,
        "updatedAt": summary.updated_at,
    }


def _session_view(session_id: str, summary: object | None) -> dict[str, object]:
    return {"sessionId": session_id, "summary": _summary_view(summary)}


def _memory_view(memory: object) -> dict[str, object]:
    return {
        "memoryId": memory.memory_id,
        "sessionId": memory.session_id,
        "memoryClass": memory.memory_class,
        "domain": memory.domain,
        "memoryType": memory.memory_type,
        "memoryKey": memory.memory_key,
        "content": memory.content_text,
        "confidence": memory.confidence,
        "sensitivity": memory.sensitivity,
        "createdAt": memory.created_at,
        "updatedAt": memory.updated_at,
        "status": memory.status,
        "currentVersion": memory.current_version,
        "validFrom": memory.valid_from,
        "validTo": memory.valid_to,
    }
