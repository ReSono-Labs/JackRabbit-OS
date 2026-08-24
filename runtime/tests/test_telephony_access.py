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
