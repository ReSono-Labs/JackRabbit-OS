from typing import Protocol
from resono_runtime.tools import ToolInvocationContext, ToolInvocationResult

class TaskToolService(Protocol):
    def invoke_tool(self, name: str, context: ToolInvocationContext, arguments: dict[str, object]) -> ToolInvocationResult: ...

class TaskToolHandlers:
    def __init__(self, service: TaskToolService) -> None: self._service = service
    def invoke(self, name: str, context: ToolInvocationContext, arguments: dict[str, object]) -> ToolInvocationResult:
        return self._service.invoke_tool(name, context, arguments)
