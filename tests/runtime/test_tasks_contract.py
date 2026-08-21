from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from resono_runtime.agents import AgentKind
from resono_runtime.domains.tasks import TaskRepository, TaskService
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.tools import ToolCatalog, ToolInvocationContext, ToolInvocationResult
from resono_runtime.tools.tasks import TasksToolPackage


class TasksContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.database = RuntimeDatabase(Path(self.temp.name) / "runtime.sqlite3")
        self.database.migrate()
        self.repository = TaskRepository(self.database)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_complete_uniform_voice_package(self) -> None:
        catalog = ToolCatalog()
        TasksToolPackage(_ToolService()).register(catalog)
        self.assertEqual(
            {"tasks_list", "tasks_read", "tasks_add", "tasks_edit",
             "tasks_mark_completed", "tasks_remove", "tasks_confirm_action"},
            {item["name"] for item in catalog.mcp_definitions(AgentKind.VOICE)},
        )

    def test_task_schema_has_no_schedule_fields(self) -> None:
        with self.database.connect() as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(tasks)")}
        self.assertEqual(
            {"task_id", "task_text", "status", "created_at", "updated_at", "completed_at"},
            columns,
        )

    def test_confirmation_uses_trusted_turn_order_not_a_phrase_allowlist(self) -> None:
        for index, approval in enumerate((
            "Yeah, go ahead and save that.",
            "Yes, approved.",
            "Yeah, it's, yes.",
            "OK, good.",
            "Approved.",
        )):
            service = TaskService(self.repository)
            prepared = service.invoke_tool(
                "tasks_add",
                ToolInvocationContext(AgentKind.VOICE, "voice-session", f"prepare-{index}", "Create it", 1),
                {"text": f"Task {index}"},
            )
            action = prepared.structured_content["result"]
            confirmed = service.invoke_tool(
                "tasks_confirm_action",
                ToolInvocationContext(AgentKind.VOICE, "voice-session", f"confirm-{index}", approval, 2),
                {"actionId": action["actionId"], "contentHash": action["contentHash"]},
            )
            self.assertFalse(confirmed.is_error, approval)

    def test_confirmation_still_rejects_the_prepare_utterance(self) -> None:
        service = TaskService(self.repository)
        prepared = service.invoke_tool(
            "tasks_add",
            ToolInvocationContext(AgentKind.VOICE, "voice-session", "prepare", "Create it", 4),
            {"text": "Unapproved task"},
        )
        action = prepared.structured_content["result"]
        confirmed = service.invoke_tool(
            "tasks_confirm_action",
            ToolInvocationContext(AgentKind.VOICE, "voice-session", "confirm", "Approved", 4),
            {"actionId": action["actionId"], "contentHash": action["contentHash"]},
        )
        self.assertTrue(confirmed.is_error)


class _ToolService:
    def invoke_tool(self, name, context, arguments):
        return ToolInvocationResult("ok")


if __name__ == "__main__":
    unittest.main()
