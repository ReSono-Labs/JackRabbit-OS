from __future__ import annotations

from typing import Protocol

from resono_runtime.tools import ToolInvocationContext, ToolInvocationResult


class CalendarToolService(Protocol):
    """Application-facing Calendar operations required by the tool package."""

    def invoke_tool(
        self,
        name: str,
        context: ToolInvocationContext,
        arguments: dict[str, object],
    ) -> ToolInvocationResult: ...


class CalendarToolHandlers:
    def __init__(self, service: CalendarToolService) -> None:
        self._service = service

    def invoke(
        self,
        name: str,
        context: ToolInvocationContext,
        arguments: dict[str, object],
    ) -> ToolInvocationResult:
        return self._service.invoke_tool(name, context, arguments)
