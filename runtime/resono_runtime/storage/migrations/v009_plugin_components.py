from __future__ import annotations
import sqlite3

def apply(connection: sqlite3.Connection) -> None:
    connection.execute("""CREATE TABLE IF NOT EXISTS plugin_components (
        plugin_name TEXT NOT NULL, component_type TEXT NOT NULL CHECK(component_type IN ('skill','mcp')),
        component_key TEXT NOT NULL, validation_state TEXT NOT NULL CHECK(validation_state IN ('valid','invalid')),
        detail TEXT, PRIMARY KEY(plugin_name, component_type, component_key))""")
