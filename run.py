#!/usr/bin/env python3
"""
Professional AutoTrader Pro - Main Entry Point
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main_automated import main  # noqa: E402


def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║                   🚀 AutoTrader Pro v1.0                     ║
    ║                                                              ║
    ║               Professional Automated Trading System          ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


if __name__ == "__main__":
    print_banner()

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
