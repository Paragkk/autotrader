"""
Alpaca Broker Adapter - Clean Implementation
Uses common infrastructure and focuses only on Alpaca-specific logic
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from ...infra.model_utils import (
    create_dataclass_from_dict,
    get_field_mappings,
    get_order_type_mappings,
    get_reverse_status_mappings,
)
from ..base import (
    AccountInfo,
    BarData,
    BrokerConnectionError,
    BrokerDataError,
    BrokerOrderError,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    OrderType,
    Position,
    Quote,
)
from ..common import (
    BrokerConfigurationMixin,
    OrderValidationMixin,
    PositionTrackingMixin,
    RESTBrokerAdapter,
)

logger = logging.getLogger(__name__)


class AlpacaBrokerAdapter(
    RESTBrokerAdapter,
    OrderValidationMixin,
    PositionTrackingMixin,
    BrokerConfigurationMixin,
):
    """Clean Alpaca broker adapter using common infrastructure"""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize Alpaca broker adapter"""
        super().__init__(config)

        # Extract Alpaca-specific configuration using common utilities
        self.api_key, self.api_secret = self.extract_broker_credentials(config, "alpaca")
        self.paper_trading = config.get("paper_trading", config.get("use_paper_trading", True))

        # Validate credentials using common validation
        self.validate_api_credentials(self.api_key, self.api_secret, "alpaca")

    @property
    def broker_name(self) -> str:
        return "alpaca"

    @property
    def base_url(self) -> str:
        if self.paper_trading:
            return "https://paper-api.alpaca.markets/v2"
        return "https://api.alpaca.markets/v2"

    @property
    def auth_headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Content-Type": "application/json",
        }

    def _validate_credentials(self) -> None:
        """Validate API credentials"""
        if not self.api_key or self.api_key == "your_alpaca_api_key_here":
            msg = (
                "Missing or invalid ALPACA_API_KEY. Please:\n"
                "1. Sign up for Alpaca paper trading at https://app.alpaca.markets\n"
                "2. Get your API key from the dashboard\n"
                "3. Set ALPACA_API_KEY in your .env file"
            )
            raise ValueError(msg)
        if not self.api_secret or self.api_secret == "your_alpaca_secret_key_here":
            msg = (
                "Missing or invalid ALPACA_SECRET_KEY. Please:\n"
                "1. Sign up for Alpaca paper trading at https://app.alpaca.markets\n"
                "2. Get your secret key from the dashboard\n"
                "3. Set ALPACA_SECRET_KEY in your .env file"
            )
            raise ValueError(msg)

    async def connect(self) -> bool:
        """Connect to Alpaca API"""
        try:
            logger.info(f"Connecting to Alpaca API ({'paper' if self.paper_trading else 'live'} trading)")

            # Test connection by getting account info without connection check (since we're connecting)
            account_data = await self._get_without_connection_check("account")
            if account_data:
                self._connected = True
                logger.info(f"✅ Connected to Alpaca ({'paper' if self.paper_trading else 'live'} trading)")
                logger.info(f"Account ID: {account_data.get('id')}")
                logger.info(f"Account Status: {account_data.get('status')}")
                return True
            msg = "Failed to get account info"
            raise BrokerConnectionError(msg)

        except Exception as e:
            logger.exception(f"❌ Failed to connect to Alpaca: {e}")
            msg = f"Alpaca connection failed: {e}"
            raise BrokerConnectionError(msg)

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
            logger.exception(f"Failed to place order: {e}")
            msg = f"Order placement failed: {e}"
            raise BrokerOrderError(msg)

    def _convert_order_request(self, order_request: OrderRequest) -> dict[str, Any]:
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
            alpaca_order["take_profit"] = {"limit_price": str(order_request.take_profit)}
        if order_request.stop_loss:
            alpaca_order["stop_loss"] = {"stop_price": str(order_request.stop_loss)}

        return alpaca_order

    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert OrderType to Alpaca format"""
        type_mapping = get_order_type_mappings("alpaca")
        return type_mapping[order_type.value]

    def _convert_alpaca_order_to_standard(self, alpaca_order: dict[str, Any]) -> OrderResponse:
        """Convert Alpaca order response to standard format"""
        # Get field mappings for Alpaca
        field_mappings = get_field_mappings("alpaca")

        # Use common conversion utility
        return create_dataclass_from_dict(alpaca_order, OrderResponse, field_mappings)

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            await self._delete(f"orders/{order_id}")
            return True
        except Exception as e:
            logger.exception(f"Failed to cancel order {order_id}: {e}")
            msg = f"Order cancellation failed: {e}"
            raise BrokerOrderError(msg)

    async def get_order_status(self, order_id: str) -> OrderResponse | None:
        """Get the status of an order"""
        try:
            response_data = await self._get(f"orders/{order_id}")
            if not response_data:
                return None
            return self._convert_alpaca_order_to_standard(response_data)
        except Exception as e:
            logger.exception(f"Failed to get order status for {order_id}: {e}")
            msg = f"Failed to get order status: {e}"
            raise BrokerDataError(msg)

    async def get_orders(self, status: OrderStatus | None = None, limit: int = 100) -> list[OrderResponse]:
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
            logger.exception(f"Failed to get orders: {e}")
            msg = f"Failed to get orders: {e}"
            raise BrokerDataError(msg)

    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        try:
            account_data = await self._get("account")

            # Use field mappings for Alpaca to standard format
            field_mappings = get_field_mappings("alpaca")

            return create_dataclass_from_dict(account_data, AccountInfo, field_mappings)

        except Exception as e:
            logger.exception(f"Failed to get account info: {e}")
            msg = f"Failed to get account info: {e}"
            raise BrokerDataError(msg)

    async def get_positions(self) -> list[Position]:
        """Get all current positions"""
        try:
            positions_data = await self._get("positions")

            positions = []
            for position_data in positions_data:
                position = self._convert_alpaca_position_to_standard(position_data)
                positions.append(position)

            return positions
        except Exception as e:
            logger.exception(f"Failed to get positions: {e}")
            msg = f"Failed to get positions: {e}"
            raise BrokerDataError(msg)

    def _convert_alpaca_position_to_standard(self, alpaca_position: dict[str, Any]) -> Position:
        """Convert Alpaca position to standard format"""
        field_mappings = get_field_mappings("alpaca")

        return create_dataclass_from_dict(alpaca_position, Position, field_mappings)

    async def get_position(self, symbol: str) -> Position | None:
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
            logger.exception(f"Failed to get position for {symbol}: {e}")
            msg = f"Failed to get position: {e}"
            raise BrokerDataError(msg)

    async def get_quote(self, symbol: str) -> Quote | None:
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
            logger.exception(f"Failed to get quote for {symbol}: {e}")
            msg = f"Failed to get quote: {e}"
            raise BrokerDataError(msg)

    async def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Get real-time quotes for multiple symbols"""
        try:
            quotes_dict = {}

            # Alpaca supports batch quotes, but we'll implement it symbol by symbol for reliability
            # In production, you might want to optimize this with batch requests
            for symbol in symbols:
                try:
                    quote = await self.get_quote(symbol)
                    if quote:
                        quotes_dict[symbol] = quote
                except Exception as e:
                    logger.warning(f"Failed to get quote for {symbol}: {e}")
                    continue

            return quotes_dict
        except Exception as e:
            logger.exception(f"Failed to get quotes for symbols {symbols}: {e}")
            msg = f"Failed to get quotes: {e}"
            raise BrokerDataError(msg)

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1D",
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[BarData]:
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
                        timestamp=datetime.fromisoformat(bar_data["t"].replace("Z", "+00:00")),
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
            logger.exception(f"Failed to get bars for {symbol}: {e}")
            msg = f"Failed to get bars: {e}"
            raise BrokerDataError(msg)

    async def is_market_open(self) -> bool:
        """Check if market is currently open"""
        try:
            clock_data = await self._get("clock")
            return clock_data.get("is_open", False)
        except Exception as e:
            logger.exception(f"Failed to check market status: {e}")
            return False

    async def get_market_hours(self, date: datetime | None = None) -> dict[str, Any]:
        """Get market hours for a specific date"""
        try:
            # Use current date if none provided
            if date is None:
                date = datetime.now()

            # Format date for API request
            date_str = date.strftime("%Y-%m-%d")

            # Get calendar data for the specified date
            # Alpaca calendar endpoint requires a date range, so we query a single day
            params = {"start": date_str, "end": date_str}

            calendar_data = await self._get("calendar", params=params)

            if not calendar_data or len(calendar_data) == 0:
                # Market is closed on this date
                return {
                    "date": date_str,
                    "is_open": False,
                    "market_open": None,
                    "market_close": None,
                    "timezone": "America/New_York",
                    "reason": "Market closed",
                }

            # Extract market hours from calendar data
            trading_day = calendar_data[0]

            return {
                "date": date_str,
                "is_open": True,
                "market_open": trading_day.get("open"),
                "market_close": trading_day.get("close"),
                "settlement_date": trading_day.get("settlement_date"),
                "timezone": "America/New_York",
                "broker_specific_data": trading_day,
            }

        except Exception as e:
            logger.exception(f"Failed to get market hours for {date_str if date else 'today'}: {e}")
            # Return fallback market hours for US markets
            return {
                "date": date.strftime("%Y-%m-%d") if date else datetime.now().strftime("%Y-%m-%d"),
                "is_open": True,  # Assume open during regular hours
                "market_open": "09:30:00",
                "market_close": "16:00:00",
                "timezone": "America/New_York",
                "error": str(e),
            }

    def _convert_status_to_alpaca(self, status: OrderStatus) -> str:
        """Convert standard OrderStatus to Alpaca format"""
        reverse_mapping = get_reverse_status_mappings("alpaca")
        return reverse_mapping.get(status.value.lower(), "new")
