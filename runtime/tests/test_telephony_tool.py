import json

from resono_runtime.tools import ToolCatalog, register_telephony_status
from resono_runtime.telephony.access import TelephonyAccess


class FakeBridge:
    def simPresent(self): return True
    def simState(self): return "LOADED"
    def carrierName(self): return "AT&T"
    def networkType(self): return "LTE"
    def signalLevel(self): return 2
    def voiceRegistered(self): return True
    def callState(self): return "IDLE"


def test_get_phone_status_registers_and_returns_snapshot():
    catalog = ToolCatalog()
    register_telephony_status(catalog, TelephonyAccess(FakeBridge()))
    result = catalog.invoke("get_phone_status", {})
    assert result.is_error is False
    body = json.loads(result.text)
    assert body["carrierName"] == "AT&T"
    assert body["voiceRegistered"] is True
