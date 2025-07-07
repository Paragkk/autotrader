"""
Config Loader with pathlib support for uv-managed projects
Supports broker-specific configuration loading
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Union, List

from .path_utils import get_project_root


def resolve_config_path(config_path: Union[str, Path, None] = None) -> Path:
    """
    Resolve configuration file path relative to project root.

    Args:
        config_path: Path to config file (can be relative or absolute)

    Returns:
        Resolved Path object
    """
    if config_path is None:
        config_path = "main_config.yaml"

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


def load_broker_config(broker_name: str) -> Dict[str, Any]:
    """
    Load broker-specific configuration file.

    Args:
        broker_name: Name of the broker (e.g., "alpaca")

    Returns:
        Dictionary containing broker-specific configuration

    Raises:
        FileNotFoundError: If broker config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    project_root = get_project_root()
    broker_config_path = project_root / "src" / "brokers" / broker_name / "config.yaml"

    if not broker_config_path.exists():
        raise FileNotFoundError(f"Broker config file not found: {broker_config_path}")

    try:
        with broker_config_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise yaml.YAMLError(
            f"Invalid YAML in broker config file {broker_config_path}: {e}"
        )


def load_base_config() -> Dict[str, Any]:
    """
    Load base configuration file.

    Returns:
        Dictionary containing base configuration

    Raises:
        FileNotFoundError: If base config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    project_root = get_project_root()
    base_config_path = (
        project_root / "src" / "brokers" / "base" / "config" / "base_config.yaml"
    )

    if not base_config_path.exists():
        raise FileNotFoundError(f"Base config file not found: {base_config_path}")

    try:
        with base_config_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise yaml.YAMLError(
            f"Invalid YAML in base config file {base_config_path}: {e}"
        )


def merge_configs(
    base_config: Dict[str, Any],
    broker_config: Dict[str, Any],
    main_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge configuration dictionaries with proper precedence.

    Args:
        base_config: Base configuration (lowest priority)
        broker_config: Broker-specific configuration (medium priority)
        main_config: Main configuration (highest priority)

    Returns:
        Merged configuration dictionary
    """
    merged = {}

    # Start with base config
    merged.update(base_config)

    # Override with broker config
    merged.update(broker_config)

    # Override with main config (excluding broker selection)
    main_overrides = {
        k: v for k, v in main_config.items() if k not in ["broker", "environment"]
    }
    merged.update(main_overrides)

    # Keep broker and environment from main config
    merged["broker"] = main_config.get("broker", "alpaca")
    merged["environment"] = main_config.get("environment", "development")

    return merged


