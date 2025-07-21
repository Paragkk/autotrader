"""
Logging Config with pathlib support
"""

import logging
from pathlib import Path

from .path_utils import ensure_directory, get_logs_dir


class WarningAndAboveFilter(logging.Filter):
    """Filter that only allows WARNING level and above messages to pass through"""

    def filter(self, record):
        return record.levelno >= logging.WARNING


def setup_logging(
    log_level: str = "INFO",
    log_file: str | Path | None = None,
    enable_file_logging: bool = True,
) -> None:
    """
    Setup logging with both console and file handlers.
    File handler only logs WARNING level and above and replaces the log file on each app start.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (relative to logs directory if not absolute)
        enable_file_logging: Whether to enable file logging (WARNING+ only)
    """
    # Clear any existing handlers
    logger = logging.getLogger()
    logger.handlers.clear()

    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    # Console handler - logs all levels according to log_level
    console_handler = logging.StreamHandler()
    # No custom formatter - preserves colorful formatting from uvicorn and other libraries
    logger.addHandler(console_handler)

    # File handler - only logs WARNING and above
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

        # File handler that replaces the log file on each app start
        # Remove existing log file to start fresh
        if log_file.exists():
            log_file.unlink()

        file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")

        # Add filter to only log WARNING and above to file
        warning_filter = WarningAndAboveFilter()
        file_handler.addFilter(warning_filter)

        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Log the setup
    logger.info(f"Logging configured with level: {log_level}")
    if enable_file_logging:
        logger.info(f"Log file (WARNING+ only): {log_file}")
