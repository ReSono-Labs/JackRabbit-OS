from __future__ import annotations

import threading

from .application import RuntimeApplication
from .config import RuntimeConfig


_lock = threading.Lock()
_application: RuntimeApplication | None = None


def start(
    root_path: str,
    local_api_token: str,
    credential_bridge: object,
    restart_request: object | None = None,
) -> None:
    global _application
    with _lock:
        if _application is not None:
            return
        application = RuntimeApplication(
            RuntimeConfig.create(root_path, local_api_token),
            credential_bridge=credential_bridge,
            restart_request=restart_request,
        )
        application.start()
        _application = application


def stop() -> None:
    global _application
    with _lock:
        application = _application
        _application = None
    if application is not None:
        application.stop()
