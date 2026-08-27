"""Slice 2 — text runner resolves third-party provider access end-to-end."""

from __future__ import annotations

import pytest

from resono_runtime.agents.runner import AgentsSdkTextRunner
from resono_runtime.api.events import RuntimeEventStream
from resono_runtime.security.credentials import ConnectionCredentialEnvelopes, ProviderCredentials
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.provider_catalog import ProviderCatalogRepository
from resono_runtime.storage.provider_keys import ProviderKeyRepository
from resono_runtime.storage.provider_settings import ProviderSettingsRepository

from .conftest import FakeCredentialBridge


@pytest.fixture
def context(tmp_path):
    database = RuntimeDatabase(tmp_path / "slice2-runner.db")
    database.migrate()
    bridge = FakeCredentialBridge()
    settings = ProviderSettingsRepository(database)
    catalog = ProviderCatalogRepository(database)
    keys = ProviderKeyRepository(database)
    envelopes = ConnectionCredentialEnvelopes(bridge)
    settings.save(provider="opencode-go", text_model="deepseek-v4-pro", realtime_model=None)
    keys.put("opencode-go", envelopes.seal_provider_key("opencode-go", "go-secret"))
    return database, settings, catalog, keys, envelopes, bridge


def test_runner_third_party_turn_uses_chat_style_and_forces_no_reasoning(context):
    database, settings, catalog, keys, envelopes, bridge = context
    captured: dict = {}
    events = RuntimeEventStream()

    def executor(**kwargs):
        captured.update(kwargs)
        return "echo:hello"

    runner = AgentsSdkTextRunner(
        credentials=ProviderCredentials(bridge),
        settings=settings,
        events=events,
        local_api_token="t" * 32,
        executor=executor,
        catalog=catalog,
        credential_envelopes=envelopes,
        provider_keys=keys,
    )
    result = runner.run("Say hello")
    assert result.text == "echo:hello"
    assert captured["api_key"] == "go-secret"
    assert captured["base_url"] == "https://opencode.ai/zen/go/v1"
    assert captured["use_responses"] is False
    assert captured["reasoning_effort"] == "none"
    assert captured["model"] == "deepseek-v4-pro"
