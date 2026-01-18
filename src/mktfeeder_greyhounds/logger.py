from __future__ import annotations

import sys
from pathlib import Path
from loguru import logger

from src.mktfeeder_greyhounds.config import settings

_LOGGER_CONFIGURED = False


def _ensure_logs_dir() -> Path:
    log_dir = settings.DATA_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logger() -> None:
    """Configura loguru (console + arquivo) uma única vez."""
    global _LOGGER_CONFIGURED
    if _LOGGER_CONFIGURED:
        return

    logger.remove()
    # Console
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | {level} | {message}",
    )
    # Arquivo com rotação
    log_dir = _ensure_logs_dir()
    logger.add(
        log_dir / "mktfeeder.log",
        level=settings.LOG_LEVEL,
        rotation="1 day",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    _LOGGER_CONFIGURED = True


def get_logger():
    setup_logger()
    return logger


# Backward compatibility
def configure_logging() -> None:
    setup_logger()


__all__ = ["setup_logger", "configure_logging", "get_logger", "logger"]

