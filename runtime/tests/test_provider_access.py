"""Slice 2 — provider_access resolver decision tests (TDD)."""

from __future__ import annotations

import pytest

from resono_runtime.providers.access import ProviderAccess, provider_access
from resono_runtime.providers.openai import OpenAIProviderError
from resono_runtime.security.credentials import ConnectionCredentialEnvelopes, ProviderCredentials
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.provider_catalog import ProviderCatalogRepository
from resono_runtime.storage.provider_keys import ProviderKeyRepository
from resono_runtime.storage.provider_settings import ProviderSettingsRepository

from .conftest import FakeCredentialBridge


class PlatformKeyBridge(FakeCredentialBridge):
    def getOpenAiPlatformKey(self) -> str | None:
        return "pk-test"


@pytest.fixture
def context(tmp_path):
    database = RuntimeDatabase(tmp_path / "slice2-access.db")
    database.migrate()
    bridge = FakeCredentialBridge()
    return {
        "database": database,
        "bridge": bridge,
        "envelopes": ConnectionCredentialEnvelopes(bridge),
        "settings": ProviderSettingsRepository(database),
        "catalog": ProviderCatalogRepository(database),
        "keys": ProviderKeyRepository(database),
    }


def _resolve(context, settings, *, credentials=None):
    return provider_access(
        credentials=credentials or ProviderCredentials(context["bridge"]),
        settings=settings,
        subscription=None,
        catalog=context["catalog"],
        envelopes=context["envelopes"],
        keys=context["keys"],
    )


def test_openai_platform_path_unchanged(context):
    settings = context["settings"]
    settings.save(text_model="gpt-5.6-sol", realtime_model=None)
    access = _resolve(context, settings, credentials=ProviderCredentials(PlatformKeyBridge()))
    assert access == ProviderAccess("pk-test", None, True, "openai")


def test_openai_without_key_raises_credential_unavailable(context):
    settings = context["settings"]
    settings.save(text_model="gpt-5.6-sol", realtime_model=None)
    with pytest.raises(OpenAIProviderError) as captured:
        _resolve(context, settings)
    assert captured.value.code == "credential_unavailable"


def test_third_party_resolves_key_url_and_chat_style(context):
    settings = context["settings"]
    settings.save(provider="opencode-go", text_model="deepseek-v4-pro", realtime_model=None)
    context["keys"].put("opencode-go", context["envelopes"].seal_provider_key("opencode-go", "go-secret"))
    access = _resolve(context, settings)
    assert access == ProviderAccess("go-secret", "https://opencode.ai/zen/go/v1", False, "opencode-go")


def test_third_party_without_key_raises_connect_first(context):
    settings = context["settings"]
    settings.save(provider="kimi", text_model="kimi-k2.7-code", realtime_model=None)
    with pytest.raises(OpenAIProviderError) as captured:
        _resolve(context, settings)
    assert captured.value.code == "credential_unavailable"
    assert "kimi" in str(captured.value)
