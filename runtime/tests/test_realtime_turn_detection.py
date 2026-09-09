import pytest

from resono_runtime.providers.openai.platform import _realtime_session


@pytest.mark.parametrize(
    "model", ("gpt-realtime-2.1", "gpt-realtime-2.1-mini", "gpt-live-1")
)
def test_realtime_session_keeps_vad_boundaries_with_client_owned_responses(model):
    session = _realtime_session(model)

    assert session["model"] == model
    assert session["audio"] == {
        "input": {
            "format": {"type": "audio/pcm", "rate": 24_000},
            "noise_reduction": {"type": "near_field"},
            "transcription": {"model": "gpt-4o-mini-transcribe"},
            "turn_detection": {
                "type": "server_vad",
                "create_response": False,
                "interrupt_response": True,
                "threshold": 0.92,
                "prefix_padding_ms": 500,
                "silence_duration_ms": 1_200,
            },
        },
        "output": {
            "format": {"type": "audio/pcm", "rate": 24_000},
            "voice": "marin",
        },
    }
