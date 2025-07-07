import pytest
import pandas as pd
from datetime import datetime
from src.core.trading.trade import Trade
from src.core.trading.portfolio import Portfolio
from src.core.trading.indicators import TechnicalIndicators
from src.core.trading.engine import TradingEngine
from src.core.trading.executor import TradeExecutor


# Mock Position class for testing
class Position:
    def __init__(self, symbol, quantity, entry_price, entry_date):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_date = entry_date


class MockBrokerAdapter:
    def __init__(self):
        self.orders = {}
        self.order_id = 0

    def place_order(
        self, symbol, side, order_type, quantity, price=None, stop_price=None
    ):
        self.order_id += 1
        order = {
            "order_id": str(self.order_id),
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "price": price,
            "stop_price": stop_price,
            "status": "filled",
        }
        self.orders[str(self.order_id)] = order
        return order

    def cancel_order(self, order_id):
        if order_id in self.orders:
            self.orders[order_id]["status"] = "cancelled"
            return {"status": "success"}
        return {"status": "error"}

    def get_order_status(self, order_id):
        return self.orders.get(order_id, {"status": "not_found"})


def test_trade_creation():
    trade = Trade(
        trade_id="test_1",
        symbol="AAPL",
        side="buy",
        entry_type="market",
        quantity=100,
        entry_price=150.0,
    )
    assert trade.trade_id == "test_1"
    assert trade.symbol == "AAPL"
    assert trade.side == "buy"
    assert trade.quantity == 100


def test_portfolio_management():
    broker = MockBrokerAdapter()
    portfolio = Portfolio(broker)

    # Test initial state
    assert len(portfolio.positions) == 0

    # Test adding position
    portfolio.add_position(
        Position(
            symbol="AAPL", quantity=100, entry_price=150.0, entry_date=datetime.now()
        )
    )
    assert len(portfolio.positions) == 1
    assert "AAPL" in portfolio.positions

    # Test position value calculation
    current_prices = {"AAPL": 160.0}
    metrics = portfolio.get_portfolio_metrics(current_prices)
    assert metrics["positions"]["AAPL"]["profit_loss"] > 0


def test_technical_indicators():
    # Create sample data
    data = pd.DataFrame(
        {
            "open": [100] * 100,
            "high": [105] * 100,
            "low": [95] * 100,
            "close": [101] * 100,
            "volume": [1000] * 100,
        }
    )

    indicators = TechnicalIndicators(data)

    # Test SMA
    sma_name = indicators.add_sma(period=20)
    sma_values = indicators.get_indicator_value(sma_name)
    assert len(sma_values) == len(data)

    # Test RSI
    rsi_name = indicators.add_rsi(period=14)
    rsi_values = indicators.get_indicator_value(rsi_name)
    assert len(rsi_values) == len(data)


def test_trading_engine():
    broker = MockBrokerAdapter()
    portfolio = Portfolio(broker)
    engine = TradingEngine(broker, portfolio)

    # Test strategy setup
    strategy_config = {
        "indicators": [{"type": "sma", "period": 20}, {"type": "rsi", "period": 14}],
        "signals": [
            {
                "indicator": "rsi_14",
                "buy_condition": lambda x, y: x < y,
                "sell_condition": lambda x, y: x > y,
                "buy_threshold": 30,
                "sell_threshold": 70,
            }
        ],
    }

    # Create sample market data
    market_data = pd.DataFrame(
        {
            "open": [100] * 100,
            "high": [105] * 100,
            "low": [95] * 100,
            "close": [101] * 100,
            "volume": [1000] * 100,
        }
    )

    engine.update_market_data(market_data)
    engine.setup_strategy(strategy_config)
    engine.check_and_execute_signals()

    # Verify engine state
    metrics = engine.get_trading_metrics()
    assert "portfolio_metrics" in metrics
    assert "active_trades" in metrics


def test_trade_executor():
    broker = MockBrokerAdapter()
    executor = TradeExecutor(broker)

    # Test order placement
    order_params = {
        "symbol": "AAPL",
        "side": "buy",
        "order_type": "market",
        "quantity": 100,
        "price": 150.0,
    }

    result = executor.place_order(order_params)
    assert result["status"] == "placed"

    # Test order cancellation
    cancel_result = executor.cancel_order(result["order_id"])
    assert cancel_result["status"] == "success"

    # Test order history
    orders = executor.get_all_orders()
    assert len(orders) == 1


if __name__ == "__main__":
    pytest.main([__file__])
