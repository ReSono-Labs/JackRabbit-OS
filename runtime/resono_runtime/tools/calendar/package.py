from __future__ import annotations

from resono_runtime.agents import AudienceResource, AudienceResourceKind
from resono_runtime.tools.catalog import ToolCatalog
from resono_runtime.tools.definitions import ToolDefinition, ToolInvocationResult

from .contract import CALENDAR_PACKAGE_VERSION, contracts
from .handlers import CalendarToolHandlers, CalendarToolService


CALENDAR_TOOL_SET = AudienceResource(AudienceResourceKind.DOMAIN_TOOL_SET, "calendar")


class CalendarToolPackage:
    """One versioned registration boundary for every built-in Calendar tool."""

    def __init__(self, service: CalendarToolService) -> None:
        self._handlers = CalendarToolHandlers(service)

    def definitions(self) -> tuple[ToolDefinition, ...]:
        result: list[ToolDefinition] = []
        for contract in contracts():
            result.append(
                ToolDefinition(
                    tool_id=f"builtin.calendar.{contract.name}.v{CALENDAR_PACKAGE_VERSION}",
                    name=contract.name,
                    description=contract.description,
                    input_schema=contract.input_schema,
                    handler=lambda _: ToolInvocationResult(
                        "Calendar requires an agent invocation context.", is_error=True
                    ),
                    context_handler=lambda context, arguments, name=contract.name: self._handlers.invoke(
                        name, context, arguments
                    ),
                    effect_class=contract.effect_class,
                    audience_resource=CALENDAR_TOOL_SET,
                )
            )
        return tuple(result)

    def register(self, catalog: ToolCatalog) -> None:
        definitions = self.definitions()
        if len(definitions) != len(contracts()):
            raise RuntimeError("Calendar tool package is incomplete.")
        for definition in definitions:
            catalog.register(definition)
