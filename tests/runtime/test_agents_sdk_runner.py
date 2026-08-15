from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from resono_runtime.agents import AgentsSdkTextRunner
from resono_runtime.api.events import RuntimeEventStream
from resono_runtime.providers.openai import OpenAIProviderError
from resono_runtime.security.credentials import ProviderCredentials
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.storage.provider_settings import ProviderSettingsRepository


class _CredentialBridge:
    def __init__(self, value: str | None) -> None:
        self.value = value

    def hasOpenAiPlatformKey(self) -> bool:
        return self.value is not None

    def getOpenAiPlatformKey(self) -> str | None:
        return self.value

    def putOpenAiPlatformKey(self, value: str) -> None:
        self.value = value

    def deleteOpenAiPlatformKey(self) -> None:
        self.value = None


class AgentsSdkTextRunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        database = RuntimeDatabase(Path(self.temporary.name) / "runtime.sqlite3")
        database.migrate()
        self.settings = ProviderSettingsRepository(database)
        self.events = RuntimeEventStream()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_turn_uses_selected_model_and_private_mcp_token(self) -> None:
        self.settings.save(text_model="gpt-5.4-mini", realtime_model=None)
        received: dict[str, str] = {}

        def execute(**values: str) -> str:
            received.update(values)
            return "The on-device runtime is ready."

        runner = AgentsSdkTextRunner(
            credentials=ProviderCredentials(_CredentialBridge("sk-test-private")),
            settings=self.settings,
            events=self.events,
            local_api_token="l" * 43,
            executor=execute,
        )

        result = runner.run("Check this device")

        self.assertEqual("gpt-5.4-mini", result.model)
        self.assertEqual("The on-device runtime is ready.", result.text)
        self.assertEqual("l" * 43, received["local_api_token"])
        self.assertEqual("sk-test-private", received["api_key"])
        self.assertEqual("none", received["reasoning_effort"])

    def test_missing_credential_and_model_fail_before_execution(self) -> None:
        unused = lambda **_: self.fail("executor must not run")
        runner = AgentsSdkTextRunner(
            credentials=ProviderCredentials(_CredentialBridge(None)),
            settings=self.settings,
            events=self.events,
            local_api_token="l" * 43,
            executor=unused,
        )
        with self.assertRaises(OpenAIProviderError) as missing_credential:
            runner.run("Hello")
        self.assertEqual("credential_unavailable", missing_credential.exception.code)

        runner = AgentsSdkTextRunner(
            credentials=ProviderCredentials(_CredentialBridge("sk-test-private")),
            settings=self.settings,
            events=self.events,
            local_api_token="l" * 43,
            executor=unused,
        )
        with self.assertRaises(OpenAIProviderError) as missing_model:
            runner.run("Hello")
        self.assertEqual("model_required", missing_model.exception.code)

    def test_subscription_path_uses_codex_base_url(self) -> None:
        self.settings.save(
            text_model="gpt-5.6-terra",
            realtime_model="gpt-realtime-2.1-mini",
            reasoning_effort="high",
        )
        self.settings.save_access_path("subscription")
        received: dict[str, object] = {}

        def execute(**values: object) -> str:
            received.update(values)
            return "Subscription response"

        subscription = type("Subscription", (), {"access_token": lambda self: "subscription-token"})()
        runner = AgentsSdkTextRunner(
            credentials=ProviderCredentials(_CredentialBridge(None)),
            settings=self.settings,
            events=self.events,
            local_api_token="l" * 43,
            subscription=subscription,
            executor=execute,
        )

        result = runner.run("Hello")

        self.assertEqual("Subscription response", result.text)
        self.assertEqual("https://chatgpt.com/backend-api/codex", received["base_url"])
        self.assertEqual("subscription-token", received["api_key"])
        self.assertEqual("high", received["reasoning_effort"])


if __name__ == "__main__":
    unittest.main()
