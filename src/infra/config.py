"""
Unified Configuration System
===========================
Comprehensive configuration loader supporting both consolidated YAML configuration
and individual broker directory configurations with environment variable overrides.

GENERIC BROKER DISCOVERY SYSTEM
==============================

This configuration system now supports automatic broker discovery and loading.
Instead of hardcoding broker imports, the system dynamically:

1. Scans the `src/brokers/` directory for broker implementations
2. Dynamically imports adapter modules from `{broker_name}/adapter.py`
3. Automatically finds adapter classes that inherit from broker base classes
4. Provides detailed error messages for missing or invalid brokers

To add a new broker:
1. Create a directory under `src/brokers/` with your broker name (e.g., `src/brokers/my_broker/`)
2. Add an `adapter.py` file with a class that inherits from BrokerAdapter or related mixins
3. Add the broker configuration to `config.yaml` under the `brokers` section
4. The system will automatically discover and load your broker

Supported base classes for auto-discovery:
- BrokerAdapter
- RESTBrokerAdapter
- OrderValidationMixin
- PositionTrackingMixin
- BrokerConfigurationMixin
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Union, List
import logging
import importlib
import inspect

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

    # Validate that we have broker configuration
    brokers_config = config_data["brokers"]
    if not brokers_config:
        raise ValueError(
            "No brokers found in configuration. "
            "At least one broker must be configured to use the trading system."
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
        EnvironmentError: If required environment variables are missing
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

    # Load environment variables dynamically based on broker configuration
    env_vars = broker_config.get("env_vars", {})
    missing_env_vars = []

    for config_key, env_var_name in env_vars.items():
        env_value = os.getenv(env_var_name)
        if env_value is None:
            missing_env_vars.append(env_var_name)
        else:
            broker_config[config_key] = env_value

    # Raise error if any required environment variables are missing
    if missing_env_vars:
        raise EnvironmentError(
            f"Missing required environment variables for broker '{broker_name}': "
            f"{', '.join(missing_env_vars)}. Please set these environment variables."
        )

    return broker_config


def get_active_brokers(config_data: Dict[str, Any] = None) -> List[str]:
    """
    Get list of available brokers.

    Args:
        config_data: Pre-loaded configuration data (optional)

    Returns:
        List of broker names that are available
    """
    if config_data is None:
        config_data = load_config()

    brokers_config = config_data.get("brokers", {})
    available_brokers = []

    for broker_name, broker_config in brokers_config.items():
        if isinstance(broker_config, dict):
            available_brokers.append(broker_name)

    return available_brokers


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
    Get the first available broker.

    This is a utility function for cases where you need a broker but don't
    care which specific one. It's recommended to explicitly specify brokers
    instead of using this function.

    Args:
        config_data: Pre-loaded configuration data (optional)

    Returns:
        Name of the first available broker

    Raises:
        ValueError: If no brokers are found
    """
    active_brokers = get_active_brokers(config_data)
    if not active_brokers:
        raise ValueError(
            "No brokers found. Please configure at least one broker in the configuration."
        )
    return active_brokers[0]


