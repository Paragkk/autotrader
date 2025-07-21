#!/usr/bin/env python3
"""
AutoTrader Pro - Simple Startup Script
Launch the complete trading system
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def setup_environment():
    """Setup the environment"""
    # Set demo broker as default
    os.environ.setdefault("ACTIVE_BROKER", "demo_broker")
    os.environ.setdefault("DEMO_API_KEY", "demo_key_123")
    os.environ.setdefault("DEMO_SECRET_KEY", "demo_secret_456")

    # Add src to Python path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))


def start_api_server():
    """Start the FastAPI server"""
    print("🚀 Starting AutoTrader Pro API Server...")
    cmd = [
        "uv",
        "run",
        "uvicorn",
        "src.api.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8080",
        "--reload",
    ]
    return subprocess.Popen(cmd)


def start_dashboard():
    """Start the Streamlit dashboard"""
    print("📊 Starting AutoTrader Pro Dashboard...")
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
        "0.0.0.0",
    ]
    return subprocess.Popen(cmd)


def main():
    """Main startup function"""
    setup_environment()

    print("🏛️ AutoTrader Pro v2.0 - Multi-Broker Trading System")
    print("=" * 60)

    try:
        # Start API server
        api_process = start_api_server()

        # Start dashboard
        dashboard_process = start_dashboard()

        print("\n✅ AutoTrader Pro is running!")
        print("🌐 API Documentation: http://localhost:8080/docs")
        print("📊 Trading Dashboard: http://localhost:8501")
        print("\nPress Ctrl+C to stop all services")

        # Wait for keyboard interrupt
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down AutoTrader Pro...")

            # Terminate processes
            api_process.terminate()
            dashboard_process.terminate()

            # Wait for processes to terminate
            api_process.wait()
            dashboard_process.wait()

            print("✅ AutoTrader Pro stopped successfully")

    except Exception as e:
        print(f"❌ Failed to start AutoTrader Pro: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
