from __future__ import annotations

import json
import unittest

from resono_runtime.handoff.inspection import _response


class HandoffInspectionResponseTest(unittest.TestCase):
    def test_subscription_accepts_completed_json_response(self) -> None:
        completed = {"id": "resp_json", "output_text": "Visible image details"}
        self.assertEqual(
            completed,
            _response(json.dumps(completed).encode(), "application/json", streaming=True),
        )

    def test_subscription_accepts_completed_event_stream(self) -> None:
        completed = {"id": "resp_sse", "output_text": "Visible image details"}
        event = {"type": "response.completed", "response": completed}
        body = f"data: {json.dumps(event)}\n\ndata: [DONE]\n\n".encode()
        self.assertEqual(completed, _response(body, "text/event-stream", streaming=True))


if __name__ == "__main__":
    unittest.main()
