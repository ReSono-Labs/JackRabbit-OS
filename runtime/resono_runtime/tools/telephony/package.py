from __future__ import annotations

from resono_runtime.agents import AudienceResource, AudienceResourceKind
from resono_runtime.telephony.access import TelephonyAccess
from resono_runtime.tools.catalog import ToolCatalog
from resono_runtime.tools.definitions import ToolDefinition, ToolInvocationResult

from .contract import TELEPHONY_PACKAGE_VERSION, contracts
from .handlers import TelephonyToolHandlers


TELEPHONY_TOOL_SET = AudienceResource(AudienceResourceKind.DOMAIN_TOOL_SET, "telephony")


class TelephonyToolPackage:
    """One versioned registration boundary for every built-in Telephony tool."""

    def __init__(self, access: TelephonyAccess) -> None:
        self._handlers = TelephonyToolHandlers(access)

    def definitions(self) -> tuple[ToolDefinition, ...]:
        result: list[ToolDefinition] = []
        for contract in contracts():
            result.append(
                ToolDefinition(
                    tool_id=f"builtin.telephony.{contract.name}.v{TELEPHONY_PACKAGE_VERSION}",
                    name=contract.name,
                    description=contract.description,
                    input_schema=contract.input_schema,
                    handler=lambda _: ToolInvocationResult(
                        "Telephony requires an agent invocation context.", is_error=True
                    ),
                    context_handler=lambda context, arguments, name=contract.name: self._handlers.invoke(
                        name, context, arguments
                    ),
                    effect_class=contract.effect_class,
                    audience_resource=TELEPHONY_TOOL_SET,
                )
            )
        return tuple(result)

    def register(self, catalog: ToolCatalog) -> None:
        definitions = self.definitions()
        if len(definitions) != len(contracts()):
            raise RuntimeError("Telephony tool package is incomplete.")
        for definition in definitions:
            catalog.register(definition)
