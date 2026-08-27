"""Shared fixtures for slice 1 MCP transport tests."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from resono_runtime.agents.routing import AgentAudienceRouter
from resono_runtime.agents.audience import AgentAudience
from resono_runtime.connections.records import ConnectionRepository
from resono_runtime.mcp.lifecycle import McpLifecycle
from resono_runtime.security.credentials import ConnectionCredentialEnvelopes
from resono_runtime.storage.agent_audiences import AgentAudienceRepository
from resono_runtime.storage.connection_credentials import ConnectionCredentialRepository
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.mcp_connections import McpConnectionRepository
from resono_runtime.storage.mcp_routing import McpRoutingRepository
from resono_runtime.tools.catalog import ToolCatalog


class FakeCredentialBridge:
    """Test double for the Android credential bridge protocol (seal/open only)."""

    def hasOpenAiPlatformKey(self) -> bool:
        return False

    def getOpenAiPlatformKey(self) -> str | None:
        return None

    def putOpenAiPlatformKey(self, value: str) -> None:
        raise NotImplementedError

    def deleteOpenAiPlatformKey(self) -> None:
        raise NotImplementedError

    def hasOpenAiSubscriptionTokens(self) -> bool:
        return False

    def getOpenAiSubscriptionTokens(self) -> str | None:
        return None

    def putOpenAiSubscriptionTokens(self, value: str) -> None:
        raise NotImplementedError

    def deleteOpenAiSubscriptionTokens(self) -> None:
        raise NotImplementedError

    def sealConnectionCredential(self, record_name: str, plaintext: str) -> str:
        return f"sealed:{plaintext}"

    def openConnectionCredential(self, record_name: str, envelope: str) -> str:
        if not envelope.startswith("sealed:"):
            raise ValueError("unseal failed")
        return envelope[len("sealed:") :]


@pytest.fixture
def lifecycle(tmp_path):
    database = RuntimeDatabase(tmp_path / "slice1-test.db")
    database.migrate()
    bindings = AgentAudienceRepository(database)
    router = AgentAudienceRouter(bindings)
    tools = ToolCatalog(audience_router=router)
    instance = McpLifecycle(
        McpConnectionRepository(database),
        ConnectionRepository(database),
        router,
        tools,
        ConnectionCredentialRepository(database),
        ConnectionCredentialEnvelopes(FakeCredentialBridge()),
        McpRoutingRepository(database),
    )
    return instance, tools, database


STDIO_SCRIPT = __import__("os").path.join(__import__("os").path.dirname(__file__), "fake_stdio_mcp_server.py")


def make_stdio_config() -> dict:
    return {"type": "stdio", "command": sys.executable, "args": [STDIO_SCRIPT]}


def make_sse_config(server) -> dict:
    return {"type": "sse", "url": server.url}


def install(lifecycle, connection_id: str, configuration: dict, display_name: str = "test provider"):
    lifecycle.install(
        connection_id=connection_id,
        display_name=display_name,
        configuration=configuration,
        audience=AgentAudience.VOICE,
        changed_by="test",
        reason="test",
    )
