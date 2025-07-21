#!/usr/bin/env python3
"""
AutoTrader Pro - Complete System Startup Script
Starts both FastAPI server and Streamlit dashboard using uv
"""

import subprocess
import sys
import os
import logging
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
    from infra.logging_config import setup_simple_logging, get_logger

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


def print_banner():
    """Print startup banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════════════════════════════╗
    ║                                                                                       ║
    ║                   🚀 AutoTrader Pro v2.0 - Complete Trading System                    ║
    ║                                                                                       ║
    ║               Professional Automated Trading with Streamlit Dashboard                 ║
    ║                                                                                       ║
    ║  FastAPI Server:     http://localhost:8080                                           ║
    ║  API Documentation:  http://localhost:8080/docs                                      ║
    ║  Streamlit Dashboard: http://localhost:8501                                          ║
    ║                                                                                       ║
    ╚═══════════════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_info():
    """Print system information"""
    print("\n📊 System Features:")
    print("   • Multi-broker support (Alpaca, Interactive Brokers, Demo)")
    print("   • Broker selection and switching via dashboard")
    print("   • Real-time portfolio monitoring and position management")
    print("   • Comprehensive trading operations (buy, sell, close positions)")
    print("   • Order management and history tracking")
    print("   • REST API for all trading operations")
    print("   • Emergency stop functionality")
    print("\n🎛️ Dashboard Controls:")
    print("   • Broker connection management and status")
    print("   • Portfolio metrics with real-time updates")
    print("   • Position management and quick close")
    print("   • Trading interface with multiple order types")
    print("   • Order history and execution monitoring")
    print("\n🔗 API Endpoints:")
    print("   • Trading: /api/trading/* (orders, positions, account)")
    print("   • Brokers: /api/brokers/* (connect, disconnect, status)")
    print("   • Documentation: http://localhost:8080/docs")


if __name__ == "__main__":
    print_banner()
    print_info()

    # Start the FastAPI server (which will auto-start the dashboard) using uv
    try:
        print("\n🚀 Starting AutoTrader Pro System with uv...")
        print("⚡ Multi-broker trading system initializing...")
        print("🔄 Please wait while services start (API + Dashboard)...")
        print("📊 Dashboard will be available at: http://localhost:8501")
        print("🔌 API documentation at: http://localhost:8080/docs")

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

        subprocess.run(cmd, cwd=Path(__file__).parent, env=env)

    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user")
        print("💡 AutoTrader Pro is shutting down gracefully...")
        print("✅ Both API and Dashboard services will be stopped")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.exception("System startup failed")
        sys.exit(1)
