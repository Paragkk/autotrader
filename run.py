#!/usr/bin/env python3
"""
AutoTrader Pro - Complete System Startup Script
Starts both FastAPI server and Streamlit dashboard using uv
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for centralized logging import
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Use centralized logging configuration
try:
    from infra.logging_config import get_logger, setup_simple_logging

    # Set up centralized logging for startup
    setup_simple_logging(log_level="INFO")
    logger = get_logger(__name__)
    logger.info("Using centralized logging configuration")
except ImportError as e:
    # Fallback to basic logging if centralized config isn't available
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import centralized logging, using basic config: {e}")


def print_banner() -> None:
    """Print startup banner"""


def print_info() -> None:
    """Print system information"""


if __name__ == "__main__":
    print_banner()
    print_info()

    # Start the FastAPI server (which will auto-start the dashboard) using uv
    try:
        # Set PYTHONPATH to include src directory
        env = os.environ.copy()
        src_path = str(Path(__file__).parent / "src")
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{src_path};{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = src_path

        # Run the FastAPI app with uv and uvicorn (dashboard starts via lifespan)
        cmd = [
            "uv",
            "run",
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8080",
            "--reload",
            "--log-level",
            "info",
            "--access-log",
            "--reload-dir",
            "src",
        ]

        subprocess.run(cmd, cwd=Path(__file__).parent, env=env, check=False)

    except KeyboardInterrupt:
        pass
    except Exception:
        logger.exception("System startup failed")
        sys.exit(1)
