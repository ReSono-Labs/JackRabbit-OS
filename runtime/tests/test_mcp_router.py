"""Slice 1 — per-audience MCP connection router (TDD)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from resono_runtime.agents.audience import AgentAudience
from resono_runtime.api.mcp_routes import McpRoutes
from resono_runtime.mcp.client import McpConnectionError

from .conftest import install, make_stdio_config


def test_router_select_and_active_persists(lifecycle):
    instance, _, database = lifecycle
    connection_id = str(uuid4())
    install(instance, connection_id, make_stdio_config())

    assert instance.active_connection(AgentAudience.VOICE) is None
    assert instance.select_connection(AgentAudience.VOICE, connection_id) == connection_id
    assert instance.active_connection(AgentAudience.VOICE) == connection_id
    assert instance.audiences_for(connection_id) == (AgentAudience.VOICE,)

    # persists across a fresh lifecycle over the same database
    from resono_runtime.connections.records import ConnectionRepository
    from resono_runtime.mcp.lifecycle import McpLifecycle
    from resono_runtime.security.credentials import ConnectionCredentialEnvelopes
    from resono_runtime.storage.agent_audiences import AgentAudienceRepository
    from resono_runtime.storage.connection_credentials import ConnectionCredentialRepository
    from resono_runtime.storage.mcp_connections import McpConnectionRepository
    from resono_runtime.storage.mcp_routing import McpRoutingRepository
    from resono_runtime.tools.catalog import ToolCatalog
    from resono_runtime.agents.routing import AgentAudienceRouter

    from .conftest import FakeCredentialBridge

    fresh = McpLifecycle(
        McpConnectionRepository(database),
        ConnectionRepository(database),
        AgentAudienceRouter(AgentAudienceRepository(database)),
        ToolCatalog(),
        ConnectionCredentialRepository(database),
        ConnectionCredentialEnvelopes(FakeCredentialBridge()),
        McpRoutingRepository(database),
    )
    assert fresh.active_connection(AgentAudience.VOICE) == connection_id


def test_router_select_rejects_failed_connection(lifecycle):
    instance, _, _ = lifecycle
    connection_id = str(uuid4())
    install(instance, connection_id, {"type": "sse", "url": "http://127.0.0.1:1/sse"})
    with pytest.raises(McpConnectionError):
        instance.discover(connection_id, changed_by="test", reason="test")
    assert instance.get(connection_id).lifecycle_state == "failed"
    with pytest.raises(ValueError):
        instance.select_connection(AgentAudience.VOICE, connection_id)
    assert instance.active_connection(AgentAudience.VOICE) is None


def test_router_select_rejects_unknown_connection(lifecycle):
    instance, _, _ = lifecycle
    with pytest.raises(ValueError):
        instance.select_connection(AgentAudience.VOICE, str(uuid4()))


def test_router_remove_cleans_routing(lifecycle):
    instance, _, _ = lifecycle
    connection_id = str(uuid4())
    install(instance, connection_id, make_stdio_config())
    instance.select_connection(AgentAudience.VOICE, connection_id)
    assert instance.active_connection(AgentAudience.VOICE) == connection_id
    assert instance.remove(connection_id, changed_by="test", reason="test") is True
    assert instance.active_connection(AgentAudience.VOICE) is None


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


def test_api_select_action_and_view(lifecycle, monkeypatch):
    from resono_runtime.api import mcp_routes as routes_module

    instance, _, _ = lifecycle
    connection_id = str(uuid4())
    install(instance, connection_id, make_stdio_config())

    monkeypatch.setattr(routes_module, "_session", lambda request, pairing, *, mutation: True)
    routes = McpRoutes(instance)

    request = StubRequest(f"/v1/management/mcp/connections/{connection_id}/select", {"audience": "voice"})
    assert routes.handle_post(request, None) is True
    assert request.response is not None
    status, payload = request.response
    assert status == 200
    assert payload["connectionId"] == connection_id
    assert payload["activeAudiences"] == ["voice"]

    # view reflects routing in the list endpoint too
    list_request = StubRequest("/v1/management/mcp/connections")
    assert routes.handle_get(list_request, None) is True
    status, payload = list_request.response
    assert status == 200
    match = [item for item in payload["connections"] if item["connectionId"] == connection_id]
    assert match and match[0]["activeAudiences"] == ["voice"]


def test_api_select_rejects_bad_audience(lifecycle, monkeypatch):
    from resono_runtime.api import mcp_routes as routes_module

    instance, _, _ = lifecycle
    connection_id = str(uuid4())
    install(instance, connection_id, make_stdio_config())
    monkeypatch.setattr(routes_module, "_session", lambda request, pairing, *, mutation: True)
    routes = McpRoutes(instance)

    request = StubRequest(f"/v1/management/mcp/connections/{connection_id}/select", {"audience": "everyone"})
    assert routes.handle_post(request, None) is True
    assert request.response is not None
    status, payload = request.response
    assert status == 409
    assert payload["error"]["code"] == "mcp_connection_conflict"