def load_config(config_path: Union[str, Path, None] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML files with broker-specific support and environment variable overrides.

    Loading order (later configs override earlier ones):
    1. Base configuration (src/brokers/base/config/base_config.yaml)
    2. Broker-specific configuration (src/brokers/{broker}/config.yaml)
    3. Main configuration file (main_config.yaml by default)
    4. Environment variable overrides

    Broker selection priority:
    1. TRADING_BROKER environment variable
    2. broker field in main config file
    3. Default to 'alpaca'

    Args:
        config_path: Path to main config file (relative to project root or absolute)

    Returns:
        Dictionary containing merged configuration data

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    # Get broker name from environment variable first
    broker_name = os.getenv("TRADING_BROKER")

    # If no environment variable, try to load from main config
    if not broker_name:
        try:
            resolved_path = resolve_config_path(config_path)
            if resolved_path.exists():
                with resolved_path.open("r", encoding="utf-8") as f:
                    main_config = yaml.safe_load(f) or {}
                broker_name = main_config.get("broker", "alpaca")
            else:
                # If main config doesn't exist, use default
                broker_name = "alpaca"
                main_config = {}
        except (FileNotFoundError, yaml.YAMLError):
            broker_name = "alpaca"
            main_config = {}
    else:
        # If broker comes from env var, still try to load main config for other settings
        try:
            resolved_path = resolve_config_path(config_path)
            if resolved_path.exists():
                with resolved_path.open("r", encoding="utf-8") as f:
                    main_config = yaml.safe_load(f) or {}
            else:
                main_config = {}
        except (FileNotFoundError, yaml.YAMLError):
            main_config = {}

    # Load base configuration
    try:
        base_config = load_base_config()
    except FileNotFoundError:
        # If base config doesn't exist, use empty dict
        base_config = {}

    # Load broker-specific configuration
    try:
        broker_config = load_broker_config(broker_name)
    except FileNotFoundError:
        # If broker config doesn't exist, use empty dict
        broker_config = {}

    # Merge all configurations
    config_data = merge_configs(base_config, broker_config, main_config)

    # Override broker name if it came from environment
    config_data["broker"] = broker_name

    # Environment variables take precedence over config file values
    # This is useful for secrets and deployment-specific overrides
    env_overrides = {
        key.lower(): value
        for key, value in os.environ.items()
        if key.startswith(("TRADING_", "ALPACA_", "DATABASE_"))
    }

    # Apply environment overrides
    for env_key, env_value in env_overrides.items():
        # Convert environment variable names to config keys
        # e.g., TRADING_MAX_POSITIONS -> max_positions
        config_key = (
            env_key.replace("trading_", "")
            .replace("alpaca_", "")
            .replace("database_", "")
        )

        # Skip the broker key as it's handled separately
        if config_key == "broker":
            continue

        # Try to convert to appropriate type
        if env_value.lower() in ("true", "false"):
            config_data[config_key] = env_value.lower() == "true"
        elif env_value.replace(".", "").replace("-", "").isdigit():
            try:
                config_data[config_key] = (
                    float(env_value) if "." in env_value else int(env_value)
                )
            except ValueError:
                config_data[config_key] = env_value
        else:
            config_data[config_key] = env_value

    return config_data


def get_available_brokers() -> List[str]:
    """
    Get list of available brokers based on existing config files.

    Returns:
        List of broker names that have config files
    """
    project_root = get_project_root()
    brokers_dir = project_root / "src" / "brokers"

    available_brokers = []

    for item in brokers_dir.iterdir():
        if item.is_dir() and item.name != "base" and item.name != "__pycache__":
            config_file = item / "config.yaml"
            if config_file.exists():
                available_brokers.append(item.name)

    return available_brokers


def validate_broker_config(broker_name: str) -> bool:
    """
    Validate that a broker configuration exists and is valid.

    Args:
        broker_name: Name of the broker to validate

    Returns:
        True if broker config is valid, False otherwise
    """
    try:
        load_broker_config(broker_name)
        return True
    except (FileNotFoundError, yaml.YAMLError):
        return False


def create_broker_config_template(broker_name: str) -> Path:
    """
    Create a configuration template for a new broker.

    Args:
        broker_name: Name of the broker

    Returns:
        Path to the created config file
    """
    project_root = get_project_root()
    broker_dir = project_root / "src" / "brokers" / broker_name
    broker_dir.mkdir(parents=True, exist_ok=True)

    config_file = broker_dir / "config.yaml"

    template_content = f"""# {broker_name.title()} Broker Configuration
# {"=" * (len(broker_name) + 24)}

# {broker_name.title()} API Configuration
# Add your broker-specific API settings here

# Risk Management ({broker_name.title()}-specific)
max_positions: 10
max_daily_loss: 1000.0
position_size_percent: 0.02  # 2% of portfolio per position
stop_loss_percent: 0.02      # 2% stop loss
take_profit_percent: 0.06    # 6% take profit

# Add other {broker_name.title()}-specific settings here
"""

    with config_file.open("w", encoding="utf-8") as f:
        f.write(template_content)

    return config_file


class Config:
    """
    Configuration class for backward compatibility.
    Consider using load_config() function directly for new code.
    """

    def __init__(self, config_path: Union[str, Path, None] = None):
        self.config_path = resolve_config_path(config_path)
        self.config = load_config(config_path)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with optional default."""
        return self.config.get(key, default)

    def reload(self) -> None:
        """Reload configuration from file."""
        self.config = load_config(self.config_path)
