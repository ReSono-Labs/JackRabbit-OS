from resono_runtime.agents import AudienceResource, AudienceResourceKind
from resono_runtime.tools.catalog import ToolCatalog
from resono_runtime.tools.definitions import ToolDefinition, ToolInvocationResult
from .contract import TASKS_PACKAGE_VERSION, contracts
from .handlers import TaskToolHandlers, TaskToolService

TASKS_TOOL_SET = AudienceResource(AudienceResourceKind.DOMAIN_TOOL_SET, "tasks")

class TasksToolPackage:
    """One versioned registration boundary for every built-in Tasks tool."""
    def __init__(self, service: TaskToolService) -> None: self._handlers = TaskToolHandlers(service)
    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(ToolDefinition(
            tool_id=f"builtin.tasks.{item.name}.v{TASKS_PACKAGE_VERSION}", name=item.name,
            description=item.description, input_schema=item.input_schema,
            handler=lambda _: ToolInvocationResult("Tasks requires an agent invocation context.", is_error=True),
            context_handler=lambda context, arguments, name=item.name: self._handlers.invoke(name, context, arguments),
            effect_class=item.effect_class, audience_resource=TASKS_TOOL_SET) for item in contracts())
    def register(self, catalog: ToolCatalog) -> None:
        definitions = self.definitions()
        if len(definitions) != len(contracts()): raise RuntimeError("Tasks tool package is incomplete.")
        for definition in definitions: catalog.register(definition)
