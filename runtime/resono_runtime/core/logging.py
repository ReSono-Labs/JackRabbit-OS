from __future__ import annotations

from logging import Handler, Formatter, StreamHandler, getLogger
from logging.handlers import RotatingFileHandler
from pathlib import Path


_LOGGER_NAME = "resono-runtime"
_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_runtime_logging(log_path: Path) -> None:
    logger = getLogger(_LOGGER_NAME)
    file_handler_exists = any(isinstance(item, RotatingFileHandler) for item in logger.handlers)
    stream_handler_exists = any(
        isinstance(item, StreamHandler) and not isinstance(item, RotatingFileHandler) for item in logger.handlers
    )
    if file_handler_exists and stream_handler_exists:
        return
    logger.setLevel("INFO")
    formatter = Formatter(_FORMAT)

    if not file_handler_exists:
        file_handler: Handler = RotatingFileHandler(
            log_path,
            maxBytes=512_000,
            backupCount=3,
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if not stream_handler_exists:
        stream_handler: Handler = StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    logger.propagate = False
    logger.info("logging.initialized", extra={"path": str(log_path)})


def runtime_logger():
    return getLogger(_LOGGER_NAME)
