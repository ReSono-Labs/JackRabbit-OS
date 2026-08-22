"""Installs the platform-owned Background Agent rules document."""

from __future__ import annotations

from pathlib import Path

from ..workspace.service import DurableWorkspace


RULES_REFERENCE = "workspace://documents/RULES.md"


def install_background_rules(workspace: DurableWorkspace, destination: Path) -> None:
    payload = Path(__file__).with_name("RULES.md").read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.is_file() or destination.read_bytes() != payload:
        destination.write_bytes(payload)
    workspace.register_managed(
        destination,
        RULES_REFERENCE,
        media_type="text/markdown",
        artifact_role="background_agent_rules",
    )
