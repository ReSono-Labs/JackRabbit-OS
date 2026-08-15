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
    def releases_path(self) -> Path:
        return self.root / "releases"

    def prepare_directories(self) -> None:
        for path in (self.database_path.parent, self.workspace_path, self.releases_path):
            path.mkdir(parents=True, exist_ok=True)
