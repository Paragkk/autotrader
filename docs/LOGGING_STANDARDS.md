# AutoTrader Pro - Logging Standards

## Overview

This document defines the centralized logging standards for AutoTrader Pro. All logging should be consistent across the application to ensure proper monitoring, debugging, and auditing capabilities.

## Centralized Logging Configuration

The project uses a centralized logging configuration located in `src/infra/logging_config.py`. This file provides:

- **Structured logging** with JSON formatting for production
- **File rotation** to prevent log files from growing too large
- **Multiple log levels** for different environments
- **Consistent formatting** across all components

## Usage Guidelines

### For Application Components (inside src/)

All modules inside the `src/` directory should use the centralized logging configuration:

```python
import logging
from infra.logging_config import setup_logging, get_logger

# Setup logging (typically done once in main application startup)
setup_logging(
    log_level="INFO",
    enable_json_logging=True,
    enable_file_logging=True,
    log_file="trading_system.log"
)

# Get logger instance
logger = get_logger(__name__)

# Use logger
logger.info("Application started successfully")
logger.error("An error occurred", exc_info=True)
```

### For Scripts and Utilities

For standalone scripts (like those in the `scripts/` directory), use the simple logging setup:

```python
import logging
from pathlib import Path
import sys

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from infra.logging_config import setup_simple_logging, get_logger

# Setup simple logging
setup_simple_logging(log_level="INFO")
logger = get_logger(__name__)

# Use logger
logger.info("Script started")
```

### For Entry Points (like run.py)

Entry point scripts that can't easily import from src should use a consistent local setup:

```python
import logging
from pathlib import Path

def setup_entry_logging():
    """Setup logging for entry point scripts"""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(logs_dir / "entry_point.log")
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

setup_entry_logging()
logger = logging.getLogger(__name__)
```

## Log Levels

Use appropriate log levels for different types of information:

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: General information about application operation
- **WARNING**: Something unexpected happened, but the application is still working
- **ERROR**: A serious problem occurred that prevented a function from working
- **CRITICAL**: A very serious error that may prevent the program from continuing

## Log Formatting Standards

### Console Format (Simple)
```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### File Format (Detailed)
```
%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s
```

### JSON Format (Production)
Uses `json_log_formatter.JSONFormatter()` for structured logging in production environments.

## File Organization

- **Main application logs**: `logs/trading_system.log`
- **Startup logs**: `logs/autotrader_startup.log`
- **Script logs**: `logs/<script_name>.log`
- **Rotating logs**: Automatically rotated at 10MB with 5 backup files

## Best Practices

1. **Use the centralized configuration** - Don't use `logging.basicConfig()` directly
2. **Include context** - Use structured logging with relevant context information
3. **Handle exceptions properly** - Use `exc_info=True` when logging exceptions
4. **Use appropriate levels** - Don't log everything as INFO
5. **Keep sensitive data out** - Never log passwords, API keys, or personal information
6. **Use logger names** - Always use `get_logger(__name__)` or `logging.getLogger(__name__)`

## Migration from basicConfig

If you find code using `logging.basicConfig()`, replace it with the appropriate centralized setup:

### Before (❌ Don't do this)
```python
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
```

### After (✅ Do this)
```python
import logging
from infra.logging_config import setup_simple_logging, get_logger

setup_simple_logging(log_level="INFO")
logger = get_logger(__name__)
```

## Configuration Options

The `setup_logging()` function accepts these parameters:

- `log_level`: Logging level (default: "INFO")
- `log_file`: Path to log file (default: "trading_system.log")
- `enable_json_logging`: Use JSON format for console (default: True)
- `enable_file_logging`: Enable file logging (default: True)
- `max_file_size`: Maximum log file size in bytes (default: 10MB)
- `backup_count`: Number of backup files to keep (default: 5)

## Examples

### Application Component
```python
# src/core/trading_engine.py
import logging
from infra.logging_config import get_logger

logger = get_logger(__name__)

class TradingEngine:
    def start(self):
        logger.info("Trading engine starting...")
        try:
            # Trading logic
            logger.info("Trading engine started successfully")
        except Exception as e:
            logger.error("Failed to start trading engine", exc_info=True)
            raise
```

### Utility Script
```python
# scripts/data_migration.py
import logging
from pathlib import Path
import sys

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from infra.logging_config import setup_simple_logging, get_logger

setup_simple_logging(log_level="INFO")
logger = get_logger(__name__)

def migrate_data():
    logger.info("Starting data migration...")
    # Migration logic
    logger.info("Data migration completed")

if __name__ == "__main__":
    migrate_data()
```

This centralized approach ensures consistent logging across the entire AutoTrader Pro application while maintaining flexibility for different use cases.
