"""
Base Broker Adapter - Unified Interface for All Brokers
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from .interface import (
    AccountInfo,
    Asset,
    MarketData,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    OrderType,
    Position,
)


class BrokerAdapter(ABC):
    """Abstract base class for all broker adapters"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.paper_trading = config.get("paper_trading", True)
        self.authenticated = False

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with broker"""

    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """Get account information"""

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Get all positions"""

    @abstractmethod
    def get_position(self, symbol: str) -> Position | None:
        """Get position for specific symbol"""

    @abstractmethod
    def submit_order(self, order: OrderRequest) -> OrderResponse:
        """Submit an order"""

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""

    @abstractmethod
    def get_order(self, order_id: str) -> OrderResponse | None:
        """Get order status"""

    @abstractmethod
    def get_orders(self, status: OrderStatus | None = None) -> list[OrderResponse]:
        """Get all orders with optional status filter"""

    @abstractmethod
    def get_assets(self) -> list[Asset]:
        """Get all tradeable assets"""

    @abstractmethod
    def get_asset(self, symbol: str) -> Asset | None:
        """Get asset information for symbol"""

    @abstractmethod
    def get_market_data(self, symbol: str) -> MarketData | None:
        """Get current market data for symbol"""

    @abstractmethod
    def get_historical_bars(self, symbol: str, start: str, end: str, timeframe: str = "1day") -> list[MarketData]:
        """Get historical market data"""

    @abstractmethod
    def is_market_open(self) -> bool:
        """Check if market is open"""

    @abstractmethod
    def get_market_calendar(self, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        """Get market calendar"""

    def validate_order(self, order: OrderRequest) -> bool:
        """Validate order before submission"""
        # Basic validation
        if not order.symbol:
            return False
        if order.quantity <= 0:
            return False
        if order.order_type == OrderType.LIMIT and not order.price:
            return False
        if order.order_type == OrderType.STOP and not order.stop_price:
            return False
        return not (order.order_type == OrderType.STOP_LIMIT and (not order.price or not order.stop_price))

    def get_buying_power(self) -> float:
        """Get available buying power"""
        account = self.get_account_info()
        return account.buying_power if account else 0.0

    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        account = self.get_account_info()
        return account.portfolio_value if account else 0.0

    def calculate_position_size(self, symbol: str, percentage: float) -> float:
        """Calculate position size based on percentage of portfolio"""
        portfolio_value = self.get_portfolio_value()
        if portfolio_value <= 0:
            return 0.0

        market_data = self.get_market_data(symbol)
        if not market_data:
            return 0.0

        position_value = portfolio_value * percentage
        shares = position_value / market_data.price
        return max(0, int(shares))  # Return whole shares

    def get_connection_status(self) -> dict[str, Any]:
        """Get connection status info"""
        return {
            "authenticated": self.authenticated,
            "paper_trading": self.paper_trading,
            "last_check": datetime.now().isoformat(),
        }
