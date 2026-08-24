from resono_runtime.telephony.access import TelephonyAccess


class FakeBridge:
    def simPresent(self): return True
    def simState(self): return "LOADED"
    def carrierName(self): return "AT&T"
    def networkType(self): return "LTE"
    def signalLevel(self): return 2
    def voiceRegistered(self): return True
    def callState(self): return "IDLE"


def test_snapshot_reads_bridge_primitives():
    snap = TelephonyAccess(FakeBridge()).snapshot()
    assert snap["enabled"] is True
    assert snap["simPresent"] is True
    assert snap["simState"] == "LOADED"
    assert snap["carrierName"] == "AT&T"
    assert snap["networkType"] == "LTE"
    assert snap["signalLevel"] == 2
    assert snap["voiceRegistered"] is True
    assert snap["callState"] == "IDLE"


def test_absent_bridge_is_disabled_with_safe_defaults():
    snap = TelephonyAccess(None).snapshot()
    assert snap["enabled"] is False
    assert snap["simState"] == "unknown"
    assert snap["carrierName"] == ""
    assert snap["networkType"] == ""
    assert snap["signalLevel"] == 0
    assert snap["callState"] == ""


class ThrowingBridge:
    def simPresent(self):
        raise RuntimeError("no radio")


def test_bridge_failure_is_captured_not_raised():
    snap = TelephonyAccess(ThrowingBridge()).snapshot()
    assert snap["enabled"] is True
    assert snap["simState"] == "unknown"


# ---------------------------------------------------------------------------
# Action methods: call() and sms()
# ---------------------------------------------------------------------------

class RecordingBridge:
    def __init__(self):
        self.calls = []
        self.sms = []

    def simPresent(self): return True
    def simState(self): return "LOADED"
    def carrierName(self): return "AT&T"
    def networkType(self): return "LTE"
    def signalLevel(self): return 2
    def voiceRegistered(self): return True
    def callState(self): return "IDLE"
    def placeCall(self, number):
        self.calls.append(number)
        return True

    def sendSms(self, to, text):
        self.sms.append((to, text))
        return True


def test_call_returns_ok_and_invokes_bridge():
    bridge = RecordingBridge()
    result = TelephonyAccess(bridge).call("5551234567")
    assert result["ok"] is True
    assert bridge.calls == ["5551234567"]


def test_sms_returns_ok_and_invokes_bridge():
    bridge = RecordingBridge()
    result = TelephonyAccess(bridge).sms("5551234567", "hello")
    assert result["ok"] is True
    assert bridge.sms == [("5551234567", "hello")]


def test_actions_without_bridge_are_safe():
    access = TelephonyAccess(None)
    assert access.call("5551234567") == {"ok": False, "error": "telephony unavailable"}
    assert access.sms("5551234567", "x") == {"ok": False, "error": "telephony unavailable"}


class FailingBridge(RecordingBridge):
    def placeCall(self, number):
        raise RuntimeError("no radio")

    def sendSms(self, to, text):
        raise RuntimeError("no radio")


def test_actions_capture_bridge_failure():
    access = TelephonyAccess(FailingBridge())
    assert access.call("5551234567")["ok"] is False
    assert "call error" in access.call("5551234567")["error"]
    assert access.sms("5551234567", "x")["ok"] is False
    assert "sms error" in access.sms("5551234567", "x")["error"]
