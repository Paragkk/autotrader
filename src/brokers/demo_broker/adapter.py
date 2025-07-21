"""
Demo Broker Adapter Implementation
This is an example of how to create a new broker adapter
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from ..base import (
    AccountInfo,
    BarData,
    BrokerAdapter,
    BrokerConnectionError,
    OrderRequest,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Quote,
)

logger = logging.getLogger(__name__)


class DemoBrokerAdapter(BrokerAdapter):
    """Demo broker adapter implementation - serves as a template for new brokers"""

    @property
    def broker_name(self) -> str:
        """Return the broker name"""
        return "demo_broker"

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialize Demo broker adapter with configuration

        Args:
            config: Configuration dictionary containing Demo broker settings
        """
        # Extract required configuration
        self.api_key = config.get("api_key") or config.get("demo_api_key")
        self.api_secret = config.get("api_secret") or config.get("secret_key") or config.get("demo_secret_key")
        self.paper_trading = config.get("paper_trading", config.get("use_paper_trading", True))
        self.base_url = config.get("base_url", "https://demo-api.example.com")

        # Validate required fields
        if not self.api_key:
            msg = "Missing required configuration: api_key or demo_api_key"
            raise ValueError(msg)
        if not self.api_secret:
            msg = "Missing required configuration: api_secret, secret_key, or demo_secret_key"
            raise ValueError(msg)

        # Store full config for other settings
        self.config = config
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Demo Broker API"""
        try:
            # Simulate connection logic
            logger.info(f"Connecting to Demo Broker at {self.base_url}")
            logger.info(f"Paper trading: {self.paper_trading}")

            # In a real implementation, you would:
            # 1. Initialize the broker's API client
            # 2. Test authentication
            # 3. Verify account access

            self._connected = True
            logger.info("✅ Connected to Demo Broker successfully")
            return True

        except Exception as e:
            logger.exception(f"❌ Failed to connect to Demo Broker: {e}")
            self._connected = False
            msg = f"Demo broker connection failed: {e}"
            raise BrokerConnectionError(msg)

    async def disconnect(self) -> None:
        """Disconnect from Demo Broker API"""
        if self._connected:
            logger.info("Disconnecting from Demo Broker")
            # In a real implementation, clean up connections here
            self._connected = False

    async def is_connected(self) -> bool:
        """Check if connected to Demo Broker"""
        return self._connected

    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate account info
        return AccountInfo(
            account_id="demo_account_123",
            buying_power=50000.0,
            cash=25000.0,
            portfolio_value=75000.0,
            equity=75000.0,
            day_trading_power=100000.0,
            pattern_day_trader=False,
            broker_specific_data={"demo": True},
        )

    async def get_positions(self) -> list[Position]:
        """Get current positions"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate empty positions for demo
        return []

    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place an order"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate order placement
        logger.info(f"Demo Broker: Placing {order_request.side} order for {order_request.quantity} shares of {order_request.symbol}")

        return OrderResponse(
            order_id=f"demo_order_{datetime.now().timestamp()}",
            client_order_id=order_request.client_order_id,
            symbol=order_request.symbol,
            quantity=order_request.quantity,
            side=order_request.side,
            order_type=order_request.order_type,
            status=OrderStatus.FILLED,
            filled_qty=order_request.quantity,
            avg_fill_price=100.0,
            timestamp=datetime.now(),
        )

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        logger.info(f"Demo Broker: Cancelling order {order_id}")
        return True

    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get order status"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate order status
        return OrderResponse(
            order_id=order_id,
            client_order_id=None,
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.FILLED,
            filled_qty=100,
            avg_fill_price=100.0,
            timestamp=datetime.now(),
        )

    async def get_quote(self, symbol: str) -> Quote:
        """Get current quote for symbol"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate quote data
        return Quote(symbol=symbol, bid=99.50, ask=100.50, last=100.00, timestamp=datetime.now())

    async def get_bars(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> list[BarData]:
        """Get historical bar data"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate bar data
        bars = []
        current = start
        while current <= end:
            bars.append(
                BarData(
                    symbol=symbol,
                    timestamp=current,
                    open=100.0,
                    high=105.0,
                    low=95.0,
                    close=102.0,
                    volume=10000,
                )
            )
            current += timedelta(days=1)

        return bars

    async def get_watchlists(self) -> list[dict[str, Any]]:
        """Get account watchlists"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate watchlist
        return [
            {
                "id": "demo_watchlist",
                "name": "Demo Watchlist",
                "symbols": ["DEMO1", "DEMO2", "DEMO3"],
            }
        ]

    async def get_orders(self, symbol: str | None = None, status: str | None = None, limit: int = 100) -> list[OrderResponse]:
        """Get account orders"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate order data
        return [
            OrderResponse(
                order_id="demo_order_1",
                symbol="DEMO1",
                side=OrderSide.BUY,
                quantity=10,
                order_type=OrderType.MARKET,
                status=OrderStatus.FILLED,
                filled_quantity=10,
                filled_price=100.0,
                created_at=datetime.now() - timedelta(hours=1),
                updated_at=datetime.now(),
            )
        ]

    async def get_position(self, symbol: str) -> Position | None:
        """Get position for specific symbol"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate position data
        return Position(
            symbol=symbol,
            quantity=10,
            avg_price=100.0,
            market_value=1000.0,
            unrealized_pnl=50.0,
            side="long",
            created_at=datetime.now() - timedelta(hours=2),
            updated_at=datetime.now(),
        )

    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Get quotes for multiple symbols"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate quotes for multiple symbols
        quotes = {}
        for symbol in symbols:
            quotes[symbol] = Quote(
                symbol=symbol,
                bid=99.50,
                ask=100.50,
                last=100.00,
                timestamp=datetime.now(),
            )
        return quotes

    async def is_market_open(self) -> bool:
        """Check if market is open"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate market hours (always open for demo)
        return True

    async def get_market_hours(self, date: datetime | None = None) -> dict[str, Any]:
        """Get market hours for a specific date"""
        if not self._connected:
            msg = "Not connected to Demo Broker"
            raise BrokerConnectionError(msg)

        # Simulate market hours
        return {
            "date": date.strftime("%Y-%m-%d") if date else datetime.now().strftime("%Y-%m-%d"),
            "is_open": True,
            "market_open": "09:30:00",
            "market_close": "16:00:00",
            "timezone": "America/New_York",
        }
