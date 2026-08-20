from __future__ import annotations
from dataclasses import dataclass

TASKS_PACKAGE_VERSION = 1

@dataclass(frozen=True, slots=True)
class TaskToolContract:
    name: str
    description: str
    effect_class: str
    input_schema: dict[str, object]

def contracts() -> tuple[TaskToolContract, ...]:
    task_id = {"taskId": {"type": "string"}}
    return (
        TaskToolContract("tasks_list", "List local tasks, open by default.", "read", _schema({"includeCompleted": {"type": "boolean"}, "limit": {"type": "integer", "minimum": 1, "maximum": 100}})),
        TaskToolContract("tasks_read", "Read one local task.", "read", _schema(task_id, ("taskId",))),
        TaskToolContract("tasks_add", "Prepare a text task. Read it back and ask before confirming.", "local_write", _schema({"text": {"type": "string"}}, ("text",))),
        TaskToolContract("tasks_edit", "Prepare replacement task text. Read it back and ask before confirming.", "local_write", _schema({**task_id, "text": {"type": "string"}}, ("taskId", "text"))),
        TaskToolContract("tasks_mark_completed", "Prepare marking a task completed. Ask before confirming.", "local_write", _schema(task_id, ("taskId",))),
        TaskToolContract("tasks_remove", "Prepare permanent removal of a task. Ask before confirming.", "local_write", _schema(task_id, ("taskId",))),
        TaskToolContract("tasks_confirm_action", "Execute one unchanged reviewed Task action after explicit approval within ten minutes.", "local_write", _schema({"actionId": {"type": "string"}, "contentHash": {"type": "string"}}, ("actionId", "contentHash"))),
    )

def _schema(properties: dict[str, object], required: tuple[str, ...] = ()) -> dict[str, object]:
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}
