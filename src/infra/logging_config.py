"""
Structured Logging Config with pathlib support
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Union
import json_log_formatter

from .path_utils import get_logs_dir, ensure_directory


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Union[str, Path]] = None,
    enable_json_logging: bool = True,
    enable_file_logging: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Setup structured logging with both console and file handlers.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (relative to logs directory if not absolute)
        enable_json_logging: Whether to use JSON formatter for console
        enable_file_logging: Whether to enable file logging
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup files to keep
    """
    # Clear any existing handlers
    logger = logging.getLogger()
    logger.handlers.clear()

    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()

    if enable_json_logging:
        console_formatter = json_log_formatter.JSONFormatter()
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    if enable_file_logging:
        if log_file is None:
            log_file = "trading_system.log"

        log_file = Path(log_file)

        # If not absolute, make it relative to logs directory
        if not log_file.is_absolute():
            logs_dir = get_logs_dir()
            log_file = logs_dir / log_file

        # Ensure log directory exists
        ensure_directory(log_file.parent)

        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_file_size, backupCount=backup_count, encoding="utf-8"
        )

        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )

        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Log the setup
    logger.info(f"Logging configured with level: {log_level}")
    if enable_file_logging:
        logger.info(f"Log file: {log_file}")


# Default setup for backward compatibility
formatter = json_log_formatter.JSONFormatter()
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)
