#!/usr/bin/env python3
"""
Professional AutoTrader Pro - Main Entry Point
Clean startup script for the automated trading system
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main_automated import main
from infra.logging_config import setup_logging


def check_environment():
    """Check if environment is properly configured"""
    print("🔍 Checking environment configuration...")

    required_vars = ["ALPACA_API_KEY", "ALPACA_SECRET_KEY"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("ℹ️  Set these variables in your environment or .env file")
        return False

    print("✅ Environment configuration valid")
    return True


def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║                   🚀 AutoTrader Pro v1.0                    ║
    ║                                                              ║
    ║               Professional Automated Trading System          ║
    ║                                                              ║
    ║  Features:                                                   ║
    ║  • Automated Stock Screening                                 ║
    ║  • Multi-Factor Stock Scoring                                ║
    ║  • Dynamic Symbol Tracking                                   ║
    ║  • Advanced Strategy Engine                                  ║
    ║  • Signal Aggregation                                        ║
    ║  • Risk Management                                           ║
    ║  • Automated Order Execution                                 ║
    ║  • Continuous Position Monitoring                            ║
    ║  • Complete Audit Logging                                    ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


if __name__ == "__main__":
    # Print banner
    print_banner()

    # Setup logging
    setup_logging()

    # Check environment
    if not check_environment():
        sys.exit(1)

    # Start the trading system
    try:
        print("🚀 Starting AutoTrader Pro...")
        print("📊 Dashboard will be available at: http://localhost:8501")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
