from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Task:
    task_id: str
    text: str
    status: str
    created_at: str
    updated_at: str
    completed_at: str | None
