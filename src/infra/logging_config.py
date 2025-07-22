"""
Logging Config with pathlib support
"""

import logging
from datetime import datetime
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
    Console handler shows INFO to CRITICAL level logs.
    File handler logs WARNING and above level logs.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (relative to logs directory if not absolute)
        enable_file_logging: Whether to enable file logging (WARNING and above)
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(logging.DEBUG)  # Set to DEBUG to allow all levels through

    # Console handler - logs INFO to CRITICAL level logs (no JSON format)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Simple formatter for console (no JSON format)
    console_formatter = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler - logs WARNING and above
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

        # File handler that overwrites the log file on each app start
        file_mode = "w"
        if log_file.exists():
            try:
                # Try to delete the file first
                log_file.unlink()
            except (PermissionError, OSError):
                # If deletion fails, try to truncate the file
                try:
                    log_file.write_text("", encoding="utf-8")
                except Exception:
                    # Final fallback: append mode with separator
                    file_mode = "a"
                    try:
                        with open(log_file, "a", encoding="utf-8") as f:
                            f.write(f"\n\n{'=' * 80}\n")
                            f.write(f"NEW SESSION STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"{'=' * 80}\n\n")
                    except Exception:
                        pass

        file_handler = logging.FileHandler(log_file, mode=file_mode, encoding="utf-8")

        # Add filter for WARNING and above to file
        warning_filter = WarningAndAboveFilter()
        file_handler.addFilter(warning_filter)

        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s")
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Configure uvicorn loggers to use the same handlers
    uvicorn_loggers = ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]

    for logger_name in uvicorn_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        # Ensure uvicorn loggers don't duplicate messages
        logger.propagate = True

    # Log the setup
    root_logger.info(f"Logging configured - Console: INFO+, File: WARNING+")
    if enable_file_logging:
        root_logger.info(f"Log file (WARNING+): {log_file}")
