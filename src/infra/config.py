"""
Config Loader for Consolidated Configuration
===========================================
Configuration loader for the consolidated configuration structure.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Union, List
import logging

from .path_utils import get_project_root

logger = logging.getLogger(__name__)


def resolve_config_path(config_path: Union[str, Path, None] = None) -> Path:
    """
    Resolve configuration file path relative to project root.

    Args:
        config_path: Path to config file (can be relative or absolute)

    Returns:
        Resolved Path object
    """
    if config_path is None:
        config_path = "config.yaml"

    config_path = Path(config_path)

    # If it's already absolute, return as-is
    if config_path.is_absolute():
        return config_path

    # Try relative to project root first
    project_root = get_project_root()
    full_path = project_root / config_path

    if full_path.exists():
        return full_path

    # Try relative to current working directory
    cwd_path = Path.cwd() / config_path
    if cwd_path.exists():
        return cwd_path

    # Return project root relative path (might not exist, but that's for caller to handle)
    return full_path


def load_config(config_path: Union[str, Path, None] = None) -> Dict[str, Any]:
    """
    Load configuration from the consolidated YAML file with environment variable overrides.

    Args:
        config_path: Path to config file (relative to project root or absolute)

    Returns:
        Dictionary containing configuration data

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
        ValueError: If no broker configuration is found or no brokers are enabled
    """
    resolved_path = resolve_config_path(config_path)

    if not resolved_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {resolved_path}")

    try:
        with resolved_path.open("r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in configuration file {resolved_path}: {e}")

    # Validate that we have broker configuration
    if "brokers" not in config_data:
        raise ValueError("No 'brokers' section found in configuration")

    # Validate that at least one broker is enabled
    brokers_config = config_data["brokers"]
    enabled_brokers = []
    for broker_name, broker_config in brokers_config.items():
        if isinstance(broker_config, dict) and broker_config.get("enabled", False):
            enabled_brokers.append(broker_name)

    if not enabled_brokers:
        raise ValueError(
            "No enabled brokers found in configuration. "
            "At least one broker must be enabled to use the trading system."
        )

    logger.info(f"✅ Configuration loaded from {resolved_path}")
    return config_data


def get_broker_config(
    broker_name: str, config_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Get configuration for a specific broker.

    Args:
        broker_name: Name of the broker (e.g., "alpaca")
        config_data: Pre-loaded configuration data (optional)

    Returns:
        Dictionary containing broker-specific configuration

    Raises:
        ValueError: If broker not found in configuration
    """
    if config_data is None:
        config_data = load_config()

    brokers_config = config_data.get("brokers", {})

    if broker_name not in brokers_config:
        available_brokers = [k for k in brokers_config.keys() if k != "default"]
        raise ValueError(
            f"Broker '{broker_name}' not found in configuration. "
            f"Available brokers: {available_brokers}"
        )

    broker_config = brokers_config[broker_name].copy()
    broker_config["broker_name"] = broker_name

    # Load environment variables directly based on broker type
    if broker_name == "alpaca":
        broker_config["api_key"] = os.getenv("ALPACA_API_KEY")
        broker_config["secret_key"] = os.getenv("ALPACA_SECRET_KEY")
    elif broker_name == "interactive_brokers":
        broker_config["api_key"] = os.getenv("IB_API_KEY")
        broker_config["secret_key"] = os.getenv("IB_SECRET_KEY")

    return broker_config


def get_active_brokers(config_data: Dict[str, Any] = None) -> List[str]:
    """
    Get list of enabled brokers.

    Args:
        config_data: Pre-loaded configuration data (optional)

    Returns:
        List of broker names that are enabled
    """
    if config_data is None:
        config_data = load_config()

    brokers_config = config_data.get("brokers", {})
    active_brokers = []

    for broker_name, broker_config in brokers_config.items():
        if isinstance(broker_config, dict):
            if broker_config.get("enabled", False):
                active_brokers.append(broker_name)

    return active_brokers


def get_alert_config(config_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get alert configuration with environment variables loaded.

    Args:
        config_data: Pre-loaded configuration data (optional)

    Returns:
        Dictionary containing alert configuration with credentials
    """
    if config_data is None:
        config_data = load_config()

    alert_config = config_data.get("alerts", {}).copy()

    # Load Telegram credentials from environment
    if "telegram" in alert_config:
        telegram_config = alert_config["telegram"]
        telegram_config["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_config["chat_id"] = os.getenv("TELEGRAM_CHAT_ID")

    # Load Email credentials from environment
    if "email" in alert_config:
        email_config = alert_config["email"]
        email_config["username"] = os.getenv("EMAIL_USERNAME")
        email_config["password"] = os.getenv("EMAIL_PASSWORD")

    return alert_config


def get_database_config(config_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get database configuration with environment variable override.

    Args:
        config_data: Pre-loaded configuration data (optional)

    Returns:
        Dictionary containing database configuration
    """
    if config_data is None:
        config_data = load_config()

    db_config = config_data.get("database", {}).copy()

    # Override with environment variable if provided
    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url:
        db_config["url"] = env_db_url

    return db_config


def get_first_active_broker(config_data: Dict[str, Any] = None) -> str:
    """
    Get the first enabled broker.

    This is a utility function for cases where you need a broker but don't
    care which specific one. It's recommended to explicitly specify brokers
    instead of using this function.

    Args:
        config_data: Pre-loaded configuration data (optional)

    Returns:
        Name of the first enabled broker

    Raises:
        ValueError: If no enabled brokers are found
    """
    active_brokers = get_active_brokers(config_data)
    if not active_brokers:
        raise ValueError(
            "No enabled brokers found. Please enable at least one broker in the configuration."
        )
    return active_brokers[0]


def get_active_broker(config_data: Dict[str, Any] = None) -> str:
    """
    Get the currently active broker based on environment variable or first enabled broker.

    Args:
        config_data: Pre-loaded configuration data (optional)

    Returns:
        Name of the active broker

    Raises:
        ValueError: If no brokers are available or enabled
    """
    if config_data is None:
        config_data = load_config()

    # Check environment variables (highest priority)
    active_broker = os.getenv("ACTIVE_BROKER", os.getenv("TRADING_BROKER"))

    brokers_config = config_data.get("brokers", {})
    available_brokers = list(brokers_config.keys())

    if active_broker:
        if active_broker in available_brokers:
            # If environment specifies a broker, use it (even if disabled in config)
            # This allows users to override config via environment
            return active_broker
        else:
            logger.warning(
                f"Environment broker '{active_broker}' not found in config. Using default."
            )

    # Fallback to first enabled broker in config
    for broker_name, broker_config in brokers_config.items():
        if isinstance(broker_config, dict) and broker_config.get("enabled", False):
            return broker_name

    # Fallback to first available broker
    if available_brokers:
        return available_brokers[0]

    raise ValueError("No brokers available in configuration")


def is_broker_enabled(broker_name: str, config_data: Dict[str, Any] = None) -> bool:
    """
    Check if a broker is enabled in configuration.

    Args:
        broker_name: Name of the broker to check
        config_data: Pre-loaded configuration data (optional)

    Returns:
        True if broker is enabled, False otherwise
    """
    if config_data is None:
        config_data = load_config()

    brokers_config = config_data.get("brokers", {})

    if broker_name not in brokers_config:
        return False

    broker_config = brokers_config[broker_name]
    return isinstance(broker_config, dict) and broker_config.get("enabled", False)
