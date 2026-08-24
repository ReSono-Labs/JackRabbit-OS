import json

from resono_runtime.agents.audience import AgentKind
from resono_runtime.telephony.access import TelephonyAccess
from resono_runtime.tools import ToolCatalog, TelephonyToolPackage
from resono_runtime.tools.definitions import ToolInvocationContext


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
    def placeCall(self, number): self.calls.append(number); return True
    def sendSms(self, to, text): self.sms.append((to, text)); return True


def build(bridge=None):
    bridge = bridge or RecordingBridge()
    catalog = ToolCatalog()
    TelephonyToolPackage(TelephonyAccess(bridge)).register(catalog)
    return catalog, bridge


def invoke(catalog, name, arguments, utterance):
    context = ToolInvocationContext(agent=AgentKind.VOICE, user_utterance=utterance)
    return catalog.invoke(name, arguments, agent=AgentKind.VOICE, context=context)


def test_place_call_creates_pending_and_does_not_dial():
    catalog, bridge = build()
    r = invoke(catalog, "place_call", {"number": "5559876543"}, "call it")
    assert r.is_error is False
    assert bridge.calls == []
    assert "confirm" in r.text.lower()
    assert r.structured_content["kind"] == "call"


def test_confirm_call_executes_on_matching_utterance():
    catalog, bridge = build()
    first = invoke(catalog, "place_call", {"number": "5559876543"}, "call 555-987-6543")
    aid = first.structured_content["pendingActionId"]
    c = invoke(catalog, "confirm_action", {"id": aid}, "call 555-987-6543")
    assert c.is_error is False
    assert c.structured_content["ok"] is True
    assert bridge.calls == ["5559876543"]


def test_confirm_replay_is_rejected():
    catalog, bridge = build()
    first = invoke(catalog, "place_call", {"number": "5559876543"}, "call x")
    aid = first.structured_content["pendingActionId"]
    assert invoke(catalog, "confirm_action", {"id": aid}, "call x").structured_content["ok"] is True
    assert invoke(catalog, "confirm_action", {"id": aid}, "call x").is_error is True
    assert bridge.calls == ["5559876543"]


def test_confirm_wrong_utterance_is_rejected():
    catalog, bridge = build()
    first = invoke(catalog, "place_call", {"number": "5559876543"}, "call mom")
    aid = first.structured_content["pendingActionId"]
    assert invoke(catalog, "confirm_action", {"id": aid}, "text grandma").is_error is True
    assert bridge.calls == []


def test_confirm_missing_or_unknown_action_rejected():
    catalog, _ = build()
    assert invoke(catalog, "confirm_action", {"id": "doesnotexist"}, "call x").is_error is True


def test_send_sms_confirm_sends_exact_text():
    catalog, bridge = build()
    first = invoke(catalog, "send_sms", {"to": "5559876543", "text": "hello jack"}, "text jack hello")
    aid = first.structured_content["pendingActionId"]
    c = invoke(catalog, "confirm_action", {"id": aid}, "text jack hello")
    assert c.structured_content["ok"] is True
    assert ("5559876543", "hello jack") in bridge.sms
