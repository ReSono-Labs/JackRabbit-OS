from __future__ import annotations

import json
import threading
import time
from uuid import uuid4

from resono_runtime.telephony.access import TelephonyAccess
from resono_runtime.tools import ToolInvocationContext, ToolInvocationResult


class PendingActionStore:
    _TTL_SECONDS = 120.0

    def __init__(self) -> None:
        self._actions: dict[str, dict[str, object]] = {}
        self._lock = threading.Lock()

    def create(self, kind: str, target: str, text: str, utterance: str) -> str:
        with self._lock:
            action_id = uuid4().hex[:12]
            self._actions[action_id] = {
                "id": action_id,
                "kind": kind,
                "target": target,
                "text": text,
                "utterance": utterance,
                "expires_at": time.monotonic() + self._TTL_SECONDS,
                "consumed": False,
            }
        return action_id

    def claim(self, action_id: str, utterance: str) -> dict[str, object] | None:
        with self._lock:
            action = self._actions.get(action_id)
            if action is None:
                return None
            if bool(action.get("consumed")):
                return None
            if time.monotonic() > float(action["expires_at"]):
                del self._actions[action_id]
                return None
            if str(action.get("utterance", "")) != utterance:
                return None
            action["consumed"] = True
            return action


class TelephonyToolHandlers:
    def __init__(self, access: TelephonyAccess) -> None:
        self._access = access
        self._pending = PendingActionStore()

    @staticmethod
    def _utterance(context: ToolInvocationContext) -> str:
        return (getattr(context, "user_utterance", None) or "").strip()

    def invoke(
        self,
        name: str,
        context: ToolInvocationContext,
        arguments: dict[str, object],
    ) -> ToolInvocationResult:
        utterance = self._utterance(context)

        if name == "get_phone_status":
            snapshot = self._access.snapshot()
            return ToolInvocationResult(
                text=json.dumps(snapshot, separators=(",", ":")),
                structured_content=snapshot,
            )

        if name == "place_call":
            number = str(arguments.get("number") or "")
            if not number:
                return ToolInvocationResult("place_call requires a number.", is_error=True)
            action_id = self._pending.create("call", number, "", utterance)
            return ToolInvocationResult(
                f"OK to call {number}? Confirm to proceed.",
                structured_content={"pendingActionId": action_id, "kind": "call", "target": number},
            )

        if name == "send_sms":
            to = str(arguments.get("to") or "")
            text = str(arguments.get("text") or "")
            if not to or not text:
                return ToolInvocationResult("send_sms requires both to and text.", is_error=True)
            action_id = self._pending.create("sms", to, text, utterance)
            return ToolInvocationResult(
                f"OK to text {to}: {text}? Confirm to proceed.",
                structured_content={"pendingActionId": action_id, "kind": "sms", "target": to},
            )

        if name == "confirm_action":
            action_id = str(arguments.get("id") or "")
            action = self._pending.claim(action_id, utterance)
            if action is None:
                return ToolInvocationResult(
                    "Cannot confirm: action is missing, expired, already used, or not bound to this request.",
                    is_error=True,
                )
            if action["kind"] == "call":
                result = self._access.call(str(action["target"]))
            else:
                result = self._access.sms(str(action["target"]), str(action.get("text", "")))
            return ToolInvocationResult(
                json.dumps(result, separators=(",", ":")),
                structured_content=result,
            )

        return ToolInvocationResult(f"Unknown telephony tool: {name}", is_error=True)
