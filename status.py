#!/usr/bin/env python3
"""
AutoTrader Pro - System Status Check
Comprehensive validation of the trading system
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

import requests

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set environment for demo
os.environ.setdefault("ACTIVE_BROKER", "demo_broker")
os.environ.setdefault("DEMO_API_KEY", "demo_key_123")
os.environ.setdefault("DEMO_SECRET_KEY", "demo_secret_456")

# Configure logging for status checker
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# HTTP Status Code Constants
HTTP_OK = 200


class SystemStatusChecker:
    """Comprehensive system status checker"""

    def __init__(self) -> None:
        self.api_running = False
        self.dashboard_running = False
        self.broker_system_ok = False

    def check_uv_installation(self) -> bool:
        """Check if uv is installed and working"""
        logger.info("1. Checking uv installation...")
        try:
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            logger.exception("   ❌ uv not found in PATH")
            return False
        else:
            if result.returncode == 0:
                logger.info("   ✅ uv installed: %s", result.stdout.strip())
                return True
            logger.error("   ❌ uv command failed")
            return False

    def check_dependencies(self) -> bool:
        """Check if dependencies are available"""
        logger.info("2. Checking Python dependencies...")
        dependencies = [
            "fastapi",
            "streamlit",
            "uvicorn",
            "pydantic",
            "python-multipart",
        ]

        for dep in dependencies:
            try:
                result = subprocess.run(
                    ["uv", "run", "python", "-c", f"import {dep}"],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                logger.exception("   ❌ Error checking %s", dep)
                return False
            else:
                if result.returncode == 0:
                    logger.info("   ✅ %s available", dep)
                else:
                    logger.error("   ❌ %s not available", dep)
                    return False

        return True

    async def check_broker_system(self) -> bool:
        """Test the broker system directly"""
        logger.info("3. Testing broker system...")
        try:
            from src.core.broker_manager import (
                get_broker_manager,
                initialize_default_broker,
            )

            await initialize_default_broker()
            broker_manager = get_broker_manager()

            # Test account info
            account = await broker_manager.get_account_info()
        except Exception:
            logger.exception("   ❌ Broker system error")
            return False
        else:
            logger.info("   ✅ Account connected: %s", account.account_id)
            logger.info("   💰 Portfolio value: $%.2f", account.portfolio_value)

            self.broker_system_ok = True
            return True

    def check_api_server(self, timeout: int = 5) -> bool:
        """Check if API server is running"""
        logger.info("4. Checking API server...")
        try:
            response = requests.get("http://localhost:8080/health", timeout=timeout)
        except requests.exceptions.RequestException:
            logger.warning("   ⚠️  API server not running or not accessible")
            return False
        else:
            if response.status_code == HTTP_OK:
                logger.info("   ✅ API server responding")
                self.api_running = True
                return True
            logger.error("   ❌ API server returned %s", response.status_code)
            return False

    def check_dashboard(self, timeout: int = 5) -> bool:
        """Check if dashboard is running"""
        logger.info("5. Checking dashboard...")
        try:
            response = requests.get("http://localhost:8501", timeout=timeout)
        except requests.exceptions.RequestException:
            logger.warning("   ⚠️  Dashboard not running or not accessible")
            return False
        else:
            if response.status_code == HTTP_OK:
                logger.info("   ✅ Dashboard responding")
                self.dashboard_running = True
                return True
            logger.error("   ❌ Dashboard returned %s", response.status_code)
            return False

    def check_configuration_files(self) -> bool:
        """Check if all required configuration files exist"""
        logger.info("6. Checking configuration files...")
        required_files = [
            "config.yaml",
            ".env",
            "pyproject.toml",
            "src/api/main.py",
            "src/dashboard/main.py",
            "src/core/broker_manager.py",
            "src/brokers/demo_broker/adapter.py",
        ]

        for file_path in required_files:
            if Path(file_path).exists():
                logger.info("   ✅ %s", file_path)
            else:
                logger.error("   ❌ %s missing", file_path)
                return False

        return True

    async def run_full_check(self) -> bool:
        """Run complete system check"""
        logger.info("🔍 AutoTrader Pro - System Status Check")
        logger.info("=" * 50)

        checks = [
            self.check_uv_installation(),
            self.check_dependencies(),
            await self.check_broker_system(),
            self.check_api_server(),
            self.check_dashboard(),
            self.check_configuration_files(),
        ]

        passed = sum(checks)
        total = len(checks)

        logger.info("\n📊 Summary:")
        logger.info("=" * 30)
        logger.info("Checks passed: %d/%d", passed, total)

        if self.broker_system_ok:
            logger.info("✅ Core broker system: WORKING")
        else:
            logger.error("❌ Core broker system: FAILED")

        if self.api_running:
            logger.info("✅ API server: RUNNING")
        else:
            logger.warning("⚠️  API server: NOT RUNNING")

        if self.dashboard_running:
            logger.info("✅ Dashboard: RUNNING")
        else:
            logger.warning("⚠️  Dashboard: NOT RUNNING")

        logger.info("\n🎯 Next Steps:")
        if passed == total:
            logger.info("• System is fully operational!")
            logger.info("• Access dashboard at: http://localhost:8501")
            logger.info("• API docs at: http://localhost:8080/docs")
        elif self.broker_system_ok:
            logger.info("• Broker system works - core functionality OK")
            logger.info("• To start full system: uv run python start.py")
            logger.info("• Or use PowerShell: .\\start.ps1")
        else:
            logger.info("• Run: uv run python demo.py (for quick test)")
            logger.info("• Run: uv run python quick_setup.py (if needed)")

        return passed == total


async def main() -> int:
    """Main function"""
    checker = SystemStatusChecker()
    success = await checker.run_full_check()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
