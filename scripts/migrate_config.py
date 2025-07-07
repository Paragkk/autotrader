#!/usr/bin/env python3
"""
Configuration Migration Script
Migrates from single config.yaml to broker-specific configuration structure
"""

import yaml
import shutil
from pathlib import Path
import argparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_config_to_broker_structure(
    old_config_path: str = "config.yaml", backup: bool = True
) -> None:
    """
    Migrate from old single config.yaml to new broker-specific structure.

    Args:
        old_config_path: Path to the old config file
        backup: Whether to create a backup of the old config
    """
    old_config = Path(old_config_path)

    if not old_config.exists():
        logger.error(f"Old config file not found: {old_config}")
        return

    # Load the old config
    try:
        with old_config.open("r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in old config file: {e}")
        return

    # Create backup if requested
    if backup:
        backup_path = old_config.with_suffix(".yaml.backup")
        shutil.copy2(old_config, backup_path)
        logger.info(f"Created backup: {backup_path}")

    # Get broker name from config
    broker_name = config_data.get("broker", "alpaca")

    # Create new main config
    main_config = {"broker": broker_name, "environment": "development"}

    # Add any custom overrides from the old config
    # These are settings that should be in the main config rather than broker-specific
    main_config_keys = ["log_level", "environment"]
    for key in main_config_keys:
        if key in config_data:
            main_config[key] = config_data[key]

    # Write new main config
    main_config_path = Path("main_config.yaml")
    with main_config_path.open("w", encoding="utf-8") as f:
        yaml.dump(main_config, f, default_flow_style=False, sort_keys=False)
    logger.info(f"Created main config: {main_config_path}")

    # Update broker-specific config if needed
    broker_config_path = Path(f"src/brokers/{broker_name}/config.yaml")
    if broker_config_path.exists():
        # Load existing broker config
        with broker_config_path.open("r", encoding="utf-8") as f:
            broker_config = yaml.safe_load(f) or {}

        # Update with values from old config
        broker_specific_keys = [
            "alpaca_api_key",
            "alpaca_secret_key",
            "use_paper_trading",
            "max_positions",
            "max_daily_loss",
            "position_size_percent",
            "stop_loss_percent",
            "take_profit_percent",
            "symbols_to_track",
            "strategy_weights",
            "market_data_update_interval",
            "news_update_interval",
            "strategy_evaluation_interval",
        ]

        for key in broker_specific_keys:
            if key in config_data:
                broker_config[key] = config_data[key]

        # Write updated broker config
        with broker_config_path.open("w", encoding="utf-8") as f:
            yaml.dump(broker_config, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Updated broker config: {broker_config_path}")
    else:
        logger.warning(f"Broker config not found: {broker_config_path}")

    # Remove old config file
    old_config.unlink()
    logger.info(f"Removed old config file: {old_config}")

    logger.info("Migration completed successfully!")
    logger.info("New configuration structure:")
    logger.info(f"  - Main config: {main_config_path}")
    logger.info("  - Base config: src/brokers/base/config/base_config.yaml")
    logger.info(f"  - Broker config: {broker_config_path}")
    logger.info("\nYou can now use environment variables to switch brokers:")
    logger.info("  export TRADING_BROKER=alpaca")
    logger.info("  # or set TRADING_BROKER=alpaca in your .env file")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate configuration to broker-specific structure"
    )
    parser.add_argument(
        "--old-config",
        default="config.yaml",
        help="Path to old config file (default: config.yaml)",
    )
    parser.add_argument(
        "--no-backup", action="store_true", help="Don't create backup of old config"
    )

    args = parser.parse_args()

    migrate_config_to_broker_structure(
        old_config_path=args.old_config, backup=not args.no_backup
    )


if __name__ == "__main__":
    main()
