"""
Refactored Alpaca Broker Adapter - Simplified Implementation
Uses common infrastructure and removes duplicated code
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ..base import (
    OrderRequest,
    OrderResponse,
    Position,
    AccountInfo,
    Quote,
    BarData,
    OrderType,
    OrderStatus,
    BrokerConnectionError,
    BrokerOrderError,
    BrokerDataError,
)
from ..common import RESTBrokerAdapter, OrderValidationMixin, PositionTrackingMixin
from ...infra.model_utils import create_dataclass_from_dict

logger = logging.getLogger(__name__)


class AlpacaBrokerAdapter(
    RESTBrokerAdapter, OrderValidationMixin, PositionTrackingMixin
):
    """Simplified Alpaca broker adapter using common infrastructure"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Alpaca broker adapter"""
        super().__init__(config)

        # Extract Alpaca-specific configuration
        self.api_key = config.get("api_key") or config.get("alpaca_api_key")
        self.api_secret = (
            config.get("api_secret")
            or config.get("secret_key")
            or config.get("alpaca_secret_key")
        )
        self.paper_trading = config.get(
            "paper_trading", config.get("use_paper_trading", True)
        )

        # Validate credentials
        self._validate_credentials()

    @property
    def broker_name(self) -> str:
        return "alpaca"

    @property
    def base_url(self) -> str:
        if self.paper_trading:
            return "https://paper-api.alpaca.markets/v2"
        return "https://api.alpaca.markets/v2"

    @property
    def auth_headers(self) -> Dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Content-Type": "application/json",
        }

    def _validate_credentials(self):
        """Validate API credentials"""
        if not self.api_key or self.api_key == "your_alpaca_api_key_here":
            raise ValueError(
                "Missing or invalid ALPACA_API_KEY. Please:\n"
                "1. Sign up for Alpaca paper trading at https://app.alpaca.markets\n"
                "2. Get your API key from the dashboard\n"
                "3. Set ALPACA_API_KEY in your .env file"
            )
        if not self.api_secret or self.api_secret == "your_alpaca_secret_key_here":
            raise ValueError(
                "Missing or invalid ALPACA_SECRET_KEY. Please:\n"
                "1. Sign up for Alpaca paper trading at https://app.alpaca.markets\n"
                "2. Get your secret key from the dashboard\n"
                "3. Set ALPACA_SECRET_KEY in your .env file"
            )

    async def connect(self) -> bool:
        """Connect to Alpaca API"""
        try:
            logger.info(
                f"Connecting to Alpaca API ({'paper' if self.paper_trading else 'live'} trading)"
            )

            # Test connection by getting account info
            account_data = await self._get("account")
            if account_data:
                self._connected = True
                logger.info(
                    f"✅ Connected to Alpaca ({'paper' if self.paper_trading else 'live'} trading)"
                )
                logger.info(f"Account ID: {account_data.get('id')}")
                logger.info(f"Account Status: {account_data.get('status')}")
                return True
            else:
                raise BrokerConnectionError("Failed to get account info")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Alpaca: {e}")
            raise BrokerConnectionError(f"Alpaca connection failed: {e}")

    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place a trading order using Alpaca API"""
        # Validate order using common validation
        self.validate_order_request(order_request)

        try:
            # Convert order request to Alpaca format
            alpaca_order = self._convert_order_request(order_request)

            # Place order via REST API
            response_data = await self._post("orders", alpaca_order)

            # Convert response to standard format
            order_response = self._convert_alpaca_order_to_standard(response_data)

            # Invalidate position cache since order was placed
            self._invalidate_position_cache()

            return order_response

        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise BrokerOrderError(f"Order placement failed: {e}")

    def _convert_order_request(self, order_request: OrderRequest) -> Dict[str, Any]:
        """Convert standard order request to Alpaca format"""
        alpaca_order = {
            "symbol": order_request.symbol,
            "qty": str(order_request.quantity),
            "side": order_request.side.value,
            "type": self._convert_order_type(order_request.order_type),
            "time_in_force": order_request.time_in_force.value,
        }

        # Add price fields based on order type
        if order_request.order_type == OrderType.LIMIT:
            alpaca_order["limit_price"] = str(order_request.price)
        elif order_request.order_type == OrderType.STOP:
            alpaca_order["stop_price"] = str(order_request.stop_price)
        elif order_request.order_type == OrderType.STOP_LIMIT:
            alpaca_order["limit_price"] = str(order_request.price)
            alpaca_order["stop_price"] = str(order_request.stop_price)

        # Add optional fields
        if order_request.extended_hours:
            alpaca_order["extended_hours"] = True
        if order_request.client_order_id:
            alpaca_order["client_order_id"] = order_request.client_order_id

        # Add bracket order fields
        if order_request.take_profit:
            alpaca_order["take_profit"] = {
                "limit_price": str(order_request.take_profit)
            }
        if order_request.stop_loss:
            alpaca_order["stop_loss"] = {"stop_price": str(order_request.stop_loss)}

        return alpaca_order

    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert OrderType to Alpaca format"""
        type_mapping = {
            OrderType.MARKET: "market",
            OrderType.LIMIT: "limit",
            OrderType.STOP: "stop",
            OrderType.STOP_LIMIT: "stop_limit",
            OrderType.TRAILING_STOP: "trailing_stop",
        }
        return type_mapping[order_type]

    def _convert_alpaca_order_to_standard(
        self, alpaca_order: Dict[str, Any]
    ) -> OrderResponse:
        """Convert Alpaca order response to standard format"""
        # Field mappings for Alpaca to standard format
        field_mappings = {
            "id": "order_id",
            "qty": "quantity",
            "filled_qty": "filled_qty",
            "filled_avg_price": "avg_fill_price",
        }

        # Use common conversion utility
        return create_dataclass_from_dict(alpaca_order, OrderResponse, field_mappings)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            await self._delete(f"orders/{order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise BrokerOrderError(f"Order cancellation failed: {e}")

    async def get_order_status(self, order_id: str) -> Optional[OrderResponse]:
        """Get the status of an order"""
        try:
            response_data = await self._get(f"orders/{order_id}")
            if not response_data:
                return None
            return self._convert_alpaca_order_to_standard(response_data)
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            raise BrokerDataError(f"Failed to get order status: {e}")

    async def get_orders(
        self, status: Optional[OrderStatus] = None, limit: int = 100
    ) -> List[OrderResponse]:
        """Get orders with optional status filter"""
        try:
            params = {"limit": limit}
            if status:
                params["status"] = self._convert_status_to_alpaca(status)

            response_data = await self._get("orders", params=params)

            orders = []
            for order_data in response_data:
                order = self._convert_alpaca_order_to_standard(order_data)
                orders.append(order)

            return orders
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            raise BrokerDataError(f"Failed to get orders: {e}")

    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        try:
            account_data = await self._get("account")

            # Field mappings for Alpaca to standard format
            field_mappings = {
                "id": "account_id",
                "portfolio_value": "portfolio_value",
                "buying_power": "buying_power",
                "cash": "cash",
                "equity": "equity",
                "daytrading_buying_power": "day_trading_power",
                "pattern_day_trader": "pattern_day_trader",
            }

            return create_dataclass_from_dict(account_data, AccountInfo, field_mappings)

        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise BrokerDataError(f"Failed to get account info: {e}")

    async def get_positions(self) -> List[Position]:
        """Get all current positions"""
        try:
            positions_data = await self._get("positions")

            positions = []
            for position_data in positions_data:
                position = self._convert_alpaca_position_to_standard(position_data)
                positions.append(position)

            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise BrokerDataError(f"Failed to get positions: {e}")

    def _convert_alpaca_position_to_standard(
        self, alpaca_position: Dict[str, Any]
    ) -> Position:
        """Convert Alpaca position to standard format"""
        field_mappings = {
            "qty": "quantity",
            "market_value": "market_value",
            "cost_basis": "cost_basis",
            "unrealized_pl": "unrealized_pl",
            "unrealized_plpc": "unrealized_pl_percent",
            "current_price": "current_price",
            "avg_entry_price": "entry_price",
        }

        return create_dataclass_from_dict(alpaca_position, Position, field_mappings)

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        try:
            position_data = await self._get(f"positions/{symbol}")
            if not position_data:
                return None
            return self._convert_alpaca_position_to_standard(position_data)
        except Exception as e:
            # Position not found is not an error
            if "404" in str(e):
                return None
            logger.error(f"Failed to get position for {symbol}: {e}")
            raise BrokerDataError(f"Failed to get position: {e}")

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote for a symbol"""
        try:
            # Use Alpaca data API endpoint
            quote_data = await self._get(f"stocks/{symbol}/quotes/latest")

            if not quote_data or "quote" not in quote_data:
                return None

            quote = quote_data["quote"]
            return Quote(
                symbol=symbol,
                bid_price=float(quote["bp"]),
                ask_price=float(quote["ap"]),
                bid_size=int(quote["bs"]),
                ask_size=int(quote["as"]),
                timestamp=datetime.fromisoformat(quote["t"].replace("Z", "+00:00")),
                broker_specific_data=quote,
            )
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            raise BrokerDataError(f"Failed to get quote: {e}")

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1D",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[BarData]:
        """Get historical bar data for a symbol"""
        try:
            # Set default dates if not provided
            if end is None:
                end = datetime.now()
            if start is None:
                start = end - timedelta(days=limit)

            params = {
                "symbols": symbol,
                "timeframe": timeframe,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "limit": limit,
            }

            bars_data = await self._get("stocks/bars", params=params)

            bars = []
            if "bars" in bars_data and symbol in bars_data["bars"]:
                for bar_data in bars_data["bars"][symbol]:
                    bar = BarData(
                        symbol=symbol,
                        timestamp=datetime.fromisoformat(
                            bar_data["t"].replace("Z", "+00:00")
                        ),
                        open=float(bar_data["o"]),
                        high=float(bar_data["h"]),
                        low=float(bar_data["l"]),
                        close=float(bar_data["c"]),
                        volume=int(bar_data["v"]),
                        vwap=float(bar_data.get("vw", 0)),
                        trade_count=int(bar_data.get("n", 0)),
                    )
                    bars.append(bar)

            return bars
        except Exception as e:
            logger.error(f"Failed to get bars for {symbol}: {e}")
            raise BrokerDataError(f"Failed to get bars: {e}")

    async def is_market_open(self) -> bool:
        """Check if market is currently open"""
        try:
            clock_data = await self._get("clock")
            return clock_data.get("is_open", False)
        except Exception as e:
            logger.error(f"Failed to check market status: {e}")
            return False

    def _convert_status_to_alpaca(self, status: OrderStatus) -> str:
        """Convert standard OrderStatus to Alpaca format"""
        status_mapping = {
            OrderStatus.NEW: "new",
            OrderStatus.PARTIALLY_FILLED: "partially_filled",
            OrderStatus.FILLED: "filled",
            OrderStatus.DONE_FOR_DAY: "done_for_day",
            OrderStatus.CANCELED: "canceled",
            OrderStatus.EXPIRED: "expired",
            OrderStatus.REPLACED: "replaced",
            OrderStatus.PENDING_CANCEL: "pending_cancel",
            OrderStatus.PENDING_REPLACE: "pending_replace",
            OrderStatus.PENDING_REVIEW: "pending_review",
            OrderStatus.REJECTED: "rejected",
            OrderStatus.SUSPENDED: "suspended",
            OrderStatus.PENDING_NEW: "pending_new",
        }
        return status_mapping.get(status, "new")
