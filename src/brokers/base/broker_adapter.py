"""
Base Broker Adapter - Unified Interface for All Brokers
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from .interface import (
    OrderRequest,
    OrderResponse,
    Position,
    AccountInfo,
    MarketData,
    Asset,
    OrderType,
    OrderStatus,
)


class BrokerAdapter(ABC):
    """Abstract base class for all broker adapters"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.paper_trading = config.get("paper_trading", True)
        self.authenticated = False

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with broker"""
        pass

    @abstractmethod
    def get_account_info(self) -> AccountInfo:
        """Get account information"""
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get all positions"""
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for specific symbol"""
        pass

    @abstractmethod
    def submit_order(self, order: OrderRequest) -> OrderResponse:
        """Submit an order"""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[OrderResponse]:
        """Get order status"""
        pass

    @abstractmethod
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[OrderResponse]:
        """Get all orders with optional status filter"""
        pass

    @abstractmethod
    def get_assets(self) -> List[Asset]:
        """Get all tradeable assets"""
        pass

    @abstractmethod
    def get_asset(self, symbol: str) -> Optional[Asset]:
        """Get asset information for symbol"""
        pass

    @abstractmethod
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get current market data for symbol"""
        pass

    @abstractmethod
    def get_historical_bars(
        self, symbol: str, start: str, end: str, timeframe: str = "1day"
    ) -> List[MarketData]:
        """Get historical market data"""
        pass

    @abstractmethod
    def is_market_open(self) -> bool:
        """Check if market is open"""
        pass

    @abstractmethod
    def get_market_calendar(
        self, start: str = None, end: str = None
    ) -> List[Dict[str, Any]]:
        """Get market calendar"""
        pass

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
        if order.order_type == OrderType.STOP_LIMIT and (
            not order.price or not order.stop_price
        ):
            return False
        return True

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

    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection status info"""
        return {
            "authenticated": self.authenticated,
            "paper_trading": self.paper_trading,
            "last_check": datetime.now().isoformat(),
        }
