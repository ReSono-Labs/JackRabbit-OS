from __future__ import annotations
from typing import TYPE_CHECKING
from resono_runtime.domains.tasks import TaskRepository
if TYPE_CHECKING:
    from .routes import RouteRequest

class TaskRoutes:
    """Device-only read projection for the native Tasks Card."""
    def __init__(self, repository: TaskRepository) -> None: self._repository = repository
    def handle_get(self, request: "RouteRequest") -> bool:
        path = request.path.split("?", 1)[0]
        if path == "/v1/tasks/active":
            request.respond_json(200, {"tasks": [_view(item) for item in self._repository.list(limit=100)]})
            return True
        if path.startswith("/v1/tasks/"):
            item = self._repository.get(path.rsplit("/", 1)[-1])
            if item is None: request.respond_json(404, {"error": {"code": "task_not_found", "message": "Task not found."}})
            else: request.respond_json(200, _view(item))
            return True
        return False

def _view(item: object) -> dict[str, object]:
    return {"taskId": item.task_id, "text": item.text, "status": item.status}
