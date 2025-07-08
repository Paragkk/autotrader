"""
Generic Broker Configuration System
"""

import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class BrokerConfigLoader:
    """Generic broker configuration loader"""

    def __init__(self, brokers_root_path: Optional[Path] = None):
        """
        Initialize the broker config loader

        Args:
            brokers_root_path: Path to the brokers directory. If None, uses current file's parent directory
        """
        if brokers_root_path is None:
            # Default to the brokers directory
            self.brokers_root_path = Path(__file__).parent.parent
        else:
            self.brokers_root_path = Path(brokers_root_path)

    def load_broker_config(self, broker_name: str) -> Dict[str, Any]:
        """
        Load configuration for a specific broker

        Args:
            broker_name: Name of the broker (e.g., 'alpaca', 'interactive_brokers')

        Returns:
            Dictionary containing broker-specific configuration

        Raises:
            FileNotFoundError: If broker directory or config file doesn't exist
            ValueError: If config file is invalid
        """
        broker_dir = self.brokers_root_path / broker_name
        config_file = broker_dir / "config.yaml"

        if not broker_dir.exists():
            raise FileNotFoundError(f"Broker directory not found: {broker_dir}")

        if not config_file.exists():
            raise FileNotFoundError(f"Broker config file not found: {config_file}")

        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)

            if not isinstance(config, dict):
                raise ValueError(f"Invalid config format in {config_file}")

            logger.info(f"✅ Loaded configuration for broker: {broker_name}")
            return config

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_file}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading config from {config_file}: {e}")

    def get_available_brokers(self) -> list[str]:
        """
        Get list of available brokers based on directory structure

        Returns:
            List of broker names that have both a directory and config.yaml file
        """
        available_brokers = []

        if not self.brokers_root_path.exists():
            logger.warning(
                f"Brokers root path does not exist: {self.brokers_root_path}"
            )
            return available_brokers

        for item in self.brokers_root_path.iterdir():
            if item.is_dir() and item.name != "base" and not item.name.startswith("__"):
                config_file = item / "config.yaml"
                adapter_file = item / "adapter.py"

                if config_file.exists() and adapter_file.exists():
                    available_brokers.append(item.name)
                else:
                    logger.debug(
                        f"Skipping {item.name}: missing config.yaml or adapter.py"
                    )

        return sorted(available_brokers)

    def validate_broker_config(self, broker_name: str, config: Dict[str, Any]) -> bool:
        """
        Validate broker configuration

        Args:
            broker_name: Name of the broker
            config: Configuration dictionary to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        # Basic validation - can be extended per broker
        required_fields = {
            "alpaca": ["alpaca_api_key", "alpaca_secret_key", "base_url"],
            "demo_broker": ["demo_api_key", "demo_secret_key", "base_url"],
            # Add other brokers as needed
        }

        if broker_name in required_fields:
            missing_fields = []
            broker_specific_fields = required_fields[broker_name]

            # Check broker-specific fields first
            for field in broker_specific_fields:
                if field not in config:
                    # Check if generic equivalent exists
                    if field.endswith("_api_key") and "api_key" not in config:
                        missing_fields.append(f"{field} or api_key")
                    elif field.endswith("_secret_key") and (
                        "secret_key" not in config and "api_secret" not in config
                    ):
                        missing_fields.append(f"{field} or secret_key or api_secret")
                    elif field not in [
                        "alpaca_api_key",
                        "alpaca_secret_key",
                        "demo_api_key",
                        "demo_secret_key",
                    ]:
                        missing_fields.append(field)

            # Check for generic fields if broker-specific ones are missing
            if (
                not any(key.endswith("_api_key") for key in config.keys())
                and "api_key" not in config
            ):
                if f"{broker_name}_api_key" not in config:
                    missing_fields.append("api_key")

            if (
                not any(key.endswith("_secret_key") for key in config.keys())
                and "secret_key" not in config
                and "api_secret" not in config
            ):
                if f"{broker_name}_secret_key" not in config:
                    missing_fields.append("secret_key or api_secret")

            if missing_fields:
                logger.error(
                    f"Missing required fields for {broker_name}: {missing_fields}"
                )
                return False
        else:
            # For unknown brokers, just check for generic required fields
            missing_fields = []
            has_api_key = any(
                key in config for key in ["api_key", f"{broker_name}_api_key"]
            )
            has_secret = any(
                key in config
                for key in ["secret_key", "api_secret", f"{broker_name}_secret_key"]
            )

            if not has_api_key:
                missing_fields.append("api_key")
            if not has_secret:
                missing_fields.append("secret_key or api_secret")

            if missing_fields:
                logger.warning(
                    f"Unknown broker '{broker_name}', checking generic fields. Missing: {missing_fields}"
                )
                return False

        logger.info(f"✅ Configuration validated for broker: {broker_name}")
        return True

    def merge_with_global_config(
        self, broker_config: Dict[str, Any], global_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge broker-specific config with global broker config

        Args:
            broker_config: Broker-specific configuration
            global_config: Global broker configuration from main config.yaml

        Returns:
            Merged configuration with global config taking precedence
        """
        merged_config = broker_config.copy()

        # Override with global config values
        for key, value in global_config.items():
            if key != "name":  # Don't override the broker name
                merged_config[key] = value

        # Special handling for API credentials - ensure generic keys override specific ones
        if "api_key" in merged_config and "alpaca_api_key" in merged_config:
            merged_config["alpaca_api_key"] = merged_config["api_key"]
        if "secret_key" in merged_config and "alpaca_secret_key" in merged_config:
            merged_config["alpaca_secret_key"] = merged_config["secret_key"]

        return merged_config
