"""
Broker Factory for Creating Broker Adapters
"""

from typing import Dict, Any, List
import logging
import importlib
from .interface import BrokerAdapter
from .config import BrokerConfigLoader

logger = logging.getLogger(__name__)


class BrokerFactory:
    """Factory for creating broker adapter instances"""

    def __init__(self):
        """Initialize the broker factory"""
        self.config_loader = BrokerConfigLoader()

    def create_broker(
        self, broker_name: str, global_config: Dict[str, Any]
    ) -> BrokerAdapter:
        """
        Create a broker instance based on broker name

        Args:
            broker_name: Name of the broker (e.g., "alpaca", "interactive_brokers")
            global_config: Global configuration dictionary for the broker

        Returns:
            BrokerAdapter: Broker instance

        Raises:
            ValueError: If broker name is not supported
            ImportError: If broker adapter module cannot be imported
        """
        # Check if broker is available
        if not self.is_broker_available(broker_name):
            available = self.get_supported_brokers()
            raise ValueError(
                f"Unsupported broker: {broker_name}. Available brokers: {available}"
            )

        try:
            # Load broker-specific configuration
            broker_config = self.config_loader.load_broker_config(broker_name)

            # Merge with global config (global config takes precedence)
            merged_config = self.config_loader.merge_with_global_config(
                broker_config, global_config
            )

            # Validate the merged configuration
            if not self.config_loader.validate_broker_config(
                broker_name, merged_config
            ):
                raise ValueError(f"Invalid configuration for broker: {broker_name}")

            # Dynamically import the broker adapter
            adapter_module = importlib.import_module(f"brokers.{broker_name}.adapter")

            # Find the adapter class (convention: {BrokerName}BrokerAdapter)
            adapter_class_name = f"{broker_name.title()}BrokerAdapter"

            if not hasattr(adapter_module, adapter_class_name):
                raise ImportError(
                    f"Adapter class {adapter_class_name} not found in {adapter_module}"
                )

            adapter_class = getattr(adapter_module, adapter_class_name)

            # Create and return the adapter instance
            logger.info(f"✅ Creating {broker_name} broker adapter")
            return adapter_class(merged_config)

        except Exception as e:
            logger.error(f"❌ Failed to create {broker_name} broker adapter: {e}")
            raise

    def get_supported_brokers(self) -> List[str]:
        """
        Get list of supported broker names

        Returns:
            List of supported broker names
        """
        return self.config_loader.get_available_brokers()

    def is_broker_available(self, broker_name: str) -> bool:
        """Check if a broker is available"""
        return broker_name.lower() in self.get_supported_brokers()


# Global broker factory instance
_broker_factory = BrokerFactory()


def get_broker_adapter(broker_name: str, config: Dict[str, Any]) -> BrokerAdapter:
    """Convenience function to create a broker adapter"""
    return _broker_factory.create_broker(broker_name, config)


def get_supported_brokers() -> List[str]:
    """Convenience function to get supported brokers"""
    return _broker_factory.get_supported_brokers()


def is_broker_available(broker_name: str) -> bool:
    """Convenience function to check if a broker is available"""
    return _broker_factory.is_broker_available(broker_name)
