from __future__ import annotations

import json
import unittest

from resono_runtime.providers.openai.subscription import OpenAISubscription
from resono_runtime.security.credentials import ProviderCredentials


class _CredentialBridge:
    def __init__(self) -> None:
        self.platform: str | None = None
        self.subscription: str | None = None

    def hasOpenAiPlatformKey(self) -> bool:
        return self.platform is not None

    def getOpenAiPlatformKey(self) -> str | None:
        return self.platform

    def putOpenAiPlatformKey(self, value: str) -> None:
        self.platform = value

    def deleteOpenAiPlatformKey(self) -> None:
        self.platform = None

    def hasOpenAiSubscriptionTokens(self) -> bool:
        return self.subscription is not None

    def getOpenAiSubscriptionTokens(self) -> str | None:
        return self.subscription

    def putOpenAiSubscriptionTokens(self, value: str) -> None:
        self.subscription = value

    def deleteOpenAiSubscriptionTokens(self) -> None:
        self.subscription = None


class OpenAISubscriptionTest(unittest.TestCase):
    def test_device_flow_pending_completion_refresh_and_disconnect(self) -> None:
        now = [1_000]
        bridge = _CredentialBridge()
        token_polls = [
            (403, {}),
            (200, {"authorization_code": "authorization", "code_verifier": "verifier"}),
        ]
        token_requests: list[tuple[dict[str, str], bool]] = []

        def device_transport(url: str, payload: dict):
            if url.endswith("/deviceauth/usercode"):
                self.assertEqual({"client_id": "app_EMoamEEZ73f0CkXaXp7hrann"}, payload)
                return 200, {"device_auth_id": "device-1", "user_code": "ABCD-EFGH", "interval": 1}
            return token_polls.pop(0)

        def token_transport(url: str, payload: dict[str, str], refresh: bool):
            self.assertEqual("https://auth.openai.com/oauth/token", url)
            token_requests.append((payload, refresh))
            if refresh:
                return {"access_token": "refreshed", "expires_in": 3600}
            return {"access_token": "connected", "refresh_token": "refresh", "expires_in": 600}

        subscription = OpenAISubscription(
            ProviderCredentials(bridge),
            clock=lambda: now[0],
            device_transport=device_transport,
            token_transport=token_transport,
        )

        started = subscription.start_auth()
        self.assertEqual("ABCD-EFGH", started.user_code)
        self.assertEqual("https://auth.openai.com/codex/device", started.verification_url)
        self.assertEqual("auth_pending", subscription.poll_auth(started.auth_session_id)["status"])
        completed = subscription.poll_auth(started.auth_session_id)
        self.assertEqual("completed", completed["status"])
        self.assertTrue(subscription.status()["connected"])
        self.assertNotIn("access_token", str(subscription.status()))
        self.assertFalse(token_requests[0][1])
        self.assertEqual("https://auth.openai.com/deviceauth/callback", token_requests[0][0]["redirect_uri"])

        now[0] = 1_400
        self.assertEqual("refreshed", subscription.access_token())
        stored = json.loads(bridge.subscription or "{}")
        self.assertEqual("refresh", stored["refresh_token"])
        self.assertTrue(token_requests[1][1])

        self.assertFalse(subscription.disconnect()["connected"])
        self.assertIsNone(bridge.subscription)


if __name__ == "__main__":
    unittest.main()
