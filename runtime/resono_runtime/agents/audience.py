"""Stable agent-audience vocabulary for user-selected capability exposure."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AgentKind(str, Enum):
    """A local R1 agent surface that can receive a capability projection."""

    VOICE = "voice"
    TEXT = "text"


class AgentAudience(str, Enum):
    """The local agents selected by the user for one capability."""

    VOICE = "voice"
    TEXT = "text"
    BOTH = "both"

    def includes(self, agent: AgentKind) -> bool:
        return self is AgentAudience.BOTH or self.value == agent.value


class AudienceResourceKind(str, Enum):
    """Closed resource kinds that may be projected to a local agent."""

    SKILL = "skill"
    PLUGIN = "plugin"
    MCP_CONNECTION = "mcp_connection"
    DOMAIN_TOOL_SET = "domain_tool_set"
    CREATION = "creation"


@dataclass(frozen=True)
class AudienceResource:
    """A stable owner-created reference to a routable capability."""

    kind: AudienceResourceKind
    stable_id: str

    def __post_init__(self) -> None:
        if not self.stable_id or self.stable_id.strip() != self.stable_id:
            raise ValueError("stable_id must be a non-empty trimmed string")

