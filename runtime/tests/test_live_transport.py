import unittest

from resono_runtime.providers.openai.live_transport import (
    LIVE_CODEX_MODEL,
    LiveRealtimeStart,
    codex_realtime_model,
    is_live_model,
)


class LiveTransportTest(unittest.TestCase):
    def test_live_model_uses_codex_internal_alias(self):
        self.assertTrue(is_live_model("gpt-live-1"))
        self.assertEqual(LIVE_CODEX_MODEL, codex_realtime_model("gpt-live-1"))

    def test_live_start_builds_webrtc_broker_payload(self):
        payload = LiveRealtimeStart("webrtc", "v=0\r\n").payload()
        self.assertEqual("v=0\r\n", payload["sdp"])
        self.assertEqual(LIVE_CODEX_MODEL, payload["session"]["model"])
        self.assertEqual("client", payload["session"]["delegation"]["type"])
        self.assertEqual("sol", payload["session"]["audio"]["output"]["voice"])

    def test_live_broker_uses_codex_endpoint_and_internal_model(self):
        from resono_runtime.providers.openai import live_transport

        captured = {}

        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, _limit): return b"v=0\r\n"

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = request.data
            # urllib canonicalizes header names (e.g. OpenAI-Alpha -> Openai-alpha),
            # so look headers up case-insensitively.
            headers = {key.lower(): value for key, value in request.headers.items()}
            captured["auth"] = headers.get("authorization")
            captured["alpha"] = headers.get("openai-alpha")
            return Response()

        original = live_transport.urlopen
        live_transport.urlopen = fake_urlopen
        try:
            answer = live_transport.create_codex_live_call(
                access_token="oauth-token",
                offer_sdp="v=0\r\n",
                thread_id="thread-1",
            )
        finally:
            live_transport.urlopen = original
        self.assertEqual("v=0", answer)
        self.assertIn("chatgpt.com/backend-api/codex/realtime/calls", captured["url"])
        self.assertIn("intent=quicksilver&architecture=avas", captured["url"])
        self.assertEqual("Bearer oauth-token", captured["auth"])
        self.assertEqual("quicksilver=v2", captured["alpha"])
        body = captured["body"].decode()
        self.assertIn("gpt-live-1-codex", body)
        self.assertIn('"type":"client"', body)

    def test_live_broker_error_includes_response_body(self):
        from resono_runtime.providers.openai import live_transport
        from urllib.error import HTTPError

        def fake_urlopen(_request, timeout):
            raise HTTPError(
                "https://chatgpt.com/backend-api/codex/realtime/calls?intent=quicksilver&architecture=avas",
                403,
                "forbidden",
                {},
                __import__("io").BytesIO(b'{"error":"missing account"}'),
            )

        original = live_transport.urlopen
        live_transport.urlopen = fake_urlopen
        try:
            with self.assertRaisesRegex(RuntimeError, "missing account"):
                live_transport.create_codex_live_call(
                    access_token="oauth-token",
                    offer_sdp="v=0\r\n",
                    thread_id="thread-1",
                )
        finally:
            live_transport.urlopen = original

    def test_live_rejects_invalid_sdp(self):
        with self.assertRaises(ValueError):
            LiveRealtimeStart("webrtc", "not-an-sdp").payload()

    def test_product_live_call_uses_wm_multipart_and_sol_voice(self):
        from resono_runtime.providers.openai import live_transport

        captured = {}

        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, _limit): return b"v=0\r\no=- 1 1 IN IP4 0.0.0.0\r\n"

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["body"] = request.data
            headers = {key.lower(): value for key, value in request.headers.items()}
            captured["content_type"] = headers.get("content-type")
            captured["auth"] = headers.get("authorization")
            return Response()

        original = live_transport.urlopen
        live_transport.urlopen = fake_urlopen
        try:
            answer = live_transport.create_product_live_call(
                access_token="oauth-token",
                offer_sdp="v=0\r\n",
                instructions="Be concise.",
            )
        finally:
            live_transport.urlopen = original

        self.assertEqual("v=0", answer[:3])
        self.assertIn("chatgpt.com/realtime/wm", captured["url"])
        self.assertTrue(captured["content_type"].startswith("multipart/form-data"))
        self.assertEqual("Bearer oauth-token", captured["auth"])
        body = captured["body"].decode()
        self.assertIn('"voice":"Sol"', body)
        self.assertIn('"voice_status_request_id"', body)
        self.assertIn("Be concise.", body)


if __name__ == "__main__":
    unittest.main()
