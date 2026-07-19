"""Centralized logging configuration.

Provides `get_logger(name)` returning a logger that writes to both the
console and a rotating file under `logs/`. Intended to replace the
scattered `print()` calls throughout the codebase.
"""

import logging
from logging.handlers import RotatingFileHandler

from app.config.settings import LOG_DIR

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_CONFIGURED = False


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(
        LOG_DIR / "job_agent.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # Avoid stacking duplicate handlers on re-import.
    if not any(getattr(h, "_job_agent", False) for h in root.handlers):
        console._job_agent = True  # type: ignore[attr-defined]
        file_handler._job_agent = True  # type: ignore[attr-defined]
        root.addHandler(console)
        root.addHandler(file_handler)

    # Quiet down noisy third-party libraries.
    for noisy in ("urllib3", "httpx", "chromadb", "httpcore", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger with the given name."""
    _configure_root()
    return logging.getLogger(name)
