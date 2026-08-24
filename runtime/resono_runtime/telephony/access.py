from __future__ import annotations


def _as_bool(value: object, default: bool = False) -> bool:
    return bool(value) if value is not None else default


def _as_str(value: object, default: str = "") -> str:
    return str(value) if value is not None else default


def _as_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class TelephonyAccess:
    """Read-only facade over an injected native telephony bridge.

    The bridge is the Java ``TelephonyBridge`` passed into
    ``entrypoint.start`` (see the Android side of this slice). When it is
    absent (or raises), every reader returns a safe disabled value so an
    agent can never crash the runtime through this capability.
    """

    def __init__(self, bridge: object | None = None) -> None:
        self._bridge = bridge

    def enabled(self) -> bool:
        return self._bridge is not None

    def snapshot(self) -> dict[str, object]:
        bridge = self._bridge
        if bridge is None:
            return {
                "enabled": False,
                "simPresent": False,
                "simState": "unknown",
                "carrierName": "",
                "networkType": "",
                "signalLevel": 0,
                "voiceRegistered": False,
                "callState": "",
            }
        try:
            return {
                "enabled": True,
                "simPresent": _as_bool(bridge.simPresent()),
                "simState": _as_str(bridge.simState(), "unknown"),
                "carrierName": _as_str(bridge.carrierName()),
                "networkType": _as_str(bridge.networkType()),
                "signalLevel": _as_int(bridge.signalLevel()),
                "voiceRegistered": _as_bool(bridge.voiceRegistered()),
                "callState": _as_str(bridge.callState()),
            }
        except Exception:
            return {
                "enabled": True,
                "simPresent": False,
                "simState": "unknown",
                "carrierName": "",
                "networkType": "",
                "signalLevel": 0,
                "voiceRegistered": False,
                "callState": "",
            }

    def call(self, number: str) -> dict[str, object]:
        bridge = self._bridge
        if bridge is None:
            return {"ok": False, "error": "telephony unavailable"}
        try:
            ok = bool(bridge.placeCall(number))
            return {"ok": ok, "error": None if ok else "call failed"}
        except Exception as exc:
            return {"ok": False, "error": f"call error: {exc}"}

    def sms(self, to: str, text: str) -> dict[str, object]:
        bridge = self._bridge
        if bridge is None:
            return {"ok": False, "error": "telephony unavailable"}
        try:
            ok = bool(bridge.sendSms(to, text))
            return {"ok": ok, "error": None if ok else "sms failed"}
        except Exception as exc:
            return {"ok": False, "error": f"sms error: {exc}"}
