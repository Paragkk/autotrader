"""
Base Broker Interface and Common Types
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderStatus(Enum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    DONE_FOR_DAY = "done_for_day"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REPLACED = "replaced"
    PENDING_CANCEL = "pending_cancel"
    PENDING_REPLACE = "pending_replace"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    PENDING_NEW = "pending_new"


class TimeInForce(Enum):
    DAY = "day"
    GTC = "gtc"  # Good Till Canceled
    OPG = "opg"  # At The Opening
    CLS = "cls"  # At The Close
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill


@dataclass
class OrderRequest:
    """Standardized order request structure"""

    symbol: str
    quantity: float
    side: OrderSide
    order_type: OrderType
    price: float | None = None
    stop_price: float | None = None
    time_in_force: TimeInForce = TimeInForce.DAY
    extended_hours: bool = False
    take_profit: float | None = None
    stop_loss: float | None = None
    client_order_id: str | None = None


@dataclass
class OrderResponse:
    """Standardized order response structure"""

    order_id: str
    client_order_id: str | None
    symbol: str
    quantity: float
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    filled_qty: float = 0.0
    avg_fill_price: float | None = None
    timestamp: datetime | None = None
    broker_specific_data: dict[str, Any] | None = None


@dataclass
class Position:
    """Standardized position structure"""

    symbol: str
    quantity: float
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_pl_percent: float
    current_price: float
    entry_price: float
    side: str = "long"  # long or short
    broker_specific_data: dict[str, Any] | None = None


@dataclass
class AccountInfo:
    """Standardized account information"""

    account_id: str
    buying_power: float
    cash: float
    portfolio_value: float
    equity: float
    day_trading_power: float
    pattern_day_trader: bool
    broker_specific_data: dict[str, Any] | None = None


@dataclass
class Quote:
    """Standardized quote structure"""

    symbol: str
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    timestamp: datetime
    broker_specific_data: dict[str, Any] | None = None


@dataclass
class BarData:
    """Standardized bar/candle data"""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float | None = None
    trade_count: int | None = None


@dataclass
class MarketData:
    """Standardized market data structure"""

    symbol: str
    price: float
    timestamp: datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None
    vwap: float | None = None
    trade_count: int | None = None
    broker_specific_data: dict[str, Any] | None = None


@dataclass
class Asset:
    """Standardized asset information"""

    symbol: str
    name: str
    exchange: str
    asset_class: str
    tradable: bool = True
    marginable: bool = False
    shortable: bool = False
    easy_to_borrow: bool = False
    fractionable: bool = False
    broker_specific_data: dict[str, Any] | None = None


class BrokerAdapter(ABC):
    """Abstract base class for broker API adapters"""

    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return the broker name"""

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the broker API"""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the broker API"""

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected to broker"""

    # Order Management
    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place a trading order"""

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderResponse | None:
        """Get the status of an order"""

    @abstractmethod
    async def get_orders(self, status: OrderStatus | None = None, limit: int = 100) -> list[OrderResponse]:
        """Get orders with optional status filter"""

    # Account Management
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Get account information"""

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Get all current positions"""

    @abstractmethod
    async def get_position(self, symbol: str) -> Position | None:
        """Get position for a specific symbol"""

    # Market Data
    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote | None:
        """Get real-time quote for a symbol"""

    @abstractmethod
    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Get real-time quotes for multiple symbols"""

    @abstractmethod
    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1D",
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[BarData]:
        """Get historical bar data for a symbol"""

    # Market Status
    @abstractmethod
    async def is_market_open(self) -> bool:
        """Check if market is currently open"""

    @abstractmethod
    async def get_market_hours(self, date: datetime | None = None) -> dict[str, Any]:
        """Get market hours for a specific date"""

    # Watchlists (optional - not all brokers support this)
    async def get_watchlists(self) -> list[dict[str, Any]]:
        """Get user watchlists - optional implementation"""
        return []

    async def create_watchlist(self, name: str, symbols: list[str]) -> bool:
        """Create a new watchlist - optional implementation"""
        return False

    async def add_to_watchlist(self, watchlist_id: str, symbol: str) -> bool:
        """Add symbol to watchlist - optional implementation"""
        return False


class BrokerError(Exception):
    """Base broker error"""


class BrokerConnectionError(BrokerError):
    """Broker connection error"""


class BrokerAuthError(BrokerError):
    """Broker authentication error"""


class BrokerOrderError(BrokerError):
    """Broker order-related error"""


class BrokerDataError(BrokerError):
    """Broker data-related error"""
