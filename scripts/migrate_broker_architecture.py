#!/usr/bin/env python3
"""
Migration Script: From Broker-Specific to Broker-Agnostic Architecture
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.brokers.base.factory import BrokerFactory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_config_file(config_path: str = "config.yaml") -> None:
    """
    Migrate old config file to new broker-agnostic format
    """
    logger.info(f"Migrating config file: {config_path}")

    # Read existing config
    if not os.path.exists(config_path):
        logger.warning(f"Config file not found: {config_path}")
        return

    with open(config_path, "r") as f:
        content = f.read()

    # Check if already migrated
    if "broker:" in content:
        logger.info("Config file already migrated")
        return

    # Add broker configuration
    lines = content.split("\n")
    new_lines = []

    for line in lines:
        if line.strip() == "# Advanced Trading System Configuration":
            new_lines.append(line)
            new_lines.append("# =====================================")
            new_lines.append("")
            new_lines.append("# Broker Configuration")
            new_lines.append('broker: "alpaca"  # Only Alpaca broker supported')
            new_lines.append("")
        elif line.strip() == "# API Configuration":
            new_lines.append('# Alpaca Configuration (when broker = "alpaca")')
        else:
            new_lines.append(line)

    # Write back
    with open(config_path, "w") as f:
        f.write("\n".join(new_lines))

    logger.info("Config file migrated successfully")


def test_broker_connection(broker_name: str, config: Dict[str, Any]) -> bool:
    """
    Test broker connection
    """
    logger.info(f"Testing {broker_name} broker connection...")

    try:
        broker = BrokerFactory.create_broker(broker_name, config)

        # Test basic operations
        if hasattr(broker, "connect"):
            broker.connect()

        # Test getting account info
        account_info = broker.get_account_info()
        logger.info(f"Account ID: {account_info.account_id}")
        logger.info(f"Buying Power: ${account_info.buying_power:,.2f}")

        if hasattr(broker, "disconnect"):
            broker.disconnect()

        logger.info(f"✅ {broker_name} broker connection successful")
        return True

    except NotImplementedError:
        logger.warning(f"⚠️ {broker_name} broker not yet implemented")
        return False
    except Exception as e:
        logger.error(f"❌ {broker_name} broker connection failed: {e}")
        return False


def validate_migration() -> bool:
    """
    Validate that the migration was successful
    """
    logger.info("Validating migration...")

    # Check if new broker structure exists
    broker_base_path = Path("src/brokers/base")
    if not broker_base_path.exists():
        logger.error("❌ Broker base directory not found")
        return False

    # Check if interface file exists
    interface_path = broker_base_path / "interface.py"
    if not interface_path.exists():
        logger.error("❌ Broker interface file not found")
        return False

    # Check if factory file exists
    factory_path = broker_base_path / "factory.py"
    if not factory_path.exists():
        logger.error("❌ Broker factory file not found")
        return False

    # Check if Alpaca adapter exists
    alpaca_path = Path("src/brokers/alpaca/adapter.py")
    if not alpaca_path.exists():
        logger.error("❌ Alpaca adapter not found")
        return False

    # Test broker factory
    try:
        supported_brokers = BrokerFactory.get_supported_brokers()
        logger.info(f"✅ Supported brokers: {supported_brokers}")
    except Exception as e:
        logger.error(f"❌ Broker factory test failed: {e}")
        return False

    logger.info("✅ Migration validation successful")
    return True


def main():
    """
    Main migration function
    """
    logger.info("Starting broker-agnostic architecture migration...")

    # Step 1: Migrate config file
    migrate_config_file()

    # Step 2: Validate migration
    if not validate_migration():
        logger.error("Migration validation failed")
        return 1

    # Step 3: Test broker connections (optional)
    if len(sys.argv) > 1 and sys.argv[1] == "--test-brokers":
        logger.info("Testing broker connections...")

        # Test Alpaca (if credentials available)
        alpaca_config = {
            "api_key": os.getenv("ALPACA_API_KEY"),
            "secret_key": os.getenv("ALPACA_SECRET_KEY"),
            "paper_trading": True,
        }

        if alpaca_config["api_key"] and alpaca_config["secret_key"]:
            test_broker_connection("alpaca", alpaca_config)
        else:
            logger.warning("Alpaca credentials not found in environment variables")

    logger.info("Migration completed successfully!")
    logger.info("\nNext steps:")
    logger.info("1. Update your config.yaml with the appropriate broker settings")
    logger.info("2. Set environment variables for broker API keys")
    logger.info("3. Test the system with paper trading first")
    logger.info("4. Review the README_BROKER_MIGRATION.md for detailed information")

    return 0


if __name__ == "__main__":
    sys.exit(main())
