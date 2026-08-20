from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    root: Path
    local_api_token: str
    local_api_host: str = "127.0.0.1"
    local_api_port: int = 8765

    @classmethod
    def create(cls, root_path: str, local_api_token: str) -> "RuntimeConfig":
        root = Path(root_path)
        if not root.is_absolute():
            raise ValueError("runtime root must be absolute")
        if len(local_api_token) < 32:
            raise ValueError("local API token is invalid")
        return cls(root=root, local_api_token=local_api_token)

    @property
    def database_path(self) -> Path:
        return self.root / "data" / "resono.sqlite3"

    @property
    def workspace_path(self) -> Path:
        return self.root / "workspace"

    @property
    def logs_path(self) -> Path:
        return self.root / "logs"

    @property
    def runtime_log_path(self) -> Path:
        return self.logs_path / "resono-runtime.log"

    @property
    def releases_path(self) -> Path:
        return self.root / "releases"

    @property
    def skills_path(self) -> Path:
        return self.workspace_path / "skills"

    @property
    def skill_quarantine_path(self) -> Path:
        return self.workspace_path / "skill-quarantine"

    @property
    def skill_rollback_path(self) -> Path:
        return self.workspace_path / "skill-rollbacks"

    @property
    def plugins_path(self) -> Path:
        return self.workspace_path / "plugins"

    @property
    def plugin_quarantine_path(self) -> Path:
        return self.workspace_path / "plugin-quarantine"

    @property
    def plugin_rollback_path(self) -> Path:
        return self.workspace_path / "plugin-rollbacks"

    @property
    def creations_path(self) -> Path:
        return self.workspace_path / "creations"

    @property
    def creation_quarantine_path(self) -> Path:
        return self.workspace_path / "creation-quarantine"

    @property
    def creation_rollback_path(self) -> Path:
        return self.workspace_path / "creation-rollbacks"

    def prepare_directories(self) -> None:
        for path in (
            self.database_path.parent,
            self.workspace_path,
            self.logs_path,
            self.releases_path,
            self.skills_path,
            self.skill_quarantine_path,
            self.skill_rollback_path,
            self.plugins_path,
            self.plugin_quarantine_path,
            self.plugin_rollback_path,
            self.creations_path,
            self.creation_quarantine_path,
            self.creation_rollback_path,
        ):
            path.mkdir(parents=True, exist_ok=True)
