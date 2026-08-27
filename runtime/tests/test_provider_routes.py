"""Slice 2 — management/host provider route dispatch (TDD)."""

from __future__ import annotations

from pathlib import Path

import pytest

from resono_runtime.api.events import RuntimeEventStream
from resono_runtime.api.routes import RuntimeRoutes
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.lifecycle_repository import LifecycleRepository


class StubProvider:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def connect_provider(self, provider: str, key: str) -> dict:
        self.calls.append(("connect", provider, key))
        return {"provider": provider, "connected": True}

    def disconnect_provider(self, provider: str) -> dict:
        self.calls.append(("disconnect", provider))
        return {"provider": provider, "connected": False}

    def select_provider(self, provider: str) -> dict:
        self.calls.append(("select", provider))
        return {"provider": provider}

    def select_models(self, *, text_model=None, realtime_model=None, reasoning_effort=None) -> dict:
        self.calls.append(("models", text_model, realtime_model))
        return {"selection": {"text": text_model}}

    def status(self, *, refresh: bool = False) -> dict:
        self.calls.append(("status", refresh))
        return {"provider": "opencode-go", "connected": True}


class StubRequest:
    def __init__(self, path: str, payload: dict | None = None) -> None:
        self.path = path
        self._payload = payload
        self.headers = {}
        self.response: tuple[int, dict] | None = None

    def request_json(self, *, max_bytes: int = 4096) -> dict | None:
        return self._payload

    def respond_json(self, status: int, payload: dict, *, headers: dict | None = None) -> None:
        self.response = (status, payload)

    def provider_error(self, error) -> None:
        self.response = (error.status, {"error": {"code": error.code, "message": str(error)}})


@pytest.fixture
def routes(tmp_path):
    database = RuntimeDatabase(tmp_path / "slice2-routes.db")
    database.migrate()
    provider = StubProvider()
    instance = RuntimeRoutes(
        health=object(),
        lifecycle=LifecycleRepository(database),
        events=RuntimeEventStream(),
        pairing=None,
        providers=provider,
        text_runner=None,
        subscription=None,
        mcp=None,
        profile=None,
        sessions=None,
        memory=None,
        restart_request=None,
    )
    return instance, provider


def test_host_providers_connect_dispatches(routes):
    instance, provider = routes
    request = StubRequest("/v1/host/providers/connect", {"provider": "opencode-go", "apiKey": "sk-go"})
    instance.handle_post(request)
    assert request.response is not None and request.response[0] == 200
    assert request.response[1]["provider"] == "opencode-go"
    assert provider.calls[0] == ("connect", "opencode-go", "sk-go")


def test_host_providers_disconnect_dispatches(routes):
    instance, provider = routes
    request = StubRequest("/v1/host/providers/disconnect", {"provider": "kimi"})
    instance.handle_post(request)
    assert request.response[0] == 200
    assert provider.calls[0] == ("disconnect", "kimi")


def test_host_providers_models_and_refresh_dispatches(routes):
    instance, provider = routes
    instance.handle_post(StubRequest("/v1/host/providers/models", {"textModel": "glm-5.2"}))
    assert provider.calls[0] == ("models", "glm-5.2", None)
    instance.handle_post(StubRequest("/v1/host/providers/refresh", {}))
    assert provider.calls[1] == ("status", True)


def test_host_providers_unknown_action_404(routes):
    instance, _ = routes
    request = StubRequest("/v1/host/providers/frobnicate", {})
    instance.handle_post(request)
    assert request.response[0] == 404


def test_management_providers_requires_pairing(routes):
    instance, _ = routes
    request = StubRequest("/v1/management/providers/connect", {"provider": "glm", "apiKey": "k"})
    instance.handle_post(request)
    assert request.response[0] == 404  # pairing unavailable -> block skipped
