"""Slice 2 — ProviderController third-party connect/disconnect/status (TDD)."""

from __future__ import annotations

import pytest

from resono_runtime.api.events import RuntimeEventStream
from resono_runtime.agents.runner import AgentsSdkTextRunner
from resono_runtime.providers.compatible import CompatibleProviderError
from resono_runtime.providers.controller import ProviderController
from resono_runtime.providers.openai import OpenAIProviderError
from resono_runtime.security.credentials import ConnectionCredentialEnvelopes, ProviderCredentials
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.provider_catalog import ProviderCatalogRepository
from resono_runtime.storage.provider_keys import ProviderKeyRepository
from resono_runtime.storage.provider_settings import ProviderSettingsRepository

from .conftest import FakeCredentialBridge
from .fake_compatible_server import FakeCompatibleServer


@pytest.fixture
def server():
    instance = FakeCompatibleServer()
    instance.start()
    yield instance
    instance.stop()


@pytest.fixture
def controller(tmp_path, server):
    database = RuntimeDatabase(tmp_path / "slice2-controller.db")
    database.migrate()
    bridge = FakeCredentialBridge()
    envelopes = ConnectionCredentialEnvelopes(bridge)
    settings = ProviderSettingsRepository(database)
    catalog = ProviderCatalogRepository(database)
    keys = ProviderKeyRepository(database)
    instance = ProviderController(
        credentials=ProviderCredentials(bridge),
        settings=settings,
        events=RuntimeEventStream(),
        safety_source="test",
        catalog=catalog,
        provider_keys=keys,
        credential_envelopes=envelopes,
    )
    with database.connect() as connection:
        connection.execute(
            "UPDATE provider_directory SET base_url = ? WHERE provider_id = 'opencode-go'",
            (server.base_url,),
        )
        connection.commit()
    return instance, settings, keys


def _select_and_connect(controller):
    controller.select_provider("opencode-go")
    return controller.connect_provider("opencode-go", "test-key")


def test_connect_provider_validates_key_and_connects(controller):
    instance, settings, keys = controller
    status = _select_and_connect(instance)
    assert status["provider"] == "opencode-go"
    assert status["connected"] is True
    assert status["accessPath"] == "key"
    assert status["connections"] == {"key": True}
    assert "deepseek-v4-pro" in status["models"]["text"]
    assert status["models"]["realtime"] == []
    assert status["selection"]["text"] == "deepseek-v4-pro"  # seeded default preferred
    envelope = keys.get("opencode-go")
    assert envelope is not None


def test_connect_provider_rejects_bad_key(controller):
    instance, _, keys = controller
    instance.select_provider("opencode-go")
    with pytest.raises(OpenAIProviderError) as captured:
        instance.connect_provider("opencode-go", "wrong-key")
    assert captured.value.code == "invalid_key"
    assert keys.get("opencode-go") is None
    status = instance.status()
    assert status["connected"] is False
    assert status["models"]["text"] == []


def test_connect_provider_requires_selection_first(controller):
    instance, _, _ = controller
    with pytest.raises(OpenAIProviderError) as captured:
        instance.connect_provider("opencode-go", "test-key")
    assert captured.value.code == "provider_unavailable"


def test_status_before_connect_shows_disconnected_key_provider(controller):
    instance, _, _ = controller
    instance.select_provider("opencode-go")
    status = instance.status()
    assert status["provider"] == "opencode-go"
    assert status["connected"] is False
    assert status["accessPath"] == "key"
    assert status["models"] == {"text": [], "realtime": []}


def test_select_models_third_party_rules(controller):
    instance, _, _ = controller
    _select_and_connect(instance)
    result = instance.select_models(text_model="glm-5.2", realtime_model=None)
    assert result["selection"]["text"] == "glm-5.2"
    with pytest.raises(OpenAIProviderError) as captured:
        instance.select_models(text_model=None, realtime_model="gpt-realtime-2.1")
    assert captured.value.code == "realtime_unavailable"


def test_realtime_call_guard_for_third_party(controller):
    instance, _, _ = controller
    instance.select_provider("opencode-go")
    with pytest.raises(OpenAIProviderError) as captured:
        instance.create_realtime_call("fake-sdp")
    assert captured.value.code == "realtime_unavailable"


def test_select_access_path_rejected_for_third_party(controller):
    instance, _, _ = controller
    instance.select_provider("opencode-go")
    with pytest.raises(OpenAIProviderError) as captured:
        instance.select_access_path("platform")
    assert captured.value.code == "invalid_access_path"


def test_disconnect_provider_falls_back_to_openai(controller):
    instance, settings, keys = controller
    _select_and_connect(instance)
    status = instance.disconnect_provider("opencode-go")
    assert status["provider"] == "openai"
    assert status["accessPath"] == "platform"
    assert keys.get("opencode-go") is None
    with pytest.raises(OpenAIProviderError):
        instance.disconnect_provider("opencode-go")  # no longer active
