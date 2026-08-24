import json

from resono_runtime.tools import ToolCatalog, TelephonyToolPackage
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
    TelephonyToolPackage(TelephonyAccess(FakeBridge())).register(catalog)
    result = catalog.invoke("get_phone_status", {})
    assert result.is_error is False
    body = json.loads(result.text)
    assert body["carrierName"] == "AT&T"
    assert body["voiceRegistered"] is True


def test_telephony_package_registers_exact_contract_set():
    catalog = ToolCatalog()
    package = TelephonyToolPackage(TelephonyAccess(FakeBridge()))
    package.register(catalog)
    definitions = package.definitions()
    assert len(definitions) == 1
    assert definitions[0].name == "get_phone_status"
    assert definitions[0].tool_id == "builtin.telephony.get_phone_status.v1"
    assert definitions[0].effect_class == "read"
