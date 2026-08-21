from __future__ import annotations

import json
import sqlite3


_BUILT_IN_RESOURCE_IDS = ("calendar", "device-status", "mail", "memory", "tasks", "web-search")
_BUILT_IN_TOOL_NAMES = (
    "get_device_status", "memory_lookup", "web_search",
    "email_account_status", "email_list_folders", "email_check", "email_get_unread",
    "email_search", "email_read", "email_read_attachment", "email_contact_lookup",
    "email_mark_read", "email_mark_unread", "email_compose", "email_send_pending",
    "email_archive", "email_create_folder", "email_rename_folder", "email_move_message",
    "calendar_list_upcoming", "calendar_search", "calendar_read_event",
    "calendar_create_event", "calendar_update_event", "calendar_delete_event",
    "calendar_confirm_action", "tasks_list", "tasks_read", "tasks_add", "tasks_edit",
    "tasks_mark_completed", "tasks_remove", "tasks_confirm_action",
)


def apply(connection: sqlite3.Connection) -> None:
    placeholders = ",".join("?" for _ in _BUILT_IN_RESOURCE_IDS)
    rows = connection.execute(
        f"SELECT resource_kind, resource_id, audience FROM agent_audience_bindings WHERE resource_id IN ({placeholders})",
        _BUILT_IN_RESOURCE_IDS,
    ).fetchall()
    timestamp = connection.execute("SELECT strftime('%Y-%m-%dT%H:%M:%fZ', 'now')").fetchone()[0]
    for resource_kind, resource_id, previous in rows:
        if previous == "both":
            continue
        connection.execute(
            """INSERT INTO agent_audience_audit(
                   resource_kind, resource_id, previous_audience, new_audience,
                   action, changed_at, changed_by, change_reason
               ) VALUES (?, ?, ?, 'both', 'set', ?, 'migration-v035',
                         'enable built-in tools for Voice and Background Agent')""",
            (resource_kind, resource_id, previous, timestamp),
        )
    connection.execute(
        f"UPDATE agent_audience_bindings SET audience = 'both', active = 1, changed_at = ?, "
        f"changed_by = 'migration-v035', change_reason = 'enable built-in tools for Voice and Background Agent' "
        f"WHERE resource_id IN ({placeholders})",
        (timestamp, *_BUILT_IN_RESOURCE_IDS),
    )
    connection.execute(
        "UPDATE background_agent_settings SET autonomy = 'custom', allowed_tool_names_json = ?, updated_at = ? WHERE settings_id = 1",
        (json.dumps(_BUILT_IN_TOOL_NAMES, separators=(",", ":")), timestamp),
    )
