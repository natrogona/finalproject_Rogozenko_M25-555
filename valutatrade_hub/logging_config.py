"""Logging configuration for the ValutaTrade Hub application."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from valutatrade_hub.infra.settings import get_settings


def setup_logging() -> logging.Logger:
    """
    Configure and return the application logger.

    Returns:
        Configured logger instance
    """
    settings = get_settings()

    # Create logger
    logger = logging.getLogger("valutatrade_hub")
    logger.setLevel(getattr(logging, settings.get("log_level", "INFO")))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Create formatter
    log_format = settings.get(
        "log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    formatter = logging.Formatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    try:
        log_file = settings.get("log_file", "valutatrade.log")
        max_bytes = settings.get("log_max_bytes", 10485760)  # 10MB
        backup_count = settings.get("log_backup_count", 5)

        # Ensure logs directory exists
        log_path = Path(log_file)
        if log_path.parent != Path("."):
            log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Failed to setup file logging: {e}")

    logger.info("Logging configured successfully")
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (optional)

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"valutatrade_hub.{name}")
    return logging.getLogger("valutatrade_hub")
