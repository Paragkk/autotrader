from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from ..core.broker_adapter import BrokerAdapter


@dataclass
class Position:
    """Represents a position in the portfolio."""

    symbol: str
    quantity: float
    entry_price: float
    entry_date: datetime

    def current_value(self, current_price: float) -> float:
        """Calculate current position value."""
        return self.quantity * current_price

    def profit_loss(self, current_price: float) -> float:
        """Calculate unrealized profit/loss."""
        return self.quantity * (current_price - self.entry_price)

    def profit_loss_percent(self, current_price: float) -> float:
        """Calculate percentage profit/loss."""
        if self.entry_price == 0:
            return 0
        return ((current_price - self.entry_price) / self.entry_price) * 100


class Portfolio:
    """
    Manages a collection of trading positions and calculates portfolio metrics.
    """

    def __init__(self, broker: BrokerAdapter):
        self.positions: Dict[str, Position] = {}
        self._broker = broker
        self.cash_balance = 0.0
        self.initial_capital = 0.0

    def add_position(self, position: Position):
        """Add a new position to the portfolio."""
        self.positions[position.symbol] = position

    def remove_position(self, symbol: str):
        """Remove a position from the portfolio."""
        if symbol in self.positions:
            del self.positions[symbol]

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position details for a symbol."""
        return self.positions.get(symbol)

    def update_position(self, symbol: str, quantity_change: float, price: float):
        """Update an existing position or create a new one."""
        if symbol in self.positions:
            position = self.positions[symbol]
            new_quantity = position.quantity + quantity_change

            if new_quantity == 0:
                del self.positions[symbol]
            else:
                # Calculate new average entry price
                total_value = (position.quantity * position.entry_price) + (
                    quantity_change * price
                )
                new_entry_price = total_value / new_quantity

                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=new_quantity,
                    entry_price=new_entry_price,
                    entry_date=position.entry_date
                    if new_quantity > 0
                    else datetime.now(),
                )
        else:
            # Create new position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity_change,
                entry_price=price,
                entry_date=datetime.now(),
            )

    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value including cash."""
        total_value = self.cash_balance

        for symbol, position in self.positions.items():
            if symbol in current_prices:
                total_value += position.current_value(current_prices[symbol])

        return total_value

    def get_portfolio_metrics(self, current_prices: Dict[str, float]) -> Dict:
        """Calculate portfolio performance metrics."""
        total_equity = self.get_portfolio_value(current_prices)
        total_pl = total_equity - self.initial_capital

        return {
            "total_equity": total_equity,
            "cash_balance": self.cash_balance,
            "total_positions": len(self.positions),
            "total_profit_loss": total_pl,
            "total_profit_loss_percent": (total_pl / self.initial_capital * 100)
            if self.initial_capital > 0
            else 0,
            "positions": {
                symbol: {
                    "quantity": pos.quantity,
                    "entry_price": pos.entry_price,
                    "current_price": current_prices.get(symbol, 0),
                    "market_value": pos.current_value(current_prices.get(symbol, 0)),
                    "profit_loss": pos.profit_loss(current_prices.get(symbol, 0)),
                    "profit_loss_percent": pos.profit_loss_percent(
                        current_prices.get(symbol, 0)
                    ),
                }
                for symbol, pos in self.positions.items()
            },
        }
