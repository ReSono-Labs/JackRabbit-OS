from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING

from ..agents.audience import AudienceResource, AudienceResourceKind

from .catalog import ToolCatalog
from .definitions import ToolDefinition, ToolInvocationResult

if TYPE_CHECKING:
    from ..memory.tools import MemoryLookupTool


DEVICE_STATUS_NAME = "get_device_status"
DEVICE_STATUS_TOOL_SET = AudienceResource(AudienceResourceKind.DOMAIN_TOOL_SET, "device-status")
MEMORY_TOOL_SET = AudienceResource(AudienceResourceKind.DOMAIN_TOOL_SET, "memory")
DEVICE_STATUS_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def register_device_status(catalog: ToolCatalog, health: Callable[[], dict[str, object]]) -> None:
    def handle(_: dict[str, object]) -> ToolInvocationResult:
        status = health()
        safe = {
            "status": status.get("status", "not_ready"),
            "service": status.get("service", "resono-runtime"),
            "contractVersion": status.get("contractVersion"),
        }
        return ToolInvocationResult(
            text=json.dumps(safe, separators=(",", ":")),
            structured_content=safe,
        )

    catalog.register(
        ToolDefinition(
            tool_id="builtin.device-status.v1",
            name=DEVICE_STATUS_NAME,
            description="Read the current health of this ReSono R1 on-device runtime.",
            input_schema=DEVICE_STATUS_SCHEMA,
            handler=handle,
            audience_resource=DEVICE_STATUS_TOOL_SET,
        )
    )


def register_memory_lookup(catalog: ToolCatalog, memory_lookup: "MemoryLookupTool") -> None:
    catalog.register(
        ToolDefinition(
            tool_id="builtin.memory-lookup.v1",
            name=memory_lookup.name(),
            description=memory_lookup.description(),
            input_schema=memory_lookup.parameters(),
            handler=lambda arguments: ToolInvocationResult(memory_lookup.call(arguments)),
            audience_resource=MEMORY_TOOL_SET,
        )
    )
