"""Install shipped standard Plugins through the public Plugin lifecycle."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

from ..agents import AgentAudience
from ..storage.plugins import PluginCatalogRepository
from .archives import PluginArchiveInspector
from .lifecycle import PluginLifecycle


class BundledPluginInstaller:
    def __init__(
        self,
        lifecycle: PluginLifecycle,
        catalog: PluginCatalogRepository,
        inspector: PluginArchiveInspector,
    ) -> None:
        self._lifecycle = lifecycle
        self._catalog = catalog
        self._inspector = inspector

    def install_once(self, root: Path) -> None:
        name = root.name
        if self._catalog.get(name) is not None or self._catalog.was_removed(name):
            return
        inspection = self._inspector.inspect(_archive(root), f"{name}.zip")
        preflight = self._lifecycle.preflight(inspection, audience=AgentAudience.VOICE)
        installed = self._lifecycle.confirm(
            preflight.token,
            replace=False,
            changed_by="runtime-bootstrap",
            reason="install bundled standard Plugin",
        )
        self._lifecycle.enable(
            installed.name,
            changed_by="runtime-bootstrap",
            reason="enable bundled standard Plugin",
        )


def _archive(root: Path) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(root.rglob("*")):
            if source.is_file():
                archive.write(source, (Path(root.name) / source.relative_to(root)).as_posix())
    return buffer.getvalue()
