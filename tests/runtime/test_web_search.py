from __future__ import annotations

import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from resono_runtime.providers.openai.web_search import OpenAIWebSearch


class WebSearchTest(unittest.TestCase):
    @patch("resono_runtime.providers.openai.web_search.urlopen")
    def test_platform_uses_json_responses_with_citations(self, open_url) -> None:
        open_url.return_value = _Response(json.dumps(_completed()).encode(), "application/json")
        search = OpenAIWebSearch(_Credentials(), _Settings("platform"), None)
        result = search.search("current information")
        request = open_url.call_args.args[0]
        self.assertEqual("https://api.openai.com/v1/responses", request.full_url)
        self.assertNotIn("stream", json.loads(request.data))
        self.assertEqual("https://example.com/source", result["citations"][0]["url"])

    @patch("resono_runtime.providers.openai.web_search.urlopen")
    def test_subscription_uses_codex_streaming_responses(self, open_url) -> None:
        event = {"type": "response.completed", "response": _completed()}
        open_url.return_value = _Response(f"data: {json.dumps(event)}\n\ndata: [DONE]\n\n".encode(), "text/event-stream")
        search = OpenAIWebSearch(_Credentials(), _Settings("subscription"), _Subscription())
        result = search.search("today")
        request = open_url.call_args.args[0]
        self.assertEqual("https://chatgpt.com/backend-api/codex/responses", request.full_url)
        self.assertTrue(json.loads(request.data)["stream"])
        self.assertEqual("Answer", result["answer"])

    @patch("resono_runtime.providers.openai.web_search.urlopen", side_effect=URLError("offline"))
    def test_timeout_or_network_failure_is_truthful(self, _open_url) -> None:
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            OpenAIWebSearch(_Credentials(), _Settings("platform"), None).search("today")

    @patch("resono_runtime.providers.openai.web_search.urlopen", side_effect=HTTPError("https://api.openai.com", 401, "denied", {}, None))
    def test_revoked_or_denied_credential_is_truthful(self, _open_url) -> None:
        with self.assertRaisesRegex(RuntimeError, "rejected"):
            OpenAIWebSearch(_Credentials(), _Settings("platform"), None).search("today")

    def test_missing_model_is_unavailable(self) -> None:
        search = OpenAIWebSearch(_Credentials(), _Settings("platform", model=None), None)
        self.assertFalse(search.available())
        with self.assertRaisesRegex(ValueError, "Choose a text model"):
            search.search("today")


class _Credentials:
    def platform_key(self) -> str:
        return "platform-key"


class _Subscription:
    def access_token(self) -> str:
        return "subscription-token"


class _Settings:
    def __init__(self, access_path: str, model: str | None = "gpt-test") -> None:
        self._selection = SimpleNamespace(access_path=access_path, text_model=model)

    def selection(self):
        return self._selection


class _Headers:
    def __init__(self, content_type: str) -> None:
        self._content_type = content_type

    def get_content_type(self) -> str:
        return self._content_type


class _Response:
    def __init__(self, body: bytes, content_type: str) -> None:
        self._body = body
        self.headers = _Headers(content_type)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit: int) -> bytes:
        return self._body


def _completed() -> dict[str, object]:
    return {
        "id": "resp_1",
        "output": [{
            "type": "message",
            "content": [{
                "type": "output_text",
                "text": "Answer",
                "annotations": [{"type": "url_citation", "title": "Source", "url": "https://example.com/source"}],
            }],
        }],
    }


if __name__ == "__main__":
    unittest.main()
