"""
Multi-Broker Management Service
Coordinates operations across multiple brokers using a single database
"""

import logging
from dataclasses import dataclass
from datetime import datetime

# Import for type hinting
from typing import TYPE_CHECKING, Any

from src.brokers.base import BrokerAdapter
from src.db.models import BrokerAccount, Order, Position
from src.infra.config import create_broker_adapter

if TYPE_CHECKING:
    from src.db.repository import BrokerRepository

logger = logging.getLogger(__name__)


@dataclass
class BrokerAllocation:
    """Broker allocation configuration"""

    broker_name: str
    allocation_percent: float
    adapter: BrokerAdapter


class MultiBrokerManager:
    """
    Manages multiple brokers using a unified database approach
    """

    def __init__(self, config: dict[str, Any], repository: "BrokerRepository") -> None:
        self.config = config
        self.repository = repository
        self.brokers: dict[str, BrokerAllocation] = {}

        # Initialize brokers
        self._initialize_brokers()

    def _initialize_brokers(self) -> None:
        """Initialize all configured brokers"""
        brokers_config = self.config.get("brokers", {})

        for broker_name, broker_config in brokers_config.items():
            try:
                # Create broker adapter
                adapter = create_broker_adapter(broker_name, broker_config)

                # Create allocation
                allocation = BrokerAllocation(
                    broker_name=broker_name,
                    allocation_percent=broker_config.get("allocation_percent", 0.0),
                    adapter=adapter,
                )

                self.brokers[broker_name] = allocation
                logger.info(f"✅ Initialized broker: {broker_name} ({allocation.allocation_percent * 100}% allocation)")

            except Exception as e:
                logger.exception(f"❌ Failed to initialize broker {broker_name}: {e}")

    async def connect_all_brokers(self) -> dict[str, bool]:
        """Connect to all configured brokers"""
        results = {}

        for broker_name, allocation in self.brokers.items():
            try:
                success = await allocation.adapter.connect()
                results[broker_name] = success

                if success:
                    # Update broker account info in database
                    await self._update_broker_account_info(broker_name, allocation.adapter)
                    logger.info(f"✅ Connected to {broker_name}")
                else:
                    logger.error(f"❌ Failed to connect to {broker_name}")

            except Exception as e:
                logger.exception(f"❌ Error connecting to {broker_name}: {e}")
                results[broker_name] = False

        return results

    async def _update_broker_account_info(self, broker_name: str, adapter: BrokerAdapter) -> None:
        """Update broker account information in database"""
        try:
            account_info = await adapter.get_account_info()

            # Check if broker account exists
            existing_account = self.repository.get_broker_account(broker_name)

            if existing_account:
                # Update existing account
                self.repository.update_broker_account(
                    broker_name=broker_name,
                    account_data={
                        "account_id": account_info.account_id,
                        "buying_power": account_info.buying_power,
                        "cash": account_info.cash,
                        "portfolio_value": account_info.portfolio_value,
                        "equity": account_info.equity,
                        "day_trading_power": account_info.day_trading_power,
                        "pattern_day_trader": account_info.pattern_day_trader,
                        "last_updated": datetime.now(),
                    },
                )
            else:
                # Create new account record
                broker_account = BrokerAccount(
                    broker_name=broker_name,
                    account_id=account_info.account_id,
                    buying_power=account_info.buying_power,
                    cash=account_info.cash,
                    portfolio_value=account_info.portfolio_value,
                    equity=account_info.equity,
                    day_trading_power=account_info.day_trading_power,
                    pattern_day_trader=account_info.pattern_day_trader,
                    paper_trading=self.brokers[broker_name].adapter.paper_trading if hasattr(self.brokers[broker_name].adapter, "paper_trading") else True,
                )
                self.repository.create_broker_account(broker_account)

        except Exception as e:
            logger.exception(f"Failed to update account info for {broker_name}: {e}")

    async def place_order_smart(
        self,
        symbol: str,
        quantity: float,
        order_type: str,
        price: float | None = None,
        broker_preference: str | None = None,
    ) -> tuple[str, str]:
        """
        Place order using smart broker selection
        Returns: (broker_name, order_id)
        """
        # Determine which broker to use
        broker_name = broker_preference or self._select_optimal_broker(symbol, quantity)

        if broker_name not in self.brokers:
            msg = f"Broker {broker_name} not available"
            raise ValueError(msg)

        adapter = self.brokers[broker_name].adapter

        # Create order request (you'll need to adapt this based on your OrderRequest structure)
        from src.brokers.base.interface import OrderRequest, OrderSide
        from src.brokers.base.interface import OrderType as OT

        order_request = OrderRequest(
            symbol=symbol,
            side=OrderSide.BUY,  # You'll need to determine this
            quantity=quantity,
            order_type=OT.MARKET if order_type == "market" else OT.LIMIT,
            price=price,
        )

        # Place order through broker
        response = await adapter.place_order(order_request)

        # Store order in database with broker info
        order_record = Order(
            broker_name=broker_name,
            broker_order_id=response.order_id,
            symbol=symbol,
            side=order_request.side.value,
            quantity=quantity,
            order_type=order_type,
            price=price,
            status=response.status.value if hasattr(response.status, "value") else str(response.status),
        )

        self.repository.create_order(order_record)

        logger.info(f"📈 Order placed: {symbol} x{quantity} via {broker_name} (Order ID: {response.order_id})")

        return broker_name, response.order_id

    def _select_optimal_broker(self, symbol: str, quantity: float) -> str:
        """
        Select optimal broker based on allocation, availability, and capacity
        """
        # Enhanced implementation - select based on allocation and availability
        # You can enhance this with more sophisticated logic:
        # - Check broker allocations
        # - Check available buying power
        # - Check broker-specific symbol availability
        # - Load balancing based on current exposure

        # Get all available brokers
        available_brokers = []
        for broker_name, _allocation in self.brokers.items():
            available_brokers.append(broker_name)

        if not available_brokers:
            msg = "No brokers available. Please configure at least one broker."
            raise RuntimeError(msg)

        # For now, return the first available broker
        # TODO: Implement more sophisticated broker selection logic based on:
        # - Available capital allocation
        # - Current position exposure
        # - Broker-specific fees and capabilities
        return available_brokers[0]

    async def get_consolidated_positions(self) -> list[dict[str, Any]]:
        """Get consolidated positions across all brokers"""
        all_positions = []

        for broker_name, allocation in self.brokers.items():
            try:
                positions = await allocation.adapter.get_positions()

                for position in positions:
                    # Store/update position in database
                    position_record = Position(
                        broker_name=broker_name,
                        symbol=position.symbol,
                        quantity=position.quantity,
                        side="long" if position.quantity > 0 else "short",
                        avg_entry_price=getattr(position, "entry_price", 0.0),
                        unrealized_pnl=getattr(position, "unrealized_pl", 0.0),
                        status="open",
                    )

                    # You'll need to implement upsert logic in repository
                    self.repository.upsert_position(position_record)

                    all_positions.append(
                        {
                            "broker": broker_name,
                            "symbol": position.symbol,
                            "quantity": position.quantity,
                            "market_value": getattr(position, "market_value", 0.0),
                            "unrealized_pnl": getattr(position, "unrealized_pl", 0.0),
                        }
                    )

            except Exception as e:
                logger.exception(f"Failed to get positions from {broker_name}: {e}")

        return all_positions

    async def get_total_portfolio_value(self) -> float:
        """Get total portfolio value across all brokers"""
        total_value = 0.0

        for broker_name, allocation in self.brokers.items():
            try:
                account_info = await allocation.adapter.get_account_info()
                total_value += account_info.portfolio_value

            except Exception as e:
                logger.exception(f"Failed to get portfolio value from {broker_name}: {e}")

        return total_value

    def get_broker_allocations(self) -> dict[str, float]:
        """Get current broker allocation percentages"""
        return {broker_name: allocation.allocation_percent for broker_name, allocation in self.brokers.items()}

    async def rebalance_allocations(self) -> None:
        """Rebalance portfolio across brokers (advanced feature)"""
        # This would be a complex algorithm to rebalance positions
        # across brokers based on target allocations
        logger.info("Rebalancing across brokers - feature to be implemented")

    async def disconnect_all_brokers(self) -> None:
        """Disconnect from all brokers"""
        for broker_name, allocation in self.brokers.items():
            try:
                await allocation.adapter.disconnect()
                logger.info(f"Disconnected from {broker_name}")
            except Exception as e:
                logger.exception(f"Error disconnecting from {broker_name}: {e}")

    def get_primary_broker(self) -> BrokerAdapter | None:
        """
        Get the primary broker adapter (highest allocation broker)
        Returns None if no brokers are available
        """
        if not self.brokers:
            return None

        # Find the broker with the highest allocation percentage
        primary_broker = max(self.brokers.values(), key=lambda allocation: allocation.allocation_percent)

        return primary_broker.adapter

    def get_configured_brokers(self) -> list[str]:
        """Get list of configured broker names"""
        return list(self.brokers.keys())
