"""Slice 1 — McpLifecycle parity across all three transports (TDD)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from resono_runtime.agents.audience import AgentAudience, AgentKind
from resono_runtime.mcp.lifecycle import McpLifecycle

from .conftest import install, make_sse_config, make_stdio_config
from .fake_sse_server import FakeSseMcpServer


def test_lifecycle_install_sse_and_stdio_are_not_failed(lifecycle):
    instance, _, _ = lifecycle
    sse_id = str(uuid4())
    install(instance, sse_id, {"type": "sse", "url": "https://example.invalid/sse"})
    record = instance.get(sse_id)
    assert record is not None
    assert record.lifecycle_state != "failed"
    assert record.health_detail is None

    stdio_id = str(uuid4())
    install(instance, stdio_id, make_stdio_config())
    record = instance.get(stdio_id)
    assert record is not None
    assert record.lifecycle_state != "failed"
    assert record.health_detail is None


def test_lifecycle_discover_enable_and_invoke_sse(lifecycle):
    instance, tools, _ = lifecycle
    server = FakeSseMcpServer()
    server.start()
    try:
        connection_id = str(uuid4())
        install(instance, connection_id, make_sse_config(server), display_name="Claude SSE")

        discovered = instance.discover(connection_id, changed_by="test", reason="test")
        assert discovered.lifecycle_state == "configured"
        assert discovered.server_name == "fake-sse"

        instance.grant_tool(connection_id, "echo", enabled=True, effect_class="read")

        enabled = instance.set_enabled(connection_id, True, changed_by="test", reason="test")
        assert enabled.lifecycle_state == "connected"

        names = {definition.name for definition in tools.definitions_for(AgentKind.VOICE)}
        assert names, "no tools projected"
        echo_name = next(name for name in names if name.endswith("__echo"))

        result = tools.invoke(echo_name, {"text": "from-sse"}, agent=AgentKind.VOICE)
        assert result.is_error is False
        assert "from-sse" in result.text
    finally:
        server.stop()


def test_lifecycle_discover_enable_and_invoke_stdio(lifecycle):
    instance, tools, _ = lifecycle
    connection_id = str(uuid4())
    install(instance, connection_id, make_stdio_config(), display_name="Local LLM")

    discovered = instance.discover(connection_id, changed_by="test", reason="test")
    assert discovered.lifecycle_state == "configured"
    assert discovered.server_name == "fake-stdio"

    instance.grant_tool(connection_id, "say", enabled=True, effect_class="read")

    enabled = instance.set_enabled(connection_id, True, changed_by="test", reason="test")
    assert enabled.lifecycle_state == "connected"

    names = {definition.name for definition in tools.definitions_for(AgentKind.VOICE)}
    say_name = next(name for name in names if name.endswith("__say"))

    result = tools.invoke(say_name, {"message": "from-stdio"}, agent=AgentKind.VOICE)
    assert result.is_error is False
    assert "from-stdio" in result.text


def test_lifecycle_restore_projects_connected_stdio_connections(lifecycle):
    instance, tools, database = lifecycle
    connection_id = str(uuid4())
    install(instance, connection_id, make_stdio_config())
    instance.discover(connection_id, changed_by="test", reason="test")
    instance.grant_tool(connection_id, "say", enabled=True, effect_class="read")
    instance.set_enabled(connection_id, True, changed_by="test", reason="test")
    assert tools.definitions_for(AgentKind.VOICE)

    # a fresh lifecycle over the same database restores and re-projects tools
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

    fresh_tools = ToolCatalog()
    fresh_instance = McpLifecycle(
        McpConnectionRepository(database),
        ConnectionRepository(database),
        AgentAudienceRouter(AgentAudienceRepository(database)),
        fresh_tools,
        ConnectionCredentialRepository(database),
        ConnectionCredentialEnvelopes(FakeCredentialBridge()),
        McpRoutingRepository(database),
    )
    fresh_instance.restore()
    names = {definition.name for definition in fresh_tools.definitions_for(AgentKind.VOICE)}
    assert any(name.endswith("__say") for name in names)
