from __future__ import annotations

import asyncio
import http.server
import importlib
import platform
import sqlite3
import ssl
from collections.abc import Callable
from types import ModuleType


AGENT_RUNTIME_MODULES = ("jiter", "pydantic_core", "rpds", "openai", "agents")


def standard_library_status() -> dict[str, object]:
    return {
        "status": "ready",
        "pythonVersion": platform.python_version(),
        "sqliteVersion": sqlite3.sqlite_version,
        "opensslVersion": ssl.OPENSSL_VERSION,
        "imports": [asyncio.__name__, http.server.__name__, sqlite3.__name__, ssl.__name__],
    }


def agent_runtime_status(
    importer: Callable[[str], ModuleType] = importlib.import_module,
) -> dict[str, object]:
    imported: list[str] = []
    try:
        for module_name in AGENT_RUNTIME_MODULES:
            importer(module_name)
            imported.append(module_name)
    except Exception:
        return {"status": "not_ready", "imports": imported}
    return {"status": "ready", "imports": imported}