def get_active_broker(config_data: Dict[str, Any] = None) -> str:
    """
    Get the currently active broker based on environment variable or first configured broker.

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

    # Fallback to first available broker in config
    available_brokers = list(brokers_config.keys())
    if available_brokers:
        return available_brokers[0]

    raise ValueError("No brokers available in configuration")


def is_broker_configured(broker_name: str, config_data: Dict[str, Any] = None) -> bool:
    """
    Check if a broker is configured.

    Args:
        broker_name: Name of the broker to check
        config_data: Pre-loaded configuration data (optional)

    Returns:
        True if broker is configured, False otherwise
    """
    if config_data is None:
        config_data = load_config()

    brokers_config = config_data.get("brokers", {})

    if broker_name not in brokers_config:
        return False

    broker_config = brokers_config[broker_name]
    return isinstance(broker_config, dict)


def validate_broker_env_vars(
    broker_name: str, config_data: Dict[str, Any] = None
) -> bool:
    """
    Validate that all required environment variables are set for a broker.

    Args:
        broker_name: Name of the broker to validate
        config_data: Pre-loaded configuration data (optional)

    Returns:
        True if all required environment variables are set

    Raises:
        ValueError: If broker not found in configuration
        EnvironmentError: If required environment variables are missing
    """
    if config_data is None:
        config_data = load_config()

    brokers_config = config_data.get("brokers", {})

    if broker_name not in brokers_config:
        available_brokers = [k for k in brokers_config.keys()]
        raise ValueError(
            f"Broker '{broker_name}' not found in configuration. "
            f"Available brokers: {available_brokers}"
        )

    broker_config = brokers_config[broker_name]
    env_vars = broker_config.get("env_vars", {})
    missing_env_vars = []

    for config_key, env_var_name in env_vars.items():
        if os.getenv(env_var_name) is None:
            missing_env_vars.append(env_var_name)

    if missing_env_vars:
        raise EnvironmentError(
            f"Missing required environment variables for broker '{broker_name}': "
            f"{', '.join(missing_env_vars)}. Please set these environment variables."
        )

    return True


def get_broker_env_vars(
    broker_name: str, config_data: Dict[str, Any] = None
) -> Dict[str, str]:
    """
    Get the environment variable mappings for a specific broker.

    Args:
        broker_name: Name of the broker
        config_data: Pre-loaded configuration data (optional)

    Returns:
        Dictionary mapping config keys to environment variable names

    Raises:
        ValueError: If broker not found in configuration
    """
    if config_data is None:
        config_data = load_config()

    brokers_config = config_data.get("brokers", {})

    if broker_name not in brokers_config:
        available_brokers = [k for k in brokers_config.keys()]
        raise ValueError(
            f"Broker '{broker_name}' not found in configuration. "
            f"Available brokers: {available_brokers}"
        )

    broker_config = brokers_config[broker_name]
    return broker_config.get("env_vars", {})


def validate_broker_config(broker_name: str, config: Dict[str, Any]) -> bool:
    """
    Validate broker configuration structure and required fields.

    This validates the final assembled configuration (after environment variables
    have been loaded) to ensure all required fields are present for broker creation.
    The required fields are loaded from the broker-specific config.yaml file.

    Args:
        broker_name: Name of the broker
        config: Configuration dictionary to validate (with env vars already loaded)

    Returns:
        True if configuration is valid, False otherwise
    """
    # Load required fields from broker-specific configuration
    required_fields = _get_broker_required_fields(broker_name)

    if not required_fields:
        # Fallback to basic validation if no broker config found
        logger.warning(
            f"No required fields config found for {broker_name}, using basic validation"
        )
        return _validate_basic_broker_config(broker_name, config)

    logger.debug(
        f"Validating {broker_name} config with required fields: {required_fields}"
    )
    logger.debug(f"Available config keys: {list(config.keys())}")

    # Check for missing required fields
    missing_fields = []

    for field in required_fields:
        # Check multiple possible field names for flexibility
        field_variants = _get_field_variants(field, broker_name)
        logger.debug(f"Checking field '{field}' with variants: {field_variants}")

        if not any(variant in config for variant in field_variants):
            missing_fields.append(field)

    if missing_fields:
        logger.error(f"Missing required fields for {broker_name}: {missing_fields}")
        logger.error(f"Available config keys: {list(config.keys())}")
        return False

    logger.info(f"✅ Configuration validated for broker: {broker_name}")
    return True


def _discover_broker_adapter(broker_name: str):
    """
    Dynamically discover and import a broker adapter class.

    Args:
        broker_name: Name of the broker (e.g., "alpaca", "demo_broker")

    Returns:
        BrokerAdapter class

    Raises:
        ImportError: If broker adapter cannot be imported
        ValueError: If broker is not supported or adapter class not found
    """
    broker_name_lower = broker_name.lower()

    # Try to import the adapter module
    try:
        module_path = f"src.brokers.{broker_name_lower}.adapter"
        adapter_module = importlib.import_module(module_path)
    except ImportError as e:
        # Check if broker directory exists
        from .path_utils import get_project_root

        broker_path = get_project_root() / "src" / "brokers" / broker_name_lower
        if not broker_path.exists():
            # List available brokers
            brokers_path = get_project_root() / "src" / "brokers"
            available_brokers = [
                d.name
                for d in brokers_path.iterdir()
                if d.is_dir()
                and not d.name.startswith((".", "__"))
                and d.name not in ("base", "common")
            ]
            raise ValueError(
                f"Broker '{broker_name}' not found. Available brokers: {available_brokers}"
            )
        else:
            raise ImportError(
                f"Could not import adapter for broker '{broker_name}': {e}"
            )

    # Find the adapter class in the module
    adapter_class = None

    # Look for classes that inherit from BrokerAdapter or related base classes
    for name, obj in inspect.getmembers(adapter_module, inspect.isclass):
        if obj.__module__ == adapter_module.__name__ and _is_broker_adapter_class(obj):
            adapter_class = obj
            break

    if adapter_class is None:
        # Get list of classes in the module for debugging
        classes_in_module = [
            name
            for name, obj in inspect.getmembers(adapter_module, inspect.isclass)
            if obj.__module__ == adapter_module.__name__
        ]

        raise ValueError(
            f"No broker adapter class found in {module_path}. "
            f"Expected a class inheriting from BrokerAdapter or related base classes. "
            f"Classes found in module: {classes_in_module}. "
            f"Make sure your adapter class inherits from one of: "
            f"BrokerAdapter, RESTBrokerAdapter, OrderValidationMixin, "
            f"PositionTrackingMixin, or BrokerConfigurationMixin."
        )

    logger.info(f"✅ Discovered broker adapter: {adapter_class.__name__}")
    return adapter_class


def _is_broker_adapter_class(cls) -> bool:
    """
    Check if a class is a broker adapter class by examining its inheritance.

    Args:
        cls: Class to check

    Returns:
        True if class appears to be a broker adapter
    """
    # Check if it's a subclass of common broker base classes
    base_class_names = {base.__name__ for base in cls.__mro__}

    # Look for common broker adapter base class names
    adapter_indicators = {
        "BrokerAdapter",
        "RESTBrokerAdapter",
        "OrderValidationMixin",
        "PositionTrackingMixin",
        "BrokerConfigurationMixin",
    }

    # Must have at least one broker-related base class
    return bool(adapter_indicators.intersection(base_class_names))


def create_broker_adapter(broker_name: str, config: Dict[str, Any]):
    """
    Create a broker adapter instance with validation.

    Args:
        broker_name: Name of the broker (e.g., "alpaca", "demo_broker")
        config: Broker configuration dictionary

    Returns:
        BrokerAdapter instance

    Raises:
        ValueError: If broker is not supported or config is invalid
    """
    # Dynamically discover and import broker adapter
    adapter_class = _discover_broker_adapter(broker_name)

    # Validate configuration before creating adapter
    if not validate_broker_config(broker_name, config):
        raise ValueError(f"Invalid configuration for broker: {broker_name}")

    try:
        logger.info(f"✅ Creating {broker_name} broker adapter")
        return adapter_class(config)
    except Exception as e:
        logger.error(f"❌ Failed to create {broker_name} broker adapter: {e}")
        raise


def get_supported_brokers_from_code() -> List[str]:
    """
    Get list of brokers that have code implementations.

    Returns:
        List of broker names that have adapter implementations
    """
    try:
        from .path_utils import get_project_root

        brokers_path = get_project_root() / "src" / "brokers"

        if not brokers_path.exists():
            logger.warning(f"Brokers directory not found: {brokers_path}")
            return []

        supported_brokers = []

        for broker_dir in brokers_path.iterdir():
            if (
                broker_dir.is_dir()
                and not broker_dir.name.startswith((".", "__"))
                and broker_dir.name not in ("base", "common")
            ):
                # Check if adapter.py exists
                adapter_file = broker_dir / "adapter.py"
                if adapter_file.exists():
                    supported_brokers.append(broker_dir.name)

        logger.info(f"✅ Discovered broker implementations: {supported_brokers}")
        return supported_brokers

    except Exception as e:
        logger.error(f"❌ Error discovering broker implementations: {e}")
        # Fallback to known brokers
        return ["alpaca", "demo_broker"]


def is_broker_supported(broker_name: str) -> bool:
    """
    Check if a broker is supported by the system.

    Args:
        broker_name: Name of the broker to check

    Returns:
        True if broker is supported, False otherwise
    """
    return broker_name.lower() in get_supported_brokers_from_code()


def _get_broker_required_fields(broker_name: str) -> List[str]:
    """
    Load required fields from broker-specific configuration file.

    Args:
        broker_name: Name of the broker

    Returns:
        List of required field names, empty list if config not found
    """
    try:
        from .path_utils import get_project_root

        broker_config_path = (
            get_project_root() / "src" / "brokers" / broker_name.lower() / "config.yaml"
        )

        if not broker_config_path.exists():
            logger.warning(
                f"No config.yaml found for broker {broker_name} at {broker_config_path}"
            )
            return []

        with broker_config_path.open("r", encoding="utf-8") as f:
            broker_config = yaml.safe_load(f) or {}

        required_fields = broker_config.get("required_config", [])
        logger.debug(f"Loaded required fields for {broker_name}: {required_fields}")
        return required_fields

    except Exception as e:
        logger.error(f"Error loading broker config for {broker_name}: {e}")
        return []


def _get_field_variants(field: str, broker_name: str) -> List[str]:
    """
    Generate field name variants to check for flexibility.

    Args:
        field: Base field name (e.g., "api_key")
        broker_name: Name of the broker

    Returns:
        List of field name variants to check
    """
    variants = [field]

    # Add broker-specific variants
    variants.append(f"{broker_name}_{field}")
    variants.append(f"{broker_name.upper()}_{field.upper()}")

    # Add common field variants
    if "secret" in field or "api_secret" in field:
        variants.extend(
            [
                "secret_key",
                "api_secret",
            ]
        )

    return list(set(variants))  # Remove duplicates


def _validate_basic_broker_config(broker_name: str, config: Dict[str, Any]) -> bool:
    """
    Fallback basic validation when broker-specific config is not available.

    Args:
        broker_name: Name of the broker
        config: Configuration dictionary to validate

    Returns:
        True if configuration is valid, False otherwise
    """
    missing_fields = []

    # Check for API key (broker-specific or generic)
    has_api_key = any(
        key in config
        for key in [
            "api_key",
            f"{broker_name}_api_key",
        ]
    )

    # Check for secret key (broker-specific or generic)
    has_secret = any(
        key in config
        for key in [
            "secret_key",
            "api_secret",
            f"{broker_name}_secret_key",
        ]
    )

    if not has_api_key:
        missing_fields.append("api_key")
    if not has_secret:
        missing_fields.append("secret_key or api_secret")

    # Check for base_url if not a demo broker
    if broker_name != "demo_broker" and "base_url" not in config:
        missing_fields.append("base_url")

    if missing_fields:
        logger.error(f"Missing required fields for {broker_name}: {missing_fields}")
        return False

    return True
