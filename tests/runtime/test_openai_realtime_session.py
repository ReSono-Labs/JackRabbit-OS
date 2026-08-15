from __future__ import annotations

import unittest

from resono_runtime.providers.openai.platform import _realtime_session


class OpenAIRealtimeSessionTest(unittest.TestCase):
    def test_session_matches_proven_r1_voice_audio_contract(self) -> None:
        session = _realtime_session("gpt-realtime-2.1-mini")

        self.assertEqual(["audio"], session["output_modalities"])
        audio = session["audio"]
        self.assertEqual({"type": "audio/pcm", "rate": 24_000}, audio["input"]["format"])
        self.assertEqual({"type": "near_field"}, audio["input"]["noise_reduction"])
        self.assertEqual(
            {"model": "gpt-4o-mini-transcribe"}, audio["input"]["transcription"]
        )
        self.assertEqual(
            {
                "type": "server_vad",
                "create_response": True,
                "interrupt_response": False,
                "threshold": 0.92,
                "prefix_padding_ms": 500,
                "silence_duration_ms": 1_200,
            },
            audio["input"]["turn_detection"],
        )
        self.assertEqual(
            {"format": {"type": "audio/pcm", "rate": 24_000}, "voice": "marin"},
            audio["output"],
        )
        self.assertEqual("auto", session["tool_choice"])


if __name__ == "__main__":
    unittest.main()
