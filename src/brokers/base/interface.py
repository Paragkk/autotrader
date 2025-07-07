"""
Base Broker Interface and Common Types
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    extended_hours: bool = False
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    client_order_id: Optional[str] = None


@dataclass
class OrderResponse:
    """Standardized order response structure"""

    order_id: str
    client_order_id: Optional[str]
    symbol: str
    quantity: float
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    filled_qty: float = 0.0
    avg_fill_price: Optional[float] = None
    timestamp: Optional[datetime] = None
    broker_specific_data: Optional[Dict[str, Any]] = None


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
    broker_specific_data: Optional[Dict[str, Any]] = None


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
    broker_specific_data: Optional[Dict[str, Any]] = None


@dataclass
class Quote:
    """Standardized quote structure"""

    symbol: str
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    timestamp: datetime
    broker_specific_data: Optional[Dict[str, Any]] = None


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
    vwap: Optional[float] = None
    trade_count: Optional[int] = None


@dataclass
class MarketData:
    """Standardized market data structure"""

    symbol: str
    price: float
    timestamp: datetime
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    vwap: Optional[float] = None
    trade_count: Optional[int] = None
    broker_specific_data: Optional[Dict[str, Any]] = None


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
    broker_specific_data: Optional[Dict[str, Any]] = None


class BrokerAdapter(ABC):
    """Abstract base class for broker API adapters"""

    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return the broker name"""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the broker API"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the broker API"""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected to broker"""
        pass

    # Order Management
    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place a trading order"""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[OrderResponse]:
        """Get the status of an order"""
        pass

    @abstractmethod
    async def get_orders(
        self, status: Optional[OrderStatus] = None, limit: int = 100
    ) -> List[OrderResponse]:
        """Get orders with optional status filter"""
        pass

    # Account Management
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all current positions"""
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        pass

    # Market Data
    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote for a symbol"""
        pass

    @abstractmethod
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get real-time quotes for multiple symbols"""
        pass

    @abstractmethod
    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1D",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[BarData]:
        """Get historical bar data for a symbol"""
        pass

    # Market Status
    @abstractmethod
    async def is_market_open(self) -> bool:
        """Check if market is currently open"""
        pass

    @abstractmethod
    async def get_market_hours(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get market hours for a specific date"""
        pass

    # Watchlists (optional - not all brokers support this)
    async def get_watchlists(self) -> List[Dict[str, Any]]:
        """Get user watchlists - optional implementation"""
        return []

    async def create_watchlist(self, name: str, symbols: List[str]) -> bool:
        """Create a new watchlist - optional implementation"""
        return False

    async def add_to_watchlist(self, watchlist_id: str, symbol: str) -> bool:
        """Add symbol to watchlist - optional implementation"""
        return False


class BrokerError(Exception):
    """Base broker error"""

    pass


class BrokerConnectionError(BrokerError):
    """Broker connection error"""

    pass


class BrokerAuthError(BrokerError):
    """Broker authentication error"""

    pass


class BrokerOrderError(BrokerError):
    """Broker order-related error"""

    pass


class BrokerDataError(BrokerError):
    """Broker data-related error"""

    pass
