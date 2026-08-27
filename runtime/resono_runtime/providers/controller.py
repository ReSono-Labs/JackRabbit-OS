from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import TYPE_CHECKING
import threading
from resono_runtime.core.logging import runtime_logger

from .openai import OpenAIPlatform, OpenAIProviderError, OpenAISubscription, ProviderModels
from .compatible import CompatibleProvider, CompatibleProviderError
from ..realtime.modes import PRIMARY_VOICE_INSTRUCTION
from ..api.events import RuntimeEventStream
from ..security.credentials import ConnectionCredentialEnvelopes, ProviderCredentials
from ..storage.provider_catalog import ProviderCatalogRepository
from ..storage.provider_keys import ProviderKeyRepository
from ..storage.provider_settings import ProviderSettingsRepository
from ..storage.profile_settings import UserProfileRepository
from ..storage.sessions import SessionTranscriptRepository

if TYPE_CHECKING:
    from ..memory.session_context import SessionContextBuilder
    from ..realtime.modes import VoiceModeService


@dataclass(frozen=True, slots=True)
class RealtimeCall:
    sdp: str
    connect_greeting_event: dict[str, object] | None
    session_id: str


class ProviderController:
    _FALLBACK_OPENAI_SUBSCRIPTION = ProviderModels(
        ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"),
        ("gpt-realtime-2.1", "gpt-realtime-2.1-mini", "gpt-live-1"),
    )

    def __init__(
        self,
        *,
        credentials: ProviderCredentials,
        settings: ProviderSettingsRepository,
        events: RuntimeEventStream,
        safety_source: str,
        subscription: OpenAISubscription | None = None,
        profile: UserProfileRepository | None = None,
        catalog: ProviderCatalogRepository | None = None,
        provider_keys: ProviderKeyRepository | None = None,
        credential_envelopes: ConnectionCredentialEnvelopes | None = None,
        sessions: SessionTranscriptRepository | None = None,
        session_context: "SessionContextBuilder | None" = None,
        memory_lookup_tool_def: dict[str, object] | None = None,
        voice_tools: Callable[[], tuple[dict[str, object], ...]] | None = None,
        goal_intake_tools: Callable[[], tuple[dict[str, object], ...]] | None = None,
        voice_skill_instructions: Callable[[], str] | None = None,
        voice_modes: "VoiceModeService | None" = None,
    ) -> None:
        self._credentials = credentials
        self._settings = settings
        self._events = events
        self._safety_source = safety_source
        self._subscription = subscription
        self._profile = profile
        self._catalog = catalog
        self._provider_keys = provider_keys
        self._credential_envelopes = credential_envelopes
        self._sessions = sessions
        self._session_context = session_context
        self._memory_lookup_tool_def = memory_lookup_tool_def
        self._voice_tools = voice_tools
        self._goal_intake_tools = goal_intake_tools
        self._voice_skill_instructions = voice_skill_instructions
        self._voice_modes = voice_modes
        self._models = ProviderModels((), ())
        self._log = runtime_logger()
        self._active_sessions: set[str] = set()
        self._active_sessions_lock = threading.Lock()

    def status(self, *, refresh: bool = False) -> dict[str, object]:
        selection = self._settings.selection()
        provider = _normalize_provider(selection.provider)
        providers = self._provider_list()
        provider_ids = tuple(item["id"] for item in providers)
        if provider not in provider_ids:
            provider = "openai"
            self._settings.set_provider(provider)
            selection = self._settings.selection()

        if provider != "openai":
            connected = self._provider_key(provider) is not None
            models = self._available_models(
                provider=provider,
                access_path="key",
                refresh=refresh,
                connected=connected,
            )
            text_model = _select_default(models.text, selection.text_model) if connected else None
            realtime_model = _select_default(models.realtime, selection.realtime_model) if connected else None
            return {
                "provider": provider,
                "providers": providers,
                "accessPath": "key",
                "connected": connected,
                "connections": {"key": connected},
                "models": {
                    "text": list(models.text) if connected else [],
                    "realtime": list(models.realtime) if connected else [],
                },
                "selection": {
                    "text": text_model,
                    "realtime": realtime_model,
                    "reasoning": selection.reasoning_effort,
                },
            }

        platform_connected = self._credentials.has_platform_key()
        subscription_connected = bool(self._subscription and self._subscription.status()["connected"])
        access_path = selection.access_path
        if subscription_connected and access_path != "subscription":
            self._settings.save_access_path("subscription")
            selection = self._settings.selection()
            access_path = "subscription"
        connected = subscription_connected if access_path == "subscription" else platform_connected

        models = self._available_models(
            provider=provider,
            access_path=access_path,
            refresh=refresh,
            connected=connected,
        )

        if connected:
            text_model = _select_default(models.text, selection.text_model)
            realtime_model = _select_default(models.realtime, selection.realtime_model)
            if text_model != selection.text_model or realtime_model != selection.realtime_model:
                selection = self._settings.save(
                    text_model=text_model,
                    realtime_model=realtime_model,
                )

        return {
            "provider": provider,
            "providers": providers,
            "accessPath": access_path,
            "connected": connected,
            "connections": {
                "platform": platform_connected,
                "subscription": subscription_connected,
            },
            "models": {
                "text": list(models.text) if connected else [],
                "realtime": list(models.realtime) if connected else [],
            },
            "selection": {
                "text": selection.text_model,
                "realtime": selection.realtime_model,
                "reasoning": selection.reasoning_effort,
            },
        }

    def connect_platform(self, key: str) -> dict[str, object]:
        self._assert_active_provider()
        if self._subscription is not None and self._subscription.status()["connected"]:
            raise OpenAIProviderError(
                "access_path_conflict",
                "Disconnect ChatGPT before connecting an OpenAI Platform API key.",
                status=409,
            )
        candidate = OpenAIPlatform(key.strip(), safety_source=self._safety_source)
        models = candidate.list_models()
        if not models.realtime:
            raise OpenAIProviderError(
                "realtime_unavailable",
                "This OpenAI project does not expose a Realtime model.",
                status=400,
            )
        self._credentials.connect_platform(key.strip())
        self._models = models
        selection = self._settings.selection()
        text_model = _select_default(
            models.text,
            selection.text_model,
            preferred="gpt-5.6-sol",
        )
        realtime_model = _select_default(models.realtime, selection.realtime_model, preferred="gpt-realtime-2.1")
        self._settings.save(text_model=text_model, realtime_model=realtime_model)
        self._settings.save_access_path("platform")
        self._events.publish("provider.connected", {"provider": "openai", "accessPath": "platform"})
        return self.status()

    def disconnect_platform(self) -> dict[str, object]:
        self._assert_active_provider()
        self._credentials.disconnect_platform()
        self._models = ProviderModels((), ())
        selection = self._settings.selection()
        subscription_connected = bool(self._subscription and self._subscription.status()["connected"])
        if selection.access_path == "platform":
            if subscription_connected:
                self._settings.save_access_path("subscription")
                fallback = self._catalog_models("subscription", selection.provider)
                self._settings.save(
                    text_model=_select_default(fallback.text, None),
                    realtime_model=_select_default(fallback.realtime, None),
                )
            else:
                self._settings.clear()
        self._events.publish("provider.disconnected", {"provider": "openai", "accessPath": "platform"})
        return self.status()

    def disconnect_subscription(self) -> dict[str, object]:
        self._assert_active_provider()
        if self._subscription is None:
            raise OpenAIProviderError("credential_unavailable", "ChatGPT is not connected.", status=409)
        selection = self._settings.selection()
        result = self._subscription.disconnect()
        if selection.access_path == "subscription":
            if self._credentials.has_platform_key():
                if not self._models.realtime:
                    self._models = self._platform().list_models()
                self._settings.save_access_path("platform")
                self._settings.save(
                    text_model=_select_default(
                        self._models.text,
                        None,
                        preferred="gpt-5.6-sol",
                    ),
                    realtime_model=_select_default(self._models.realtime, None, preferred="gpt-realtime-2.1"),
                )
            else:
                self._settings.clear()
        self._events.publish(
            "provider.disconnected", {"provider": "openai", "accessPath": "subscription"}
        )
        return result

    def connect_provider(self, provider: str, key: str) -> dict[str, object]:
        provider_id = _normalize_provider(provider)
        if provider_id == "openai":
            raise OpenAIProviderError(
                "invalid_provider", "OpenAI uses the platform connection.", status=400
            )
        self._assert_active_provider(provider_id)
        descriptor = self._descriptor(provider_id)
        candidate = CompatibleProvider(
            descriptor.base_url,
            key.strip(),
            api_style=descriptor.api_style,
            auth_header=descriptor.auth_header,
        )
        try:
            models = candidate.list_models()
        except CompatibleProviderError as error:
            raise OpenAIProviderError(error.code, str(error), status=error.status) from error
        self._provider_keys.put(
            provider_id,
            self._credential_envelopes.seal_provider_key(provider_id, key.strip()),
        )
        selection = self._settings.selection()
        catalog_models = self._catalog_models("key", provider_id)
        voice_capability = getattr(descriptor, "voice", "none")
        if voice_capability == "websocket":
            # Voice-only provider (Gemini Live): no text models today.
            self._models = ProviderModels((), catalog_models.realtime)
            self._settings.save(
                text_model=None,
                realtime_model=_select_default(catalog_models.realtime, selection.realtime_model),
            )
        else:
            self._models = ProviderModels(tuple(models), ())
            text_model = _select_default(
                tuple(models),
                selection.text_model,
                preferred=catalog_models.text[0] if catalog_models.text else None,
            )
            realtime_model = _select_default(catalog_models.realtime, selection.realtime_model)
            self._settings.save(text_model=text_model, realtime_model=realtime_model)
        self._settings.save_access_path("key")
        self._events.publish("provider.connected", {"provider": provider_id, "accessPath": "key"})
        self._log.info("provider.key_connected", extra={"provider": provider_id, "models": len(models)})
        return self.status()

    def disconnect_provider(self, provider: str) -> dict[str, object]:
        provider_id = _normalize_provider(provider)
        if provider_id == "openai":
            raise OpenAIProviderError(
                "invalid_provider", "OpenAI uses the platform connection.", status=400
            )
        self._assert_active_provider(provider_id)
        self._provider_keys.delete(provider_id)
        self._models = ProviderModels((), ())
        self._settings.clear()
        subscription_connected = bool(self._subscription and self._subscription.status()["connected"])
        if subscription_connected:
            self._settings.save_access_path("subscription")
            fallback = self._catalog_models("subscription", "openai")
            self._settings.save(
                text_model=_select_default(fallback.text, None),
                realtime_model=_select_default(fallback.realtime, None),
            )
        else:
            self._settings.set_provider("openai")
            self._settings.save_access_path("platform")
        self._events.publish("provider.disconnected", {"provider": provider_id})
        return self.status()

    def select_models(
        self,
        *,
        text_model: str | None,
        realtime_model: str | None,
        reasoning_effort: str | None = None,
    ) -> dict[str, object]:
        self._assert_active_provider()
        selection = self._settings.selection()
        provider = _normalize_provider(selection.provider)
        if provider != "openai":
            if self._provider_key(provider) is None:
                raise OpenAIProviderError(
                    "credential_unavailable", f"Connect {provider} first.", status=409
                )
            descriptor = self._descriptor(provider)
            models = self._catalog_models("key", provider)
            if self._models.text and getattr(descriptor, "voice", "none") != "websocket":
                models = self._models
            supports_realtime = getattr(descriptor, "voice", "none") == "websocket"
            if realtime_model is not None:
                if not supports_realtime:
                    raise OpenAIProviderError(
                        "realtime_unavailable",
                        "Realtime models are only available on voice providers.",
                        status=400,
                    )
                if realtime_model not in models.realtime:
                    raise OpenAIProviderError("unsupported_model", "Select an available realtime model.", status=400)
            if text_model is not None and text_model not in models.text:
                raise OpenAIProviderError("unsupported_model", "Select an available text model.", status=400)
            self._settings.save(
                text_model=text_model if text_model is not None or supports_realtime else text_model,
                realtime_model=realtime_model if supports_realtime else None,
                reasoning_effort=reasoning_effort,
            )
            self._events.publish("provider.models_selected", {"provider": provider})
            return self.status()
        if selection.access_path == "subscription":
            if self._subscription is None or not self._subscription.status()["connected"]:
                raise OpenAIProviderError("credential_unavailable", "Connect ChatGPT first.", status=409)
            models = self._catalog_models("subscription", selection.provider)
        elif not self._credentials.has_platform_key():
            raise OpenAIProviderError("credential_unavailable", "Connect OpenAI first.", status=409)
        else:
            if not self._models.realtime:
                self._models = self._platform().list_models()
            if not self._models.realtime and not self._models.text:
                # If model listing fails, use catalog defaults as a safety net.
                models = self._catalog_models("platform", selection.provider)
            else:
                models = self._models

        if text_model is not None and text_model not in models.text:
            raise OpenAIProviderError("unsupported_model", "Select an available text model.", status=400)
        if realtime_model is not None and realtime_model not in models.realtime:
            raise OpenAIProviderError("unsupported_model", "Select an available Realtime model.", status=400)
        self._settings.save(
            text_model=text_model,
            realtime_model=realtime_model,
            reasoning_effort=reasoning_effort,
        )
        self._events.publish("provider.models_selected", {"provider": "openai"})
        return self.status()

    def select_provider(self, provider: str) -> dict[str, object]:
        provider_id = _normalize_provider(provider)
        if provider_id not in self._provider_ids():
            raise OpenAIProviderError("unsupported_provider", "Select a supported provider.", status=400)
        selection = self._settings.selection()
        if provider_id == _normalize_provider(selection.provider):
            return self.status()

        self._settings.set_provider(provider_id)
        self._settings.save(
            text_model=None,
            realtime_model=None,
            provider=provider_id,
        )
        self._models = ProviderModels((), ())

        if provider_id == "openai":
            prefer_access = "subscription" if self._subscription and self._subscription.status()["connected"] else "platform"
        else:
            prefer_access = "key"
        self._settings.save_access_path(prefer_access)

        self._events.publish(
            "provider.selected",
            {
                "from": selection.provider,
                "to": provider_id,
                "accessPath": self._settings.selection().access_path,
            },
        )
        return self.status()

    def select_access_path(self, access_path: str) -> dict[str, object]:
        self._assert_active_provider()
        if _normalize_provider(self._settings.selection().provider) != "openai":
            raise OpenAIProviderError(
                "invalid_access_path",
                "API-key providers use the key access path.",
                status=400,
            )
        if access_path == "platform":
            if self._subscription is not None and self._subscription.status()["connected"]:
                raise OpenAIProviderError(
                    "access_path_conflict",
                    "Disconnect ChatGPT before using the OpenAI Platform API.",
                    status=409,
                )
            if not self._credentials.has_platform_key():
                raise OpenAIProviderError("credential_unavailable", "Connect OpenAI first.", status=409)
            if not self._models.realtime:
                self._models = self._platform().list_models()
            if not self._models.realtime and not self._models.text:
                models = self._catalog_models("platform", self._settings.selection().provider)
            else:
                models = self._models
        elif access_path == "subscription":
            if self._subscription is None or not self._subscription.status()["connected"]:
                raise OpenAIProviderError("credential_unavailable", "Connect ChatGPT first.", status=409)
            models = self._catalog_models("subscription", self._settings.selection().provider)
        else:
            raise OpenAIProviderError("invalid_access_path", "OpenAI access path is invalid.", status=400)

        self._settings.save_access_path(access_path)
        self._settings.save(
            text_model=_select_default(
                models.text,
                None,
                preferred="gpt-5.6-sol" if access_path == "platform" else None,
            ),
            realtime_model=_select_default(models.realtime, None),
        )
        self._events.publish("provider.access_selected", {"provider": "openai", "accessPath": access_path})
        return self.status()

    def _voice_session_prep(
        self,
    ) -> tuple[str, str, tuple[dict[str, object], ...] | None, tuple[dict[str, object], ...]]:
        """Mint the voice session id and assemble memory/tool context shared by every transport."""
        # The voice session id is minted server-side before the call so the
        # session-start memory context can exclude this session when selecting
        # the previous session summary, and so the client can post the captured
        # transcript back against the same id at session close.
        session_id = self._sessions.new_session_id() if self._sessions is not None else ""
        instructions_extra = ""
        if self._session_context is not None:
            context = self._session_context.build(current_session_id=session_id)
            instructions_extra = context.render()
            self._log.info(
                "voice.session_context",
                extra={
                    "memoryCount": len(context.memories),
                    "hasPreviousSummary": context.previous_summary is not None,
                    "instructionsExtraLen": len(instructions_extra),
                },
            )
        if self._voice_skill_instructions is not None:
            skill_instructions = self._voice_skill_instructions()
            if skill_instructions:
                instructions_extra = "\n\n".join(
                    value for value in (instructions_extra, skill_instructions) if value
                )
        tool_definitions: tuple[dict[str, object], ...] | None = None
        extra_tools: tuple[dict[str, object], ...] = ()
        if self._voice_tools is not None:
            tool_definitions = self._voice_tools()
        elif self._memory_lookup_tool_def is not None:
            extra_tools = (self._memory_lookup_tool_def,)
        return session_id, instructions_extra, tool_definitions, extra_tools

    def create_voice_session(self) -> dict[str, object]:
        """Start a WebSocket voice session for the active provider (Gemini Live today)."""
        self._assert_active_provider()
        provider = _normalize_provider(self._settings.selection().provider)
        descriptor = self._descriptor(provider)
        if descriptor.voice != "websocket":
            raise OpenAIProviderError(
                "realtime_unavailable",
                "This provider does not support WebSocket voice sessions.",
                status=409,
            )
        selection = self._settings.selection()
        key = self._provider_key_value(provider)
        if not key:
            raise OpenAIProviderError("credential_unavailable", f"Connect {provider} first.", status=409)
        if not selection.realtime_model:
            raise OpenAIProviderError("model_required", "Choose a realtime model first.", status=409)
        session_id, instructions_extra, tool_definitions, extra_tools = self._voice_session_prep()
        full_instructions = "\n\n".join(
            value for value in (PRIMARY_VOICE_INSTRUCTION, instructions_extra) if value
        )
        try:
            from ..providers.gemini.live import AUDIO_IN_MIME, AUDIO_OUT_MIME, build_setup, session_url

            if self._voice_modes is not None:
                self._voice_modes.open_session(
                    session_id,
                    primary_instructions=full_instructions,
                    primary_tools=(
                        self._voice_tools
                        if self._voice_tools is not None
                        else lambda: extra_tools
                    ),
                    goal_intake_tools=(
                        self._goal_intake_tools
                        if self._goal_intake_tools is not None
                        else lambda: ()
                    ),
                )
            setup = build_setup(
                model=selection.realtime_model,
                instructions=full_instructions,
                tool_definitions=tool_definitions if tool_definitions is not None else (),
            )
            url = session_url(key)
        except Exception:
            if self._voice_modes is not None:
                self._voice_modes.close_session(session_id)
            raise
        self._events.publish(
            "voice.connecting",
            {"provider": provider, "model": selection.realtime_model},
        )
        self._events.publish(
            "voice.session_created",
            {"provider": provider, "model": selection.realtime_model, "sessionId": session_id},
        )
        with self._active_sessions_lock:
            self._active_sessions.add(session_id)
        greeting = self._profile.connect_greeting_event() if self._profile else None
        self._log.info(
            "provider.voice_session_created",
            extra={"provider": provider, "transport": "websocket", "model": selection.realtime_model},
        )
        return {
            "transport": "websocket",
            "provider": provider,
            "model": selection.realtime_model,
            "url": url,
            "setup": setup,
            "audio": {"input": {"mimeType": AUDIO_IN_MIME}, "output": {"mimeType": AUDIO_OUT_MIME}},
            "sessionId": session_id,
            "connectGreetingEvent": greeting,
        }

    def create_realtime_call(self, offer_sdp: str) -> RealtimeCall:
        self._assert_active_provider()
        if _normalize_provider(self._settings.selection().provider) != "openai":
            raise OpenAIProviderError(
                "realtime_unavailable",
                "Voice calls are only available with OpenAI in this build.",
                status=409,
            )
        selection = self._settings.selection()
        if selection.access_path == "subscription":
            if self._subscription is None:
                raise OpenAIProviderError("credential_unavailable", "Connect ChatGPT first.", status=409)
            access_token = self._subscription.access_token()
        else:
            if not self._credentials.has_platform_key():
                raise OpenAIProviderError("credential_unavailable", "Connect OpenAI first.", status=409)
            access_token = self._credentials.platform_key()
        if not selection.realtime_model:
            raise OpenAIProviderError("model_required", "Choose a Realtime model first.", status=409)
        session_id, instructions_extra, tool_definitions, extra_tools = self._voice_session_prep()
        self._events.publish(
            "voice.connecting",
            {"provider": "openai", "model": selection.realtime_model},
        )
        self._log.info(
            "provider.realtime.begin",
            extra={
                "provider": "openai",
                "accessPath": selection.access_path,
                "model": selection.realtime_model,
                "sdpLen": len(offer_sdp),
            },
        )
        try:
            if self._voice_modes is not None:
                self._voice_modes.open_session(
                    session_id,
                    primary_instructions="\n\n".join(
                        value for value in (
                            PRIMARY_VOICE_INSTRUCTION,
                            instructions_extra,
                        ) if value
                    ),
                    primary_tools=(
                        self._voice_tools
                        if self._voice_tools is not None
                        else lambda: extra_tools
                    ),
                    goal_intake_tools=(
                        self._goal_intake_tools
                        if self._goal_intake_tools is not None
                        else lambda: ()
                    ),
                )
            answer = OpenAIPlatform(access_token, safety_source=self._safety_source).create_realtime_call(
                offer_sdp=offer_sdp,
                model=selection.realtime_model,
                instructions_extra=instructions_extra,
                extra_tools=extra_tools,
                tool_definitions=tool_definitions,
            )
            self._log.info("provider.realtime.success", extra={"provider": "openai", "model": selection.realtime_model})
        except OpenAIProviderError as error:
            if self._voice_modes is not None:
                self._voice_modes.close_session(session_id)
            self._log.warning(
                "provider.realtime.failed provider=%s model=%s code=%s status=%s details=%s",
                "openai",
                selection.realtime_model,
                error.code,
                error.status,
                error.details or {},
            )
            self._events.publish(
                "voice.connect_failed",
                {
                    "provider": "openai",
                    "model": selection.realtime_model,
                    "code": error.code,
                    "message": str(error),
                    "details": error.details or {},
                },
            )
            raise
        self._events.publish(
            "voice.session_created",
            {"provider": "openai", "model": selection.realtime_model, "sessionId": session_id},
        )
        with self._active_sessions_lock:
            self._active_sessions.add(session_id)
        greeting = self._profile.connect_greeting_event() if self._profile else None
        return RealtimeCall(answer, greeting, session_id)

    def is_active_realtime_session(self, session_id: str) -> bool:
        with self._active_sessions_lock: return bool(session_id) and session_id in self._active_sessions

    def close_realtime_session(self, session_id: str) -> None:
        with self._active_sessions_lock: self._active_sessions.discard(session_id)
        if self._voice_modes is not None:
            self._voice_modes.close_session(session_id)

    def _platform(self) -> OpenAIPlatform:
        return OpenAIPlatform(self._credentials.platform_key(), safety_source=self._safety_source)

    def _provider_list(self) -> list[dict[str, str]]:
        providers = []
        if self._catalog is None:
            return [{"id": "openai", "name": "OpenAI"}]
        for item in self._catalog.providers():
            providers.append({"id": item.provider_id, "name": item.name})
        if providers:
            return providers
        return [{"id": "openai", "name": "OpenAI"}]

    def _provider_ids(self) -> tuple[str, ...]:
        return tuple(item["id"] for item in self._provider_list())

    def _assert_active_provider(self, provider_id: str | None = None) -> None:
        provider = _normalize_provider(self._settings.selection().provider)
        if provider not in self._provider_ids():
            raise OpenAIProviderError("provider_unavailable", "Provider is not active.", status=400)
        if provider_id is not None and provider != _normalize_provider(provider_id):
            raise OpenAIProviderError(
                "provider_unavailable",
                f"Select {provider_id} before connecting it.",
                status=400,
            )

    def _descriptor(self, provider_id: str) -> object:
        descriptor = self._catalog.descriptor(provider_id) if self._catalog is not None else None
        if descriptor is None or not descriptor.base_url:
            raise OpenAIProviderError(
                "provider_unavailable", "Provider is not configured.", status=400
            )
        return descriptor

    def _provider_key(self, provider_id: str) -> str | None:
        if self._provider_keys is None:
            return None
        return self._provider_keys.get(provider_id)

    def _provider_key_value(self, provider_id: str) -> str | None:
        envelope = self._provider_key(provider_id)
        if envelope is None or self._credential_envelopes is None:
            return None
        return self._credential_envelopes.open_provider_key(provider_id, envelope)

    def _catalog_models(self, access_path: str, provider: str) -> ProviderModels:
        provider_id = _normalize_provider(provider)
        if self._catalog is None:
            if access_path == "subscription" and provider_id == "openai":
                return self._FALLBACK_OPENAI_SUBSCRIPTION
            return ProviderModels((), ())
        text = self._catalog.models(provider_id, access_path, "text")
        realtime = self._catalog.models(provider_id, access_path, "realtime")
        if access_path == "subscription" and provider_id == "openai":
            if not text:
                text = self._FALLBACK_OPENAI_SUBSCRIPTION.text
            if not realtime:
                realtime = self._FALLBACK_OPENAI_SUBSCRIPTION.realtime
        return ProviderModels(text, realtime)

    def _available_models(
        self,
        *,
        provider: str,
        access_path: str,
        refresh: bool,
        connected: bool,
    ) -> ProviderModels:
        if access_path == "platform":
            if connected and (refresh or not self._models.realtime):
                self._models = self._platform().list_models()
            if not connected:
                return ProviderModels((), ())
            if self._models.text and self._models.realtime:
                return self._models
            return self._catalog_models("platform", provider)
        if access_path == "subscription":
            return self._catalog_models("subscription", provider) if connected else ProviderModels((), ())
        if access_path == "key":
            descriptor = self._descriptor(provider) if connected else None
            if connected and (refresh or not self._models.text):
                try:
                    live = CompatibleProvider(
                        descriptor.base_url,
                        self._provider_key_value(provider),
                        api_style=descriptor.api_style,
                        auth_header=descriptor.auth_header,
                    ).list_models()
                except CompatibleProviderError:
                    live = ()
                self._models = ProviderModels(tuple(live), ())
            if not connected:
                return ProviderModels((), ())
            if getattr(descriptor, "voice", "none") == "websocket":
                # Voice-only provider: catalog realtime models; no text models.
                return ProviderModels((), self._catalog_models("key", provider).realtime)
            if self._models.text:
                return self._models
            return self._catalog_models("key", provider)
        return ProviderModels((), ())


def _select_default(available: tuple[str, ...], current: str | None, *, preferred: str | None = None) -> str | None:
    if current in available:
        return current
    if preferred in available:
        return preferred
    return available[0] if available else None


def _normalize_provider(value: str) -> str:
    return value.strip().lower()
