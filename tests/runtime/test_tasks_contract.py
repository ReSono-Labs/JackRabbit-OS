from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from resono_runtime.agents import AgentKind
from resono_runtime.domains.tasks import TaskRepository
from resono_runtime.storage.database import RuntimeDatabase
from resono_runtime.tools import ToolCatalog, ToolInvocationResult
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


class _ToolService:
    def invoke_tool(self, name, context, arguments):
        return ToolInvocationResult("ok")


if __name__ == "__main__":
    unittest.main()
