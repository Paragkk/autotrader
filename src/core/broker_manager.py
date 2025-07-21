"""
Centralized Broker Manager for Multi-Broker Support
Handles broker initialization, connection, and lifecycle management
"""

import importlib
import logging
from typing import Any

from brokers.base import BrokerAdapter, OrderRequest, OrderResponse
from infra.config import load_config

logger = logging.getLogger(__name__)


class BrokerManager:
    """
    Centralized broker management system
    Only one broker can be connected at a time - the active broker
    All trading operations use the single connected broker
    """

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize broker manager"""
        self.config = load_config(config_path)
        self.available_brokers: dict[str, dict[str, Any]] = {}
        self.active_broker: BrokerAdapter | None = None
        self.active_broker_name: str | None = None

        # Initialize available brokers from config
        self._load_broker_configurations()

    def _load_broker_configurations(self) -> None:
        """Load all available broker configurations"""
        try:
            # Get brokers configuration from main config
            brokers_config = self.config.get("brokers", {})

            for broker_name, broker_config in brokers_config.items():
                if broker_config.get("enabled", False):
                    self.available_brokers[broker_name] = {
                        "config": broker_config,
                        "adapter_class": None,
                        "connected": False,
                    }

            logger.info(f"Loaded {len(self.available_brokers)} broker configurations")

        except Exception as e:
            logger.exception(f"Failed to load broker configurations: {e}")
            raise

    def _get_broker_adapter_class(self, broker_name: str):
        """Dynamically import broker adapter class"""
        try:
            # Map broker names to their module paths
            broker_modules = {
                "alpaca": "src.brokers.alpaca.adapter",
                "demo_broker": "src.brokers.demo_broker.adapter",
                "interactive_brokers": "src.brokers.interactive_brokers.adapter",
            }

            if broker_name not in broker_modules:
                msg = f"Unknown broker: {broker_name}"
                raise ValueError(msg)

            module_path = broker_modules[broker_name]
            module = importlib.import_module(module_path)

            # Get the adapter class (convention: {BrokerName}BrokerAdapter)
            class_name = f"{broker_name.title().replace('_', '')}BrokerAdapter"
            if broker_name == "alpaca":
                class_name = "AlpacaBrokerAdapter"
            elif broker_name == "demo_broker":
                class_name = "DemoBrokerAdapter"
            elif broker_name == "interactive_brokers":
                class_name = "InteractiveBrokersBrokerAdapter"

            return getattr(module, class_name)

        except Exception as e:
            logger.exception(f"Failed to load broker adapter for {broker_name}: {e}")
            raise

    async def connect_broker(self, broker_name: str) -> bool:
        """Connect to a specific broker (disconnects any currently connected broker first)"""
        try:
            if broker_name not in self.available_brokers:
                msg = f"Broker {broker_name} is not configured or enabled"
                raise ValueError(msg)

            # Disconnect current broker if any
            if self.active_broker is not None:
                await self.disconnect_broker()

            # Get broker configuration
            broker_info = self.available_brokers[broker_name]

            # Load adapter class if not already loaded
            if broker_info["adapter_class"] is None:
                broker_info["adapter_class"] = self._get_broker_adapter_class(broker_name)

            # Create adapter instance
            adapter = broker_info["adapter_class"](broker_info["config"])

            # Test connection
            if await adapter.connect():
                # Store as active broker
                self.active_broker = adapter
                self.active_broker_name = broker_name
                broker_info["connected"] = True

                logger.info(f"✅ Successfully connected to {broker_name} (now active broker)")
                return True
            logger.error(f"❌ Failed to connect to {broker_name}")
            return False

        except Exception as e:
            logger.exception(f"Failed to connect to broker {broker_name}: {e}")
            return False

    async def disconnect_broker(self, broker_name: str | None = None) -> None:
        """Disconnect from the active broker"""
        if self.active_broker is not None:
            try:
                # Call disconnect on the adapter
                await self.active_broker.disconnect()

                # Mark as disconnected in available brokers
                if self.active_broker_name in self.available_brokers:
                    self.available_brokers[self.active_broker_name]["connected"] = False

                logger.info(f"Disconnected from {self.active_broker_name}")

                # Clear active broker
                self.active_broker = None
                self.active_broker_name = None

            except Exception as e:
                logger.exception(f"Error disconnecting from {self.active_broker_name}: {e}")

    async def disconnect_all_brokers(self) -> None:
        """Disconnect from the active broker (same as disconnect_broker)"""
        await self.disconnect_broker()

    def get_broker(self, broker_name: str | None = None) -> BrokerAdapter | None:
        """Get the active broker adapter (broker_name parameter ignored for compatibility)"""
        return self.active_broker

    def get_active_broker(self) -> BrokerAdapter | None:
        """Get the active broker adapter"""
        return self.active_broker

    def get_active_broker_name(self) -> str | None:
        """Get the name of the active broker"""
        return self.active_broker_name

    def get_connected_brokers(self) -> list[str]:
        """Get list of currently connected broker names (at most one)"""
        return [self.active_broker_name] if self.active_broker_name else []

    def get_available_brokers(self) -> list[dict[str, Any]]:
        """Get list of available brokers with their status"""
        brokers = []
        for name, info in self.available_brokers.items():
            brokers.append(
                {
                    "name": name,
                    "connected": info["connected"],
                    "display_name": name.replace("_", " ").title(),
                    "paper_trading": info["config"].get("paper_trading", True),
                }
            )
        return brokers

    def is_broker_connected(self, broker_name: str | None = None) -> bool:
        """Check if a broker is connected (if broker_name is None, checks if any broker is connected)"""
        if broker_name is None:
            return self.active_broker is not None
        return self.active_broker_name == broker_name

    def get_connected_brokers_info(self) -> list[dict[str, Any]]:
        """Get detailed info about the connected broker"""
        if not self.active_broker_name:
            return []

        broker_info = self.available_brokers.get(self.active_broker_name, {})
        return [
            {
                "name": self.active_broker_name,
                "display_name": self.active_broker_name.replace("_", " ").title(),
                "connected": True,
                "paper_trading": broker_info.get("config", {}).get("paper_trading", True),
                "broker_type": self.active_broker_name,
            }
        ]

    # Trading Operations - These now use the active broker automatically
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place order through active broker"""
        if not self.active_broker:
            msg = "No broker is currently connected"
            raise RuntimeError(msg)
        return await self.active_broker.place_order(order_request)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order through active broker"""
        if not self.active_broker:
            msg = "No broker is currently connected"
            raise RuntimeError(msg)
        return await self.active_broker.cancel_order(order_id)

    async def get_positions(self):
        """Get all positions from active broker"""
        if not self.active_broker:
            msg = "No broker is currently connected"
            raise RuntimeError(msg)
        return await self.active_broker.get_positions()

    async def get_orders(self, **kwargs):
        """Get orders from active broker"""
        if not self.active_broker:
            msg = "No broker is currently connected"
            raise RuntimeError(msg)
        return await self.active_broker.get_orders(**kwargs)

    async def get_account_info(self):
        """Get account info from active broker"""
        if not self.active_broker:
            msg = "No broker is currently connected"
            raise RuntimeError(msg)
        return await self.active_broker.get_account_info()

    async def get_quote(self, symbol: str):
        """Get quote from active broker"""
        if not self.active_broker:
            msg = "No broker is currently connected"
            raise RuntimeError(msg)
        return await self.active_broker.get_quote(symbol)

    async def get_current_price(self, symbol: str):
        """Get current price from active broker"""
        if not self.active_broker:
            msg = "No broker is currently connected"
            raise RuntimeError(msg)
        return await self.active_broker.get_current_price(symbol)

    async def get_position(self, symbol: str):
        """Get position for specific symbol from active broker"""
        if not self.active_broker:
            msg = "No broker is currently connected"
            raise RuntimeError(msg)
        return await self.active_broker.get_position(symbol)

    async def is_market_open(self) -> bool:
        """Check if market is open via active broker"""
        if not self.active_broker:
            msg = "No broker is currently connected"
            raise RuntimeError(msg)
        return await self.active_broker.is_market_open()

    async def get_market_clock(self):
        """Get market clock from active broker"""
        if not self.active_broker:
            msg = "No broker is currently connected"
            raise RuntimeError(msg)
        return await self.active_broker.get_market_clock()


# Global broker manager instance
_broker_manager: BrokerManager | None = None


def get_broker_manager() -> BrokerManager:
    """Get global broker manager instance"""
    global _broker_manager
    if _broker_manager is None:
        _broker_manager = BrokerManager()
    return _broker_manager


async def initialize_default_brokers() -> bool:
    """Initialize and connect to the first available default broker"""
    import os

    broker_manager = get_broker_manager()

    # Get list of brokers to try to connect to
    default_brokers = os.getenv("DEFAULT_BROKERS", "alpaca,demo_broker").split(",")
    default_brokers = [broker.strip() for broker in default_brokers]

    logger.info(f"Attempting to connect to first available broker from: {default_brokers}")

    for broker_name in default_brokers:
        try:
            if await broker_manager.connect_broker(broker_name):
                logger.info(f"✅ Connected to {broker_name} as active broker")
                return True
            logger.warning(f"❌ Failed to connect to {broker_name}")
        except Exception as e:
            logger.warning(f"❌ Error connecting to {broker_name}: {e}")

    logger.warning("⚠️ No brokers could be connected")
    return False
