from __future__ import annotations

import json
from resono_runtime.tools import ToolInvocationContext, ToolInvocationResult
from .models import Task
from .repository import TaskRepository


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def invoke_tool(self, name: str, context: ToolInvocationContext,
                    arguments: dict[str, object]) -> ToolInvocationResult:
        try:
            if name == "tasks_list":
                value: object = [_view(item) for item in self._repository.list(
                    include_completed=bool(arguments.get("includeCompleted", False)),
                    limit=_limit(arguments))]
            elif name == "tasks_read":
                item = self._repository.get(_required(arguments, "taskId"))
                if item is None:
                    raise ValueError("Task was not found.")
                value = _view(item)
            elif name == "tasks_confirm_action":
                value = self._confirm(context, arguments)
            else:
                value = self._prepare(name, context, arguments)
            return ToolInvocationResult(json.dumps(value, separators=(",", ":")), {"result": value})
        except (ValueError, RuntimeError) as error:
            return ToolInvocationResult(str(error), is_error=True)

    def _prepare(self, name: str, context: ToolInvocationContext,
                 arguments: dict[str, object]) -> dict[str, object]:
        operation = {"tasks_add": "add", "tasks_edit": "edit",
                     "tasks_mark_completed": "complete", "tasks_remove": "remove"}.get(name)
        if operation is None:
            raise ValueError("Task tool is unavailable.")
        payload: dict[str, object] = {}
        if operation in {"add", "edit"}:
            payload["text"] = _required(arguments, "text")
        return self._repository.prepare(
            operation=operation, task_id=_optional(arguments, "taskId"), payload=payload,
            voice_session_id=context.voice_session_id or "", tool_call_id=context.tool_call_id or "",
            utterance_id=context.user_utterance_id or 0)

    def _confirm(self, context: ToolInvocationContext,
                 arguments: dict[str, object]) -> dict[str, object]:
        action_id = _required(arguments, "actionId")
        claim = self._repository.claim(
            action_id=action_id, content_hash=_required(arguments, "contentHash"),
            voice_session_id=context.voice_session_id or "",
            approval_utterance_id=context.user_utterance_id or 0)
        try:
            item = self._repository.execute(claim)
        except Exception:
            self._repository.finish(action_id, completed=False)
            raise
        self._repository.finish(action_id, completed=True)
        return {"state": "completed", "actionId": action_id,
                "task": _view(item) if item is not None else None}


def _view(item: Task) -> dict[str, object]:
    return {"taskId": item.task_id, "text": item.text, "status": item.status,
            "createdAt": item.created_at, "updatedAt": item.updated_at,
            "completedAt": item.completed_at}


def _required(value: dict[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{key} is required.")
    return item.strip()


def _optional(value: dict[str, object], key: str) -> str | None:
    item = value.get(key)
    return item.strip() if isinstance(item, str) and item.strip() else None


def _limit(value: dict[str, object]) -> int:
    item = value.get("limit", 25)
    return max(1, min(item, 100)) if isinstance(item, int) and not isinstance(item, bool) else 25
