#!/usr/bin/env python3
"""
AutoTrader Pro - System Status Check
Comprehensive validation of the trading system
"""

import os
import sys
import asyncio
import requests
from pathlib import Path
import subprocess

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set environment for demo
os.environ.setdefault("ACTIVE_BROKER", "demo_broker")
os.environ.setdefault("DEMO_API_KEY", "demo_key_123")
os.environ.setdefault("DEMO_SECRET_KEY", "demo_secret_456")


class SystemStatusChecker:
    """Comprehensive system status checker"""

    def __init__(self):
        self.api_running = False
        self.dashboard_running = False
        self.broker_system_ok = False

    def check_uv_installation(self):
        """Check if uv is installed and working"""
        print("1. Checking uv installation...")
        try:
            result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ uv installed: {result.stdout.strip()}")
                return True
            else:
                print("   ❌ uv command failed")
                return False
        except FileNotFoundError:
            print("   ❌ uv not found in PATH")
            return False

    def check_dependencies(self):
        """Check if dependencies are available"""
        print("2. Checking Python dependencies...")
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
                    ["uv", "run", "python", "-c", f"import {dep}"], capture_output=True
                )
                if result.returncode == 0:
                    print(f"   ✅ {dep} available")
                else:
                    print(f"   ❌ {dep} not available")
                    return False
            except Exception as e:
                print(f"   ❌ Error checking {dep}: {e}")
                return False

        return True

    async def check_broker_system(self):
        """Test the broker system directly"""
        print("3. Testing broker system...")
        try:
            from src.core.broker_manager import (
                get_broker_manager,
                initialize_default_broker,
            )

            await initialize_default_broker()
            broker_manager = get_broker_manager()

            # Test account info
            account = await broker_manager.get_account_info()
            print(f"   ✅ Account connected: {account.account_id}")
            print(f"   💰 Portfolio value: ${account.portfolio_value:,.2f}")

            self.broker_system_ok = True
            return True

        except Exception as e:
            print(f"   ❌ Broker system error: {e}")
            return False

    def check_api_server(self, timeout=5):
        """Check if API server is running"""
        print("4. Checking API server...")
        try:
            response = requests.get("http://localhost:8080/health", timeout=timeout)
            if response.status_code == 200:
                print("   ✅ API server responding")
                self.api_running = True
                return True
            else:
                print(f"   ❌ API server returned {response.status_code}")
                return False
        except requests.exceptions.RequestException:
            print("   ⚠️  API server not running or not accessible")
            return False

    def check_dashboard(self, timeout=5):
        """Check if dashboard is running"""
        print("5. Checking dashboard...")
        try:
            response = requests.get("http://localhost:8501", timeout=timeout)
            if response.status_code == 200:
                print("   ✅ Dashboard responding")
                self.dashboard_running = True
                return True
            else:
                print(f"   ❌ Dashboard returned {response.status_code}")
                return False
        except requests.exceptions.RequestException:
            print("   ⚠️  Dashboard not running or not accessible")
            return False

    def check_configuration_files(self):
        """Check if all required configuration files exist"""
        print("6. Checking configuration files...")
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
                print(f"   ✅ {file_path}")
            else:
                print(f"   ❌ {file_path} missing")
                return False

        return True

    async def run_full_check(self):
        """Run complete system check"""
        print("🔍 AutoTrader Pro - System Status Check")
        print("=" * 50)

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

        print("\n📊 Summary:")
        print("=" * 30)
        print(f"Checks passed: {passed}/{total}")

        if self.broker_system_ok:
            print("✅ Core broker system: WORKING")
        else:
            print("❌ Core broker system: FAILED")

        if self.api_running:
            print("✅ API server: RUNNING")
        else:
            print("⚠️  API server: NOT RUNNING")

        if self.dashboard_running:
            print("✅ Dashboard: RUNNING")
        else:
            print("⚠️  Dashboard: NOT RUNNING")

        print("\n🎯 Next Steps:")
        if passed == total:
            print("• System is fully operational!")
            print("• Access dashboard at: http://localhost:8501")
            print("• API docs at: http://localhost:8080/docs")
        elif self.broker_system_ok:
            print("• Broker system works - core functionality OK")
            print("• To start full system: uv run python start.py")
            print("• Or use PowerShell: .\\start.ps1")
        else:
            print("• Run: uv run python demo.py (for quick test)")
            print("• Run: uv run python quick_setup.py (if needed)")

        return passed == total


async def main():
    """Main function"""
    checker = SystemStatusChecker()
    success = await checker.run_full_check()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
