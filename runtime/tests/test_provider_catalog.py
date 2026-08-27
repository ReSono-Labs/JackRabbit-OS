"""Slice 2 — provider catalog extension: descriptors, styles, seeds (TDD)."""

from __future__ import annotations

from pathlib import Path

from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.provider_catalog import ProviderCatalogRepository


def _repo(tmp_path) -> ProviderCatalogRepository:
    database = RuntimeDatabase(tmp_path / "slice2-catalog.db")
    database.migrate()
    return ProviderCatalogRepository(database)


def test_catalog_seeds_providers_with_styles(tmp_path):
    repo = _repo(tmp_path)
    by_id = {item.provider_id: item for item in repo.providers()}
    assert "openai" in by_id
    assert by_id["openai"].api_style == "responses"

    for provider_id, expected_url, expected_style, key_required, voice in (
        ("opencode-go", "https://opencode.ai/zen/go/v1", "chat", True, "none"),
        ("opencode-zen", "https://opencode.ai/zen/v1", "chat", True, "none"),
        ("openrouter", "https://openrouter.ai/api/v1", "chat", True, "none"),
        ("glm", "https://api.z.ai/api/coding/paas/v4", "chat", True, "none"),
        ("kimi", "https://api.kimi.com/coding/v1", "chat", True, "none"),
        ("local", "http://127.0.0.1:11434/v1", "chat", False, "none"),
        ("gemini", "https://generativelanguage.googleapis.com/v1beta", "chat", True, "websocket"),
    ):
        descriptor = by_id.get(provider_id)
        assert descriptor is not None, f"{provider_id} not seeded"
        assert descriptor.base_url == expected_url, provider_id
        assert descriptor.api_style == expected_style, provider_id
        assert descriptor.key_required is key_required, provider_id
        assert descriptor.voice == voice, provider_id
    assert by_id["openai"].voice == "webrtc"
    assert by_id["gemini"].auth_header == "x-goog-api-key"


def test_catalog_descriptor_lookup(tmp_path):
    repo = _repo(tmp_path)
    go = repo.descriptor("opencode-go")
    assert go is not None
    assert go.base_url == "https://opencode.ai/zen/go/v1"
    assert go.name == "OpenCode Go"
    assert repo.descriptor("does-not-exist") is None


def test_catalog_seeds_text_models_for_opencode_plans(tmp_path):
    repo = _repo(tmp_path)
    go_models = repo.models("opencode-go", "key", "text")
    assert "deepseek-v4-pro" in go_models
    assert "deepseek-v4-flash" in go_models
    zen_models = repo.models("opencode-zen", "key", "text")
    assert "claude-opus-4-8" in zen_models


def test_catalog_realtime_models(tmp_path):
    repo = _repo(tmp_path)
    assert repo.models("opencode-go", "key", "realtime") == ()
    assert repo.models("openrouter", "key", "realtime") == ()
    gemini_realtime = repo.models("gemini", "key", "realtime")
    assert "gemini-3.1-flash-live-preview" in gemini_realtime
