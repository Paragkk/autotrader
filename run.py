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

# Import and setup centralized logging
from infra.logging_config import setup_logging

setup_logging(log_level="INFO")
logger = logging.getLogger(__name__)


def print_banner() -> None:
    """Print startup banner"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║                    🚀 AutoTrader Pro                         ║
║                                                               ║
║            Professional Multi-Broker Trading System          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info("AutoTrader Pro - Starting system...")


def print_info() -> None:
    """Print system information"""
    info = """
📊 System Configuration:
   • FastAPI Server: http://localhost:8080
   • Dashboard: http://localhost:8501 (auto-started)
   • Default Broker: demo_broker (fallback: alpaca)
   • Environment: Development Mode
   
🔧 Features:
   • Multi-broker support (Alpaca, Demo, Interactive Brokers)
   • Real-time trading dashboard
   • Paper trading mode
   • Order management & portfolio tracking
   
💡 Quick Start:
   1. Server will start automatically
   2. Dashboard will launch at http://localhost:8501
   3. Use dropdown in dashboard to switch brokers
   4. Check API docs at http://localhost:8080/docs
    """
    print(info)
    logger.info("System configuration loaded")


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

        # Set DEFAULT_BROKERS to prioritize demo_broker first
        env["DEFAULT_BROKERS"] = "demo_broker"

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

        logger.info(f"Starting FastAPI server with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=Path(__file__).parent, env=env, check=True)

        # If we reach here, the server exited normally
        logger.info("FastAPI server has stopped")
        if result.returncode != 0:
            logger.error(f"FastAPI server exited with error code: {result.returncode}")
            sys.exit(result.returncode)

    except KeyboardInterrupt:
        pass
    except Exception:
        logger.exception("System startup failed")
        sys.exit(1)
