from dataclasses import dataclass
from datetime import datetime

from ..core.broker_adapter import BrokerAdapter


@dataclass
class Trade:
    """
    Represents a trade in the system including entry/exit orders and risk management parameters.
    """

    trade_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_type: str  # 'market', 'limit', 'stop', 'stop_limit'
    quantity: float
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    order_status: str = "NOT_PLACED"
    entry_time: datetime | None = None
    exit_time: datetime | None = None

    def __post_init__(self):
        self.order = {}
        self.exit_order = {}
        self._is_closed = False
        self._broker: BrokerAdapter | None = None

    def set_broker(self, broker: BrokerAdapter) -> None:
        """Set the broker adapter for executing trades."""
        self._broker = broker

    def place_entry_order(self) -> dict:
        """Place the entry order through the broker."""
        if not self._broker:
            msg = "Broker not set. Call set_broker() first."
            raise ValueError(msg)

        self.order = self._broker.place_order(
            symbol=self.symbol,
            side=self.side,
            order_type=self.entry_type,
            quantity=self.quantity,
            price=self.entry_price,
        )

        if self.stop_loss or self.take_profit:
            self._place_risk_orders()

        return self.order

    def _place_risk_orders(self) -> None:
        """Place stop loss and take profit orders."""
        if not self._broker:
            return

        # Place stop loss
        if self.stop_loss:
            self._broker.place_order(
                symbol=self.symbol,
                side="sell" if self.side == "buy" else "buy",
                order_type="stop",
                quantity=self.quantity,
                price=self.stop_loss,
            )

        # Place take profit
        if self.take_profit:
            self._broker.place_order(
                symbol=self.symbol,
                side="sell" if self.side == "buy" else "buy",
                order_type="limit",
                quantity=self.quantity,
                price=self.take_profit,
            )

    def close_trade(self, exit_price: float | None = None) -> dict:
        """Close the trade at market or specified price."""
        if not self._broker or self._is_closed:
            return {}

        self.exit_order = self._broker.place_order(
            symbol=self.symbol,
            side="sell" if self.side == "buy" else "buy",
            order_type="market" if not exit_price else "limit",
            quantity=self.quantity,
            price=exit_price,
        )

        self._is_closed = True
        self.exit_time = datetime.now()
        return self.exit_order

    def get_status(self) -> dict:
        """Get the current status of the trade."""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "status": self.order_status,
            "entry_time": self.entry_time,
            "exit_time": self.exit_time,
            "is_closed": self._is_closed,
        }
