"""Slice 2 — OpenAI-compatible provider backend (TDD)."""

from __future__ import annotations

from pathlib import Path

import pytest

from resono_runtime.providers.compatible import CompatibleProvider, CompatibleProviderError

from .fake_compatible_server import FakeCompatibleServer


@pytest.fixture
def server():
    instance = FakeCompatibleServer()
    instance.start()
    yield instance
    instance.stop()


def test_verify_key_with_valid_key_returns_models(server):
    provider = CompatibleProvider(server.base_url, api_key="test-key")
    models = provider.list_models()
    assert "deepseek-v4-pro" in models
    assert "deepseek-v4-flash" in models


def test_verify_key_rejects_invalid_key(server):
    provider = CompatibleProvider(server.base_url, api_key="wrong-key")
    with pytest.raises(CompatibleProviderError) as captured:
        provider.list_models()
    assert "rejected" in str(captured.value).lower() or "401" in str(captured.value)


def test_local_provider_works_without_key():
    server = FakeCompatibleServer(require_key=False)
    server.start()
    try:
        provider = CompatibleProvider(server.base_url, api_key=None, api_style="chat")
        models = provider.list_models()
        assert models
    finally:
        server.stop()


def test_rejects_non_loopback_http_endpoint():
    with pytest.raises(CompatibleProviderError):
        CompatibleProvider("http://example.com/v1", api_key="k")


def test_endpoint_requiring_https_scheme_is_validated(server):
    with pytest.raises(CompatibleProviderError):
        CompatibleProvider("ftp://example.com/v1", api_key="k")
