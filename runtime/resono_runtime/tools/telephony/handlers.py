from __future__ import annotations

import json

from resono_runtime.telephony.access import TelephonyAccess
from resono_runtime.tools import ToolInvocationContext, ToolInvocationResult


class TelephonyToolHandlers:
    def __init__(self, access: TelephonyAccess) -> None:
        self._access = access

    def invoke(
        self,
        name: str,
        context: ToolInvocationContext,
        arguments: dict[str, object],
    ) -> ToolInvocationResult:
        if name == "get_phone_status":
            snapshot = self._access.snapshot()
            return ToolInvocationResult(
                text=json.dumps(snapshot, separators=(",", ":")),
                structured_content=snapshot,
            )
        return ToolInvocationResult(f"Unknown telephony tool: {name}", is_error=True)
