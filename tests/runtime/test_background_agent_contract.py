from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from resono_runtime.background_agent import AgentRunRequest, InvocationType, WorkspacePolicy, WorkspaceSandbox
from resono_runtime.background_agent.workspace import WorkspaceViolation


class BackgroundAgentContractTest(unittest.TestCase):
    def test_request_requires_structured_goal_contract(self) -> None:
        request = AgentRunRequest(
            run_id="run-1",
            invocation_type=InvocationType.GOAL,
            origin_id="voice-session-1",
            objective="Prepare a bounded report.",
            instruction_profile="voice-goal-v1",
            success_criteria=("Report contains evidence.",),
            result_schema={"type": "object"},
            original_request="Prepare a bounded report.",
            verification_method="Inspect the report evidence.",
            completion_conditions=("The report is complete.",),
        )
        self.assertEqual("goal", request.invocation_type.value)

    def test_workspace_is_allowlisted_quota_bound_and_process_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sandbox = WorkspaceSandbox()
            workspace = sandbox.create(
                Path(temporary) / "run-1",
                WorkspacePolicy(
                    allowed_read=("notes/input.txt",),
                    allowed_write=("output/result.txt",),
                    max_files=1,
                    max_file_bytes=32,
                    max_total_bytes=32,
                ),
            )
            workspace.write_text("output/result.txt", "bounded result")
            self.assertEqual("bounded result", workspace.read_text("output/result.txt"))
            with self.assertRaises(WorkspaceViolation):
                workspace.write_text("../escape.txt", "no")
            with self.assertRaises(WorkspaceViolation):
                workspace.write_text("other.txt", "no")
            self.assertFalse(sandbox.supports_process_execution)


if __name__ == "__main__":
    unittest.main()
