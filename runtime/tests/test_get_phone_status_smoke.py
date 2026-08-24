from resono_runtime.tools import ToolCatalog, TelephonyToolPackage
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
    TelephonyToolPackage(TelephonyAccess(FakeBridge())).register(catalog)
    result = catalog.invoke("get_phone_status", {})
    assert result is not None and result.is_error is False
