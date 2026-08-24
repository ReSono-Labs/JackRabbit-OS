from resono_runtime.tools import ToolCatalog, register_telephony_status
from resono_runtime.telephony.access import TelephonyAccess


class FakeBridge:
    def simPresent(self): return True
    def simState(self): return "LOADED"
    def carrierName(self): return "AT&T"
    def networkType(self): return "LTE"
    def signalLevel(self): return 3
    def voiceRegistered(self): return True
    def callState(self): return "IDLE"


def test_registered_tool_returns_snapshot_end_to_end():
    catalog = ToolCatalog()
    register_telephony_status(catalog, TelephonyAccess(FakeBridge()))
    result = catalog.invoke("get_phone_status", {})
    assert result is not None and result.is_error is False
