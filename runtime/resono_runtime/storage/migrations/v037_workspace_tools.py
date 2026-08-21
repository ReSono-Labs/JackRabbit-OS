from __future__ import annotations

import json
import sqlite3


_TOOLS = (
    "workspace_list", "workspace_read", "run_workspace_list",
    "run_workspace_read", "run_workspace_write", "workspace_publish",
)


def apply(connection: sqlite3.Connection) -> None:
    row = connection.execute(
        "SELECT allowed_tool_names_json FROM background_agent_settings WHERE settings_id = 1"
    ).fetchone()
    if row is None:
        return
    current = json.loads(str(row[0]))
    names = sorted(set(item for item in current if isinstance(item, str)) | set(_TOOLS))
    connection.execute(
        "UPDATE background_agent_settings SET allowed_tool_names_json = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE settings_id = 1",
        (json.dumps(names, separators=(",", ":")),),
    )
