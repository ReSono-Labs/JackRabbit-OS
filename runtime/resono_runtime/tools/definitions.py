from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..agents.audience import AgentKind, AudienceResource


ToolHandler = Callable[[dict[str, object]], "ToolInvocationResult"]
AgentToolHandler = Callable[[AgentKind, dict[str, object]], "ToolInvocationResult"]
ToolAvailability = Callable[[AgentKind], bool]


@dataclass(frozen=True, slots=True)
class ToolInvocationContext:
    agent: AgentKind
    voice_session_id: str | None = None
    tool_call_id: str | None = None
    user_utterance: str | None = None
    user_utterance_id: int | None = None


ContextToolHandler = Callable[[ToolInvocationContext, dict[str, object]], "ToolInvocationResult"]


@dataclass(frozen=True, slots=True)
class ToolInvocationResult:
    text: str
    structured_content: dict[str, object] | None = None
    is_error: bool = False

    def mcp_result(self) -> dict[str, object]:
        result: dict[str, object] = {
            "content": [{"type": "text", "text": self.text}],
            "isError": self.is_error,
        }
        if self.structured_content is not None:
            result["structuredContent"] = self.structured_content
        return result


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    tool_id: str
    name: str
    description: str
    input_schema: dict[str, object]
    handler: ToolHandler
    effect_class: str = "read"
    voice_available: bool = True
    audience_resource: AudienceResource | None = None
    agent_handler: AgentToolHandler | None = None
    context_handler: ContextToolHandler | None = None
    available_to: ToolAvailability | None = None

    def mcp_definition(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }

    def realtime_definition(self) -> dict[str, object]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema,
        }
