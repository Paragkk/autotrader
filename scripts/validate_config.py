#!/usr/bin/env python3
"""
Configuration Validation Script
Validates broker-specific configuration files and provides detailed feedback
"""

import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from infra.config import load_config, get_available_brokers


# Set up standardized logging for scripts
def setup_script_logging():
    """Setup consistent logging for standalone scripts"""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    # Console handler with consistent format
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


setup_script_logging()
logger = logging.getLogger(__name__)


def validate_required_keys(
    config: Dict[str, Any], required_keys: List[str], config_name: str
) -> List[str]:
    """
    Validate that required keys are present in config.

    Args:
        config: Configuration dictionary
        required_keys: List of required keys
        config_name: Name of the config for error messages

    Returns:
        List of missing keys
    """
    missing_keys = []
    for key in required_keys:
        if key not in config:
            missing_keys.append(key)

    if missing_keys:
        logger.error(f"{config_name}: Missing required keys: {missing_keys}")
    else:
        logger.info(f"{config_name}: All required keys present")

    return missing_keys


def validate_alpaca_config(config: Dict[str, Any]) -> bool:
    """
    Validate Alpaca-specific configuration.

    Args:
        config: Configuration dictionary

    Returns:
        True if valid, False otherwise
    """
    logger.info("Validating Alpaca configuration...")

    required_keys = [
        "alpaca_api_key",
        "alpaca_secret_key",
        "use_paper_trading",
        "max_positions",
        "position_size_percent",
    ]

    missing_keys = validate_required_keys(config, required_keys, "Alpaca Config")

    # Validate API keys are not default values
    if config.get("alpaca_api_key") == "your_alpaca_api_key_here":
        logger.warning("Alpaca API key is still set to default value")

    if config.get("alpaca_secret_key") == "your_alpaca_secret_key_here":
        logger.warning("Alpaca secret key is still set to default value")

    # Validate base URL for paper trading
    if config.get("use_paper_trading") and config.get("base_url"):
        expected_paper_url = "https://paper-api.alpaca.markets"
        if config.get("base_url") != expected_paper_url:
            logger.warning(
                f"Paper trading enabled but base_url is not {expected_paper_url}"
            )

    # Validate numeric ranges
    max_positions = config.get("max_positions", 0)
    if max_positions <= 0:
        logger.error("max_positions must be greater than 0")
        return False

    position_size = config.get("position_size_percent", 0)
    if position_size <= 0 or position_size > 1:
        logger.error("position_size_percent must be between 0 and 1")
        return False

    return len(missing_keys) == 0


def validate_main_config(config: Dict[str, Any]) -> bool:
    """
    Validate main configuration.

    Args:
        config: Configuration dictionary

    Returns:
        True if valid, False otherwise
    """
    logger.info("Validating main configuration...")

    required_keys = ["broker"]
    missing_keys = validate_required_keys(config, required_keys, "Main Config")

    # Validate broker selection
    broker = config.get("broker")
    if broker:
        available_brokers = get_available_brokers()
        if broker not in available_brokers:
            logger.error(
                f"Selected broker '{broker}' not in available brokers: {available_brokers}"
            )
            return False
        logger.info(f"Broker '{broker}' is available")

    return len(missing_keys) == 0


def validate_base_config(config: Dict[str, Any]) -> bool:
    """
    Validate base configuration.

    Args:
        config: Configuration dictionary

    Returns:
        True if valid, False otherwise
    """
    logger.info("Validating base configuration...")

    # Base config is optional, so just check for common issues
    if "database_url" in config:
        logger.info("Database URL configured")

    if "log_level" in config:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level = config.get("log_level", "").upper()
        if level not in valid_levels:
            logger.warning(f"Invalid log level '{level}'. Valid levels: {valid_levels}")

    return True


def validate_full_config() -> bool:
    """
    Validate the complete configuration system.

    Returns:
        True if all validations pass, False otherwise
    """
    logger.info("Starting full configuration validation...")

    try:
        # Load the full merged configuration
        config = load_config()
        logger.info("✓ Configuration loaded successfully")

        # Validate main config
        if not validate_main_config(config):
            return False

        # Validate base config
        if not validate_base_config(config):
            return False

        # Validate broker-specific config
        broker = config.get("broker")
        if broker == "alpaca":
            if not validate_alpaca_config(config):
                return False
        else:
            logger.warning(f"No specific validation for broker '{broker}'")

        logger.info("✓ All configuration validations passed!")
        return True

    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return False


def show_config_summary():
    """Show a summary of the current configuration."""
    logger.info("Configuration Summary")
    logger.info("=" * 50)

    try:
        config = load_config()

        # Show key settings
        logger.info(f"Broker: {config.get('broker', 'Not set')}")
        logger.info(f"Environment: {config.get('environment', 'Not set')}")
        logger.info(f"Paper Trading: {config.get('use_paper_trading', 'Not set')}")
        logger.info(f"Max Positions: {config.get('max_positions', 'Not set')}")
        logger.info(f"Log Level: {config.get('log_level', 'Not set')}")

        # Show broker selection source
        import os

        if os.getenv("TRADING_BROKER"):
            logger.info("Broker source: Environment variable (TRADING_BROKER)")
        else:
            logger.info("Broker source: Configuration file")

        # Show available brokers
        brokers = get_available_brokers()
        logger.info(f"Available Brokers: {brokers}")

        # Show broker config path
        broker_name = config.get("broker", "alpaca")
        from infra.path_utils import get_project_root

        project_root = get_project_root()
        broker_config_path = (
            project_root / "src" / "brokers" / broker_name / "config.yaml"
        )
        logger.info(f"Broker config path: {broker_config_path}")

        # Show symbols being tracked
        symbols = config.get("symbols_to_track", [])
        logger.info(f"Symbols Tracked: {len(symbols)} symbols")

    except Exception as e:
        logger.error(f"Failed to load config for summary: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate trading system configuration"
    )
    parser.add_argument(
        "--summary", action="store_true", help="Show configuration summary"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Perform full validation"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Reduce output verbosity"
    )

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    if args.summary:
        show_config_summary()
        return

    if args.validate or not any([args.summary]):
        # Default to validation if no specific action requested
        success = validate_full_config()
        if not success:
            sys.exit(1)

    logger.info("Configuration validation completed successfully!")


if __name__ == "__main__":
    main()
