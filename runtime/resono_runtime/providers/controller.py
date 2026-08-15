from __future__ import annotations

from dataclasses import dataclass

from .openai import OpenAIPlatform, OpenAIProviderError, OpenAISubscription, ProviderModels
from ..api.events import RuntimeEventStream
from ..security.credentials import ProviderCredentials
from ..storage.provider_settings import ProviderSettingsRepository
from ..storage.profile_settings import UserProfileRepository


@dataclass(frozen=True, slots=True)
class RealtimeCall:
    sdp: str
    connect_greeting_event: dict[str, object] | None


class ProviderController:
    SUBSCRIPTION_MODELS = ProviderModels(
        ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"),
        ("gpt-realtime-2.1-mini", "gpt-live-1"),
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
    ) -> None:
        self._credentials = credentials
        self._settings = settings
        self._events = events
        self._safety_source = safety_source
        self._subscription = subscription
        self._profile = profile
        self._models = ProviderModels((), ())

    def status(self, *, refresh: bool = False) -> dict[str, object]:
        selection = self._settings.selection()
        platform_connected = self._credentials.has_platform_key()
        subscription_connected = bool(self._subscription and self._subscription.status()["connected"])
        access_path = selection.access_path
        connected = subscription_connected if access_path == "subscription" else platform_connected
        if access_path == "platform" and connected and (refresh or not self._models.realtime):
            self._models = self._platform().list_models()
        models = self.SUBSCRIPTION_MODELS if access_path == "subscription" else self._models
        if connected:
            text_model = _select_default(models.text, selection.text_model)
            realtime_model = _select_default(models.realtime, selection.realtime_model)
            if text_model != selection.text_model or realtime_model != selection.realtime_model:
                selection = self._settings.save(
                    text_model=text_model,
                    realtime_model=realtime_model,
                )
        return {
            "provider": "openai",
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
        text_model = _select_default(models.text, selection.text_model)
        realtime_model = _select_default(
            models.realtime, selection.realtime_model, preferred="gpt-realtime-2.1"
        )
        self._settings.save(text_model=text_model, realtime_model=realtime_model)
        self._settings.save_access_path("platform")
        self._events.publish("provider.connected", {"provider": "openai", "accessPath": "platform"})
        return self.status()

    def disconnect_platform(self) -> dict[str, object]:
        self._credentials.disconnect_platform()
        self._models = ProviderModels((), ())
        selection = self._settings.selection()
        subscription_connected = bool(
            self._subscription and self._subscription.status()["connected"]
        )
        if selection.access_path == "platform":
            if subscription_connected:
                self._settings.save_access_path("subscription")
                self._settings.save(
                    text_model=_select_default(self.SUBSCRIPTION_MODELS.text, None),
                    realtime_model=_select_default(self.SUBSCRIPTION_MODELS.realtime, None),
                )
            else:
                self._settings.clear()
        self._events.publish("provider.disconnected", {"provider": "openai", "accessPath": "platform"})
        return self.status()

    def disconnect_subscription(self) -> dict[str, object]:
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
                    text_model=_select_default(self._models.text, None),
                    realtime_model=_select_default(
                        self._models.realtime, None, preferred="gpt-realtime-2.1"
                    ),
                )
            else:
                self._settings.clear()
        self._events.publish(
            "provider.disconnected", {"provider": "openai", "accessPath": "subscription"}
        )
        return result

    def select_models(
        self,
        *,
        text_model: str | None,
        realtime_model: str | None,
        reasoning_effort: str | None = None,
    ) -> dict[str, object]:
        selection = self._settings.selection()
        if selection.access_path == "subscription":
            if self._subscription is None or not self._subscription.status()["connected"]:
                raise OpenAIProviderError("credential_unavailable", "Connect ChatGPT first.", status=409)
            models = self.SUBSCRIPTION_MODELS
        elif not self._credentials.has_platform_key():
            raise OpenAIProviderError("credential_unavailable", "Connect OpenAI first.", status=409)
        else:
            if not self._models.realtime:
                self._models = self._platform().list_models()
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

    def select_access_path(self, access_path: str) -> dict[str, object]:
        if access_path == "platform":
            if not self._credentials.has_platform_key():
                raise OpenAIProviderError("credential_unavailable", "Connect OpenAI first.", status=409)
            if not self._models.realtime:
                self._models = self._platform().list_models()
            models = self._models
        elif access_path == "subscription":
            if self._subscription is None or not self._subscription.status()["connected"]:
                raise OpenAIProviderError("credential_unavailable", "Connect ChatGPT first.", status=409)
            models = self.SUBSCRIPTION_MODELS
        else:
            raise OpenAIProviderError("invalid_access_path", "OpenAI access path is invalid.", status=400)
        self._settings.save_access_path(access_path)
        self._settings.save(
            text_model=_select_default(models.text, None),
            realtime_model=_select_default(models.realtime, None),
        )
        self._events.publish("provider.access_selected", {"provider": "openai", "accessPath": access_path})
        return self.status()

    def create_realtime_call(self, offer_sdp: str) -> RealtimeCall:
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
        self._events.publish(
            "voice.connecting",
            {"provider": "openai", "model": selection.realtime_model},
        )
        answer = OpenAIPlatform(access_token, safety_source=self._safety_source).create_realtime_call(
            offer_sdp=offer_sdp, model=selection.realtime_model
        )
        self._events.publish(
            "voice.session_created",
            {"provider": "openai", "model": selection.realtime_model},
        )
        greeting = self._profile.connect_greeting_event() if self._profile else None
        return RealtimeCall(answer, greeting)

    def _platform(self) -> OpenAIPlatform:
        return OpenAIPlatform(
            self._credentials.platform_key(), safety_source=self._safety_source
        )


def _select_default(
    available: tuple[str, ...], current: str | None, *, preferred: str | None = None
) -> str | None:
    if current in available:
        return current
    if preferred in available:
        return preferred
    return available[0] if available else None
