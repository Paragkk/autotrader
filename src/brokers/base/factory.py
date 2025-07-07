"""
Broker Factory for Creating Broker Adapters
"""

from typing import Dict, Any, List
import logging
from .interface import BrokerAdapter

logger = logging.getLogger(__name__)


class BrokerFactory:
    """Factory for creating broker adapter instances"""

    @staticmethod
    def create_broker(broker_name: str, config: Dict[str, Any]) -> BrokerAdapter:
        """
        Create a broker instance based on broker name

        Args:
            broker_name: Name of the broker ("alpaca")
            config: Configuration dictionary for the broker

        Returns:
            BrokerInterface: Broker instance

        Raises:
            ValueError: If broker name is not supported
        """
        if broker_name == "alpaca":
            from ..alpaca.adapter import AlpacaBrokerAdapter

            return AlpacaBrokerAdapter(config)

        else:
            raise ValueError(f"Unsupported broker: {broker_name}")

    @staticmethod
    def get_supported_brokers() -> List[str]:
        """
        Get list of supported broker names

        Returns:
            List of supported broker names
        """
        return ["alpaca"]

    @staticmethod
    def is_broker_available(broker_name: str) -> bool:
        """Check if a broker is available"""
        return broker_name.lower() in BrokerFactory.get_supported_brokers()


def get_broker_adapter(broker_name: str, config: Dict[str, Any]) -> BrokerAdapter:
    """Convenience function to create a broker adapter"""
    return BrokerFactory.create_broker(broker_name, config)
