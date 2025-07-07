"""
Alpaca Broker Adapter Implementation
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from brokers.base import (
    BrokerAdapter,
    OrderRequest,
    OrderResponse,
    Position,
    AccountInfo,
    Quote,
    BarData,
    OrderSide,
    OrderType,
    OrderStatus,
    TimeInForce,
    BrokerConnectionError,
    BrokerOrderError,
    BrokerDataError,
)
from brokers.alpaca.api import PyAlpacaAPI

logger = logging.getLogger(__name__)


class AlpacaBrokerAdapter(BrokerAdapter):
    """Alpaca broker adapter implementation"""

    def __init__(self, api_key: str, api_secret: str, paper_trading: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.paper_trading = paper_trading
        self._client: Optional[PyAlpacaAPI] = None
        self._connected = False

    @property
    def broker_name(self) -> str:
        return "alpaca"

    async def connect(self) -> bool:
        """Connect to Alpaca API"""
        try:
            self._client = PyAlpacaAPI(
                api_key=self.api_key,
                api_secret=self.api_secret,
                api_paper=self.paper_trading,
            )

            # Test connection by getting account info
            account = self._client.trading.account.get()
            if account:
                self._connected = True
                logger.info(
                    f"Connected to Alpaca ({'paper' if self.paper_trading else 'live'} trading)"
                )
                return True
            else:
                raise BrokerConnectionError("Failed to get account info")

        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            raise BrokerConnectionError(f"Alpaca connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Alpaca API"""
        self._client = None
        self._connected = False
        logger.info("Disconnected from Alpaca")

    async def is_connected(self) -> bool:
        """Check if connected to Alpaca"""
        return self._connected and self._client is not None

    def _ensure_connected(self):
        """Ensure we're connected to the broker"""
        if not self._connected or not self._client:
            raise BrokerConnectionError(
                "Not connected to Alpaca. Call connect() first."
            )

    def _convert_order_side(self, side: OrderSide) -> str:
        """Convert our OrderSide to Alpaca format"""
        return side.value

    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert our OrderType to Alpaca format"""
        type_mapping = {
            OrderType.MARKET: "market",
            OrderType.LIMIT: "limit",
            OrderType.STOP: "stop",
            OrderType.STOP_LIMIT: "stop_limit",
            OrderType.TRAILING_STOP: "trailing_stop",
        }
        return type_mapping[order_type]

    def _convert_time_in_force(self, tif: TimeInForce) -> str:
        """Convert our TimeInForce to Alpaca format"""
        return tif.value

    def _convert_from_alpaca_status(self, alpaca_status: str) -> OrderStatus:
        """Convert Alpaca order status to our OrderStatus"""
        status_mapping = {
            "new": OrderStatus.NEW,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "filled": OrderStatus.FILLED,
            "done_for_day": OrderStatus.DONE_FOR_DAY,
            "canceled": OrderStatus.CANCELED,
            "expired": OrderStatus.EXPIRED,
            "replaced": OrderStatus.REPLACED,
            "pending_cancel": OrderStatus.PENDING_CANCEL,
            "pending_replace": OrderStatus.PENDING_REPLACE,
            "pending_review": OrderStatus.PENDING_REVIEW,
            "rejected": OrderStatus.REJECTED,
            "suspended": OrderStatus.SUSPENDED,
            "pending_new": OrderStatus.PENDING_NEW,
        }
        return status_mapping.get(alpaca_status, OrderStatus.NEW)

    async def place_order(self, order_request: OrderRequest) -> OrderResponse:
        """Place a trading order using Alpaca API"""
        self._ensure_connected()

        try:
            # Convert order request to Alpaca format
            side = self._convert_order_side(order_request.side)
            time_in_force = self._convert_time_in_force(order_request.time_in_force)

            # Place order based on type
            if order_request.order_type == OrderType.MARKET:
                response = self._client.trading.orders.market(
                    symbol=order_request.symbol,
                    qty=order_request.quantity,
                    side=side,
                    time_in_force=time_in_force,
                    extended_hours=order_request.extended_hours,
                    take_profit=order_request.take_profit,
                    stop_loss=order_request.stop_loss,
                )
            elif order_request.order_type == OrderType.LIMIT:
                if order_request.price is None:
                    raise BrokerOrderError("Limit price required for limit orders")
                response = self._client.trading.orders.limit(
                    symbol=order_request.symbol,
                    qty=order_request.quantity,
                    limit_price=order_request.price,
                    side=side,
                    time_in_force=time_in_force,
                    extended_hours=order_request.extended_hours,
                    take_profit=order_request.take_profit,
                    stop_loss=order_request.stop_loss,
                )
            elif order_request.order_type == OrderType.STOP:
                if order_request.stop_price is None:
                    raise BrokerOrderError("Stop price required for stop orders")
                response = self._client.trading.orders.stop(
                    symbol=order_request.symbol,
                    qty=order_request.quantity,
                    stop_price=order_request.stop_price,
                    side=side,
                    time_in_force=time_in_force,
                    extended_hours=order_request.extended_hours,
                )
            elif order_request.order_type == OrderType.STOP_LIMIT:
                if order_request.stop_price is None or order_request.price is None:
                    raise BrokerOrderError(
                        "Both stop price and limit price required for stop-limit orders"
                    )
                response = self._client.trading.orders.stop_limit(
                    symbol=order_request.symbol,
                    qty=order_request.quantity,
                    stop_price=order_request.stop_price,
                    limit_price=order_request.price,
                    side=side,
                    time_in_force=time_in_force,
                    extended_hours=order_request.extended_hours,
                )
            else:
                raise BrokerOrderError(
                    f"Unsupported order type: {order_request.order_type}"
                )

            # Convert response to our format
            return OrderResponse(
                order_id=response.id,
                client_order_id=getattr(response, "client_order_id", None),
                symbol=response.symbol,
                quantity=float(response.qty),
                side=OrderSide(response.side),
                order_type=OrderType(response.type),
                status=self._convert_from_alpaca_status(response.status),
                filled_qty=float(response.filled_qty) if response.filled_qty else 0.0,
                avg_fill_price=float(response.filled_avg_price)
                if response.filled_avg_price
                else None,
                timestamp=datetime.now(),
                broker_specific_data=response.__dict__,
            )

        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise BrokerOrderError(f"Order placement failed: {e}")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        self._ensure_connected()

        try:
            result = self._client.trading.orders.cancel_by_id(order_id)
            return "cancelled" in result.lower() or "canceled" in result.lower()
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise BrokerOrderError(f"Order cancellation failed: {e}")

    async def get_order_status(self, order_id: str) -> Optional[OrderResponse]:
        """Get the status of an order"""
        self._ensure_connected()

        try:
            response = self._client.trading.orders.get_by_id(order_id)
            if not response:
                return None

            return OrderResponse(
                order_id=response.id,
                client_order_id=getattr(response, "client_order_id", None),
                symbol=response.symbol,
                quantity=float(response.qty),
                side=OrderSide(response.side),
                order_type=OrderType(response.type),
                status=self._convert_from_alpaca_status(response.status),
                filled_qty=float(response.filled_qty) if response.filled_qty else 0.0,
                avg_fill_price=float(response.filled_avg_price)
                if response.filled_avg_price
                else None,
                timestamp=datetime.now(),
                broker_specific_data=response.__dict__,
            )

        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            raise BrokerDataError(f"Failed to get order status: {e}")

    async def get_orders(
        self, status: Optional[OrderStatus] = None, limit: int = 100
    ) -> List[OrderResponse]:
        """Get orders with optional status filter"""
        self._ensure_connected()

        try:
            # Alpaca doesn't have a direct get_orders method in our current implementation
            # This would need to be implemented in the py_alpaca_api
            # For now, return empty list
            logger.warning("get_orders not fully implemented for Alpaca adapter")
            return []

        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            raise BrokerDataError(f"Failed to get orders: {e}")

    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        self._ensure_connected()

        try:
            account = self._client.trading.account.get()

            return AccountInfo(
                account_id=account.id,
                buying_power=float(account.buying_power),
                cash=float(account.cash),
                portfolio_value=float(account.portfolio_value),
                equity=float(account.equity),
                day_trading_power=float(account.daytrading_buying_power),
                pattern_day_trader=account.pattern_day_trader,
                broker_specific_data=account.__dict__,
            )

        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise BrokerDataError(f"Failed to get account info: {e}")

    async def get_positions(self) -> List[Position]:
        """Get all current positions"""
        self._ensure_connected()

        try:
            positions_df = self._client.trading.positions.get_all()
            positions = []

            for _, row in positions_df.iterrows():
                position = Position(
                    symbol=row["symbol"],
                    quantity=float(row["qty"]),
                    market_value=float(row["market_value"]),
                    cost_basis=float(row["cost_basis"]),
                    unrealized_pl=float(row["profit_dol"]),
                    unrealized_pl_percent=float(row["profit_pct"]),
                    current_price=float(row["current_price"]),
                    entry_price=float(row["avg_entry_price"]),
                    side=row["side"],
                    broker_specific_data=row.to_dict(),
                )
                positions.append(position)

            return positions

        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise BrokerDataError(f"Failed to get positions: {e}")

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        positions = await self.get_positions()
        for position in positions:
            if position.symbol == symbol:
                return position
        return None

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote for a symbol"""
        self._ensure_connected()

        try:
            quote_data = self._client.stock.latest_quote.get_latest_quote(symbol)

            return Quote(
                symbol=symbol,
                bid_price=float(quote_data.bid_price),
                ask_price=float(quote_data.ask_price),
                bid_size=int(quote_data.bid_size),
                ask_size=int(quote_data.ask_size),
                timestamp=datetime.now(),
                broker_specific_data=quote_data.__dict__,
            )

        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            raise BrokerDataError(f"Failed to get quote: {e}")

    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get real-time quotes for multiple symbols"""
        quotes = {}
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                if quote:
                    quotes[symbol] = quote
            except Exception as e:
                logger.warning(f"Failed to get quote for {symbol}: {e}")
        return quotes

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1D",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[BarData]:
        """Get historical bar data for a symbol"""
        self._ensure_connected()

        try:
            # Set default dates if not provided
            if end is None:
                end = datetime.now().date()
            if start is None:
                start = end - timedelta(days=limit)

            # Convert dates to strings
            start_str = (
                start.strftime("%Y-%m-%d")
                if isinstance(start, datetime)
                else str(start)
            )
            end_str = (
                end.strftime("%Y-%m-%d") if isinstance(end, datetime) else str(end)
            )

            # Get data from Alpaca
            data = self._client.stock.history.get_stock_data(
                symbol=symbol, start=start_str, end=end_str, timeframe=timeframe
            )

            bars = []
            for _, row in data.iterrows():
                bar = BarData(
                    symbol=symbol,
                    timestamp=row["date"] if "date" in row else datetime.now(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                    vwap=float(row["vwap"]) if "vwap" in row else None,
                    trade_count=int(row["trade_count"])
                    if "trade_count" in row
                    else None,
                )
                bars.append(bar)

            return bars

        except Exception as e:
            logger.error(f"Failed to get bars for {symbol}: {e}")
            raise BrokerDataError(f"Failed to get bars: {e}")

    async def is_market_open(self) -> bool:
        """Check if market is currently open"""
        self._ensure_connected()

        try:
            clock = self._client.trading.market.clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Failed to check market status: {e}")
            return False

    async def get_market_hours(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get market hours for a specific date"""
        self._ensure_connected()

        try:
            if date is None:
                date = datetime.now()

            start_date = date.strftime("%Y-%m-%d")
            end_date = start_date

            calendar = self._client.trading.market.calendar(start_date, end_date)

            if not calendar.empty:
                day_info = calendar.iloc[0]
                return {
                    "date": start_date,
                    "is_open": True,
                    "open_time": day_info.get("open"),
                    "close_time": day_info.get("close"),
                    "broker_specific_data": day_info.to_dict(),
                }
            else:
                return {
                    "date": start_date,
                    "is_open": False,
                    "open_time": None,
                    "close_time": None,
                }

        except Exception as e:
            logger.error(f"Failed to get market hours: {e}")
            return {"date": date.strftime("%Y-%m-%d") if date else "", "is_open": False}

    async def get_watchlists(self) -> List[Dict[str, Any]]:
        """Get user watchlists"""
        self._ensure_connected()

        try:
            watchlists_data = self._client.trading.watchlists.get_all()
            watchlists = []

            for watchlist in watchlists_data:
                watchlists.append(
                    {
                        "id": watchlist.id,
                        "name": watchlist.name,
                        "symbols": [asset.symbol for asset in watchlist.assets],
                        "created_at": watchlist.created_at,
                        "updated_at": watchlist.updated_at,
                    }
                )

            return watchlists

        except Exception as e:
            logger.error(f"Failed to get watchlists: {e}")
            return []

    async def create_watchlist(self, name: str, symbols: List[str]) -> bool:
        """Create a new watchlist"""
        self._ensure_connected()

        try:
            symbols_str = ", ".join(symbols)
            watchlist = self._client.trading.watchlists.create(
                name=name, symbols=symbols_str
            )
            return watchlist is not None

        except Exception as e:
            logger.error(f"Failed to create watchlist {name}: {e}")
            return False

    async def add_to_watchlist(self, watchlist_id: str, symbol: str) -> bool:
        """Add symbol to watchlist"""
        self._ensure_connected()

        try:
            result = self._client.trading.watchlists.add_asset(
                watchlist_id=watchlist_id, symbol=symbol
            )
            return result is not None

        except Exception as e:
            logger.error(f"Failed to add {symbol} to watchlist {watchlist_id}: {e}")
            return False
