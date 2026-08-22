from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from resono_runtime.providers.openai.web_search import OpenAIWebSearch


class WebSearchTest(unittest.TestCase):
    @patch("resono_runtime.providers.openai.web_search._run_search", new_callable=AsyncMock)
    def test_platform_uses_agents_sdk_search(self, run_search) -> None:
        run_search.return_value = _result()
        result = OpenAIWebSearch(_Credentials(), _Settings("platform"), None).search(" current  information ")
        run_search.assert_awaited_once_with(query="current information", api_key="platform-key", base_url=None)
        self.assertEqual("https://example.com/source", result["citations"][0]["url"])

    @patch("resono_runtime.providers.openai.web_search._run_search", new_callable=AsyncMock)
    def test_subscription_uses_canonical_codex_access(self, run_search) -> None:
        run_search.return_value = _result()
        result = OpenAIWebSearch(_Credentials(), _Settings("subscription"), _Subscription()).search("today")
        run_search.assert_awaited_once_with(
            query="today",
            api_key="subscription-token",
            base_url="https://chatgpt.com/backend-api/codex",
        )
        self.assertEqual("Answer", result["answer"])

    @patch("resono_runtime.providers.openai.web_search._run_search", new_callable=AsyncMock)
    def test_consecutive_searches_create_independent_sdk_runs(self, run_search) -> None:
        run_search.return_value = _result()
        search = OpenAIWebSearch(_Credentials(), _Settings("platform"), None)
        self.assertEqual("Answer", search.search("first")["answer"])
        self.assertEqual("Answer", search.search("second")["answer"])
        self.assertEqual(2, run_search.await_count)

    @patch("resono_runtime.providers.openai.web_search._run_search", new_callable=AsyncMock)
    def test_provider_failure_is_truthful(self, run_search) -> None:
        error = type("ProviderError", (RuntimeError,), {"status_code": 401})("denied")
        run_search.side_effect = error
        with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
            OpenAIWebSearch(_Credentials(), _Settings("platform"), None).search("today")


class _Credentials:
    def platform_key(self) -> str:
        return "platform-key"


class _Subscription:
    def access_token(self) -> str:
        return "subscription-token"


class _Settings:
    def __init__(self, access_path: str) -> None:
        self._selection = SimpleNamespace(access_path=access_path, text_model="gpt-test")

    def selection(self):
        return self._selection


def _result() -> dict[str, object]:
    return {
        "query": "query",
        "answer": "Answer",
        "citations": [{"title": "Source", "url": "https://example.com/source"}],
        "responseId": "resp_1",
    }


if __name__ == "__main__":
    unittest.main()
