from __future__ import annotations

import json

from ..agents.audience import AudienceResource, AudienceResourceKind
from ..telephony.access import TelephonyAccess
from .catalog import ToolCatalog
from .definitions import ToolDefinition, ToolInvocationResult

TELEPHONY_STATUS_NAME = "get_phone_status"
TELEPHONY_STATUS_TOOL_SET = AudienceResource(
    AudienceResourceKind.DOMAIN_TOOL_SET, "telephony-status"
)
TELEPHONY_STATUS_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def register_telephony_status(catalog: ToolCatalog, access: TelephonyAccess) -> None:
    def handle(_: dict[str, object]) -> ToolInvocationResult:
        snapshot = access.snapshot()
        return ToolInvocationResult(
            text=json.dumps(snapshot, separators=(",", ":")),
            structured_content=snapshot,
        )

    catalog.register(
        ToolDefinition(
            tool_id="telephony.status.v1",
            name=TELEPHONY_STATUS_NAME,
            description="Read current SIM, carrier, network, signal, and voice state from the R1 modem.",
            input_schema=TELEPHONY_STATUS_SCHEMA,
            handler=handle,
            audience_resource=TELEPHONY_STATUS_TOOL_SET,
        )
    )
