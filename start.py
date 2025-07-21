#!/usr/bin/env python3
"""
AutoTrader Pro - Simple Startup Script
Launch the complete trading system
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def setup_environment() -> None:
    """Setup the environment"""
    # Set demo broker as default
    os.environ.setdefault("ACTIVE_BROKER", "demo_broker")
    os.environ.setdefault("DEMO_API_KEY", "demo_key_123")
    os.environ.setdefault("DEMO_SECRET_KEY", "demo_secret_456")

    # Add src to Python path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))


def start_api_server() -> subprocess.Popen[bytes]:
    """Start the FastAPI server"""
    cmd = [
        "uv",
        "run",
        "uvicorn",
        "src.api.main:app",
        "--host",
        "127.0.0.1",  # Changed from 0.0.0.0 for security
        "--port",
        "8080",
        "--reload",
    ]
    return subprocess.Popen(cmd)


def start_dashboard() -> subprocess.Popen[bytes]:
    """Start the Streamlit dashboard"""
    time.sleep(2)  # Give API server time to start
    cmd = [
        "uv",
        "run",
        "streamlit",
        "run",
        "src/dashboard/main.py",
        "--server.port",
        "8501",
        "--server.address",
        "127.0.0.1",  # Changed from 0.0.0.0 for security
    ]
    return subprocess.Popen(cmd)


def main() -> int:
    """Main startup function"""
    setup_environment()

    try:
        # Start API server
        api_process = start_api_server()

        # Start dashboard
        dashboard_process = start_dashboard()

        # Wait for keyboard interrupt
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            # Terminate processes
            api_process.terminate()
            dashboard_process.terminate()

            # Wait for processes to terminate
            api_process.wait()
            dashboard_process.wait()

    except Exception:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
