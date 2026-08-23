from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from resono_runtime.api.events import RuntimeEventStream
from resono_runtime.providers.controller import ProviderController
from resono_runtime.providers.openai.platform import OpenAIPlatform
from resono_runtime.providers.openai import ProviderModels
from resono_runtime.security.credentials import ProviderCredentials
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.provider_settings import ProviderSettingsRepository


class _CredentialBridge:
    def __init__(self) -> None:
        self.value: str | None = None
        self.subscription: str | None = None

    def hasOpenAiPlatformKey(self) -> bool:
        return self.value is not None

    def getOpenAiPlatformKey(self) -> str | None:
        return self.value

    def putOpenAiPlatformKey(self, value: str) -> None:
        self.value = value

    def deleteOpenAiPlatformKey(self) -> None:
        self.value = None

    def hasOpenAiSubscriptionTokens(self) -> bool:
        return self.subscription is not None

    def getOpenAiSubscriptionTokens(self) -> str | None:
        return self.subscription

    def putOpenAiSubscriptionTokens(self, value: str) -> None:
        self.subscription = value

    def deleteOpenAiSubscriptionTokens(self) -> None:
        self.subscription = None


class _OpenAI:
    def __init__(self, key: str, *, safety_source: str) -> None:
        self.key = key

    def list_models(self) -> ProviderModels:
        return ProviderModels(("gpt-5.4",), ("gpt-realtime-2.1",))

    def create_realtime_call(
        self,
        *,
        offer_sdp: str,
        model: str,
        instructions_extra: str = "",
        extra_tools: tuple = (),
        tool_definitions: tuple | None = None,
    ) -> str:
        if model not in ("gpt-realtime-2.1", "gpt-realtime-2.1-mini", "gpt-live-1"):
            raise AssertionError("unexpected model")
        return "v=0\r\nanswer"


class _SkillOpenAI(_OpenAI):
    instructions_extra = ""

    def create_realtime_call(self, *, offer_sdp: str, model: str, instructions_extra: str = "", **_: object) -> str:
        self.__class__.instructions_extra = instructions_extra
        return super().create_realtime_call(
            offer_sdp=offer_sdp,
            model=model,
            instructions_extra=instructions_extra,
        )


class OpenAIProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        database = RuntimeDatabase(Path(self.temporary.name) / "runtime.sqlite3")
        database.migrate()
        self.bridge = _CredentialBridge()
        self.settings = ProviderSettingsRepository(database)
        self.events = RuntimeEventStream()
        self.controller = ProviderController(
            credentials=ProviderCredentials(self.bridge),
            settings=self.settings,
            events=self.events,
            safety_source="local-install",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @patch("resono_runtime.providers.controller.OpenAIPlatform", _OpenAI)
    def test_connect_select_and_create_call_without_returning_secret(self) -> None:
        status = self.controller.connect_platform("sk-test-value-long-enough")

        self.assertTrue(status["connected"])
        self.assertNotIn("sk-test", str(status))
        self.assertEqual("gpt-realtime-2.1", status["selection"]["realtime"])
        self.assertEqual(
            "v=0\r\nanswer", self.controller.create_realtime_call("v=0\r\noffer").sdp
        )

    @patch("resono_runtime.providers.controller.OpenAIPlatform", _OpenAI)
    def test_rejects_model_not_reported_by_provider(self) -> None:
        self.controller.connect_platform("sk-test-value-long-enough")
        with self.assertRaisesRegex(RuntimeError, "available Realtime"):
            self.controller.select_models(text_model=None, realtime_model="made-up")

    @patch("resono_runtime.providers.controller.OpenAIPlatform", _SkillOpenAI)
    def test_realtime_receives_skill_disclosure_not_full_skill_body(self) -> None:
        controller = ProviderController(
            credentials=ProviderCredentials(self.bridge),
            settings=self.settings,
            events=self.events,
            safety_source="local-install",
            voice_skill_instructions=lambda: "Enabled Agent Skills:\n- planning: Plan meetings.",
        )
        controller.connect_platform("sk-test-value-long-enough")

        controller.create_realtime_call("v=0\r\noffer")

        self.assertIn("planning: Plan meetings.", _SkillOpenAI.instructions_extra)
        self.assertNotIn("Full private instructions", _SkillOpenAI.instructions_extra)

    @patch("resono_runtime.providers.controller.OpenAIPlatform", _OpenAI)
    def test_disconnect_removes_credential_and_selection(self) -> None:
        self.controller.connect_platform("sk-test-value-long-enough")
        status = self.controller.disconnect_platform()
        self.assertFalse(status["connected"])
        self.assertIsNone(self.bridge.value)
        self.assertIsNone(status["selection"]["realtime"])

    @patch("resono_runtime.providers.controller.OpenAIPlatform", _OpenAI)
    def test_subscription_access_has_bounded_models_and_powers_realtime(self) -> None:
        subscription = type(
            "Subscription",
            (),
            {
                "status": lambda self: {"connected": True},
                "access_token": lambda self: "subscription-token",
            },
        )()
        controller = ProviderController(
            credentials=ProviderCredentials(self.bridge),
            settings=self.settings,
            events=self.events,
            safety_source="local-install",
            subscription=subscription,
        )

        status = controller.select_access_path("subscription")

        self.assertEqual("subscription", status["accessPath"])
        self.assertEqual(
            ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"],
            status["models"]["text"],
        )
        self.assertEqual(
            ["gpt-realtime-2.1", "gpt-realtime-2.1-mini", "gpt-live-1"],
            status["models"]["realtime"],
        )
        self.assertEqual("gpt-realtime-2.1", status["selection"]["realtime"])
        self.assertEqual(
            "v=0\r\nanswer", controller.create_realtime_call("v=0\r\noffer").sdp
        )

    @patch("resono_runtime.providers.controller.OpenAIPlatform", _OpenAI)
    def test_status_repairs_a_persisted_model_removed_from_subscription_catalog(self) -> None:
        self.settings.save(text_model="old-text", realtime_model="old-realtime")
        self.settings.save_access_path("subscription")
        subscription = type(
            "Subscription",
            (),
            {"status": lambda self: {"connected": True}},
        )()
        controller = ProviderController(
            credentials=ProviderCredentials(self.bridge),
            settings=self.settings,
            events=self.events,
            safety_source="local-install",
            subscription=subscription,
        )

        status = controller.status()

        self.assertEqual("gpt-5.6-sol", status["selection"]["text"])
        self.assertEqual("gpt-realtime-2.1", status["selection"]["realtime"])

    @patch("resono_runtime.providers.controller.OpenAIPlatform", _OpenAI)
    def test_platform_connection_is_rejected_while_subscription_is_active(self) -> None:
        subscription = type(
            "Subscription",
            (),
            {
                "status": lambda self: {"connected": True},
                "access_token": lambda self: "subscription-token",
            },
        )()
        controller = ProviderController(
            credentials=ProviderCredentials(self.bridge),
            settings=self.settings,
            events=self.events,
            safety_source="local-install",
            subscription=subscription,
        )
        with self.assertRaisesRegex(RuntimeError, "Disconnect ChatGPT"):
            controller.connect_platform("sk-test-value-long-enough")

        status = controller.status()

        self.assertFalse(status["connections"]["platform"])
        self.assertTrue(status["connections"]["subscription"])
        self.assertEqual("subscription", status["accessPath"])
        self.assertEqual("gpt-5.6-sol", status["selection"]["text"])
        self.assertEqual("gpt-realtime-2.1", status["selection"]["realtime"])

    @patch("resono_runtime.providers.controller.OpenAIPlatform", _OpenAI)
    def test_disconnect_selected_subscription_falls_back_to_connected_platform(self) -> None:
        self.bridge.value = "sk-test-value-long-enough"
        connected = [True]
        subscription = type(
            "Subscription",
            (),
            {
                "status": lambda self: {"connected": connected[0]},
                "disconnect": lambda self: connected.__setitem__(0, False) or {"connected": False},
            },
        )()
        controller = ProviderController(
            credentials=ProviderCredentials(self.bridge),
            settings=self.settings,
            events=self.events,
            safety_source="local-install",
            subscription=subscription,
        )
        controller.select_access_path("subscription")

        result = controller.disconnect_subscription()
        status = controller.status()

        self.assertFalse(result["connected"])
        self.assertEqual("platform", status["accessPath"])
        self.assertTrue(status["connected"])
        self.assertEqual("gpt-5.4", status["selection"]["text"])
        self.assertEqual("gpt-realtime-2.1", status["selection"]["realtime"])


class OpenAIPlatformTest(unittest.TestCase):
    def test_platform_realtime_discovery_includes_live_realtime(self) -> None:
        platform = OpenAIPlatform("sk-test", safety_source="local")

        response = {
            "data": [
                {"id": "gpt-4o-mini"},
                {"id": "gpt-realtime-2.1"},
                {"id": "gpt-realtime-2.1-mini"},
                {"id": "gpt-live-1"},
                {"id": "text-embedding-3-small"},
            ]
        }

        with patch("resono_runtime.providers.openai.platform.urlopen") as request:
            request.return_value.__enter__.return_value.read.return_value = json.dumps(response).encode()
            models = platform.list_models()

        self.assertEqual(
            ("gpt-live-1", "gpt-realtime-2.1", "gpt-realtime-2.1-mini"),
            models.realtime,
        )
        self.assertEqual(("gpt-4o-mini",), models.text)


if __name__ == "__main__":
    unittest.main()
