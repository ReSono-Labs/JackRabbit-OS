"""Slice 3 — provider voice capability: Gemini WebSocket voice sessions (TDD)."""

from __future__ import annotations

import pytest

from resono_runtime.api.events import RuntimeEventStream
from resono_runtime.providers.compatible import CompatibleProviderError  # noqa: F401
from resono_runtime.providers.controller import ProviderController
from resono_runtime.providers.openai import OpenAIProviderError
from resono_runtime.security.credentials import ConnectionCredentialEnvelopes, ProviderCredentials
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.provider_catalog import ProviderCatalogRepository
from resono_runtime.storage.provider_keys import ProviderKeyRepository
from resono_runtime.storage.provider_settings import ProviderSettingsRepository
from resono_runtime.storage.sessions import SessionTranscriptRepository

from .conftest import FakeCredentialBridge
from .fake_compatible_server import FakeCompatibleServer, VALID_KEY


@pytest.fixture
def server():
    instance = FakeCompatibleServer(auth_header="x-goog-api-key")
    instance.start()
    yield instance
    instance.stop()


@pytest.fixture
def controller(tmp_path, server):
    database = RuntimeDatabase(tmp_path / "slice3-controller.db")
    database.migrate()
    bridge = FakeCredentialBridge()
    settings = ProviderSettingsRepository(database)
    instance = ProviderController(
        credentials=ProviderCredentials(bridge),
        settings=settings,
        events=RuntimeEventStream(),
        safety_source="test",
        catalog=ProviderCatalogRepository(database),
        provider_keys=ProviderKeyRepository(database),
        credential_envelopes=ConnectionCredentialEnvelopes(bridge),
        sessions=SessionTranscriptRepository(database),
    )
    with database.connect() as connection:
        connection.execute(
            "UPDATE provider_directory SET base_url = ? WHERE provider_id = 'gemini'",
            (server.base_url,),
        )
        connection.commit()
    return instance, settings


def test_connect_gemini_uses_x_goog_api_key_and_sets_realtime_default(controller):
    instance, settings = controller
    instance.select_provider("gemini")
    status = instance.connect_provider("gemini", VALID_KEY)
    assert status["connected"] is True
    assert status["accessPath"] == "key"
    assert status["models"]["text"] == []  # voice-only provider
    assert "gemini-3.1-flash-live-preview" in status["models"]["realtime"]
    assert status["selection"]["realtime"] == "gemini-3.1-flash-live-preview"


def test_create_voice_session_returns_websocket_descriptor(controller):
    instance, _ = controller
    instance.select_provider("gemini")
    instance.connect_provider("gemini", VALID_KEY)
    session = instance.create_voice_session()
    assert session["transport"] == "websocket"
    assert session["provider"] == "gemini"
    assert session["model"] == "gemini-3.1-flash-live-preview"
    assert session["url"].startswith("wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent")
    assert "key=" in session["url"]
    assert session["setup"]["setup"]["model"] == "models/gemini-3.1-flash-live-preview"
    assert session["audio"]["input"]["mimeType"] == "audio/pcm;rate=16000"
    assert session["audio"]["output"]["mimeType"] == "audio/pcm;rate=24000"
    assert session["sessionId"]
    # active session tracking mirrors the WebRTC path
    assert instance.is_active_realtime_session(session["sessionId"]) is True


def test_webrtc_realtime_call_rejected_on_websocket_provider(controller):
    instance, _ = controller
    instance.select_provider("gemini")
    instance.connect_provider("gemini", VALID_KEY)
    with pytest.raises(OpenAIProviderError) as captured:
        instance.create_realtime_call("v=0 fake-sdp")
    assert captured.value.code == "realtime_unavailable"


def test_select_models_voice_provider_rules(controller):
    instance, _ = controller
    instance.select_provider("gemini")
    instance.connect_provider("gemini", VALID_KEY)
    result = instance.select_models(
        text_model=None,
        realtime_model="gemini-2.5-flash-native-audio-preview-12-2025",
    )
    assert result["selection"]["realtime"] == "gemini-2.5-flash-native-audio-preview-12-2025"
    with pytest.raises(OpenAIProviderError) as captured:
        instance.select_models(text_model="glm-5.2", realtime_model=None)
    assert captured.value.code == "unsupported_model"


def test_voice_session_requires_connection(controller):
    instance, _ = controller
    instance.select_provider("gemini")
    with pytest.raises(OpenAIProviderError) as captured:
        instance.create_voice_session()
    assert captured.value.code == "credential_unavailable"
