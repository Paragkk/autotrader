"""
Database models for the automated trading system using SQLModel
"""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy.sql import func
from sqlmodel import JSON, Column, DateTime, Field, Relationship, SQLModel


class ScreenedStockBase(SQLModel):
    """Base model for screened stocks"""

    symbol: str = Field(index=True, max_length=10)
    screening_criteria: dict[str, Any] = Field(sa_column=Column(JSON))
    price: float
    volume: int
    daily_change: float
    market_cap: float | None = None
    sector: str | None = Field(default=None, max_length=50)


class ScreenedStock(ScreenedStockBase, table=True):
    """Table for storing screened stocks"""

    __tablename__ = "screened_stocks"

    id: int | None = Field(default=None, primary_key=True)
    screened_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), nullable=False))

    # Relationships
    scores: list["StockScore"] = Relationship(back_populates="screened_stock")


class StockScoreBase(SQLModel):
    """Base model for stock scores"""

    symbol: str = Field(index=True, max_length=10)
    score: float
    rank: int
    factors_used: dict[str, Any] = Field(sa_column=Column(JSON))
    momentum_score: float | None = None
    volume_score: float | None = None
    volatility_score: float | None = None
    technical_score: float | None = None
    sentiment_score: float | None = None
    fundamentals_score: float | None = None


class StockScore(StockScoreBase, table=True):
    """Table for storing stock scores and rankings"""

    __tablename__ = "stock_scores"

    id: int | None = Field(default=None, primary_key=True)
    screened_stock_id: int | None = Field(default=None, foreign_key="screened_stocks.id")
    scored_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), nullable=False))

    # Relationships
    screened_stock: ScreenedStock | None = Relationship(back_populates="scores")
    tracked_symbol: Optional["TrackedSymbol"] = Relationship(back_populates="stock_score")


class TrackedSymbolBase(SQLModel):
    """Base model for tracked symbols"""

    symbol: str = Field(index=True, max_length=10, unique=True)
    is_active: bool = Field(default=True)
    reason_added: str | None = Field(default=None, max_length=100)


class TrackedSymbol(TrackedSymbolBase, table=True):
    """Table for dynamically tracked symbols"""

    __tablename__ = "tracked_symbols"

    id: int | None = Field(default=None, primary_key=True)
    stock_score_id: int | None = Field(default=None, foreign_key="stock_scores.id")
    added_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), nullable=False))
    last_updated: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now()))

    # Relationships
    stock_score: StockScore | None = Relationship(back_populates="tracked_symbol")
    strategy_results: list["StrategyResult"] = Relationship(back_populates="tracked_symbol")


class StrategyResultBase(SQLModel):
    """Base model for strategy results"""

    symbol: str = Field(index=True, max_length=10)
    strategy_name: str = Field(max_length=50)
    signal: str = Field(max_length=10)  # 'buy', 'sell', 'hold'
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    price_at_analysis: float
    strategy_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))


class StrategyResult(StrategyResultBase, table=True):
    """Table for storing strategy analysis results"""

    __tablename__ = "strategy_results"

    id: int | None = Field(default=None, primary_key=True)
    tracked_symbol_id: int | None = Field(default=None, foreign_key="tracked_symbols.id")
    analyzed_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), nullable=False))

    # Relationships
    tracked_symbol: TrackedSymbol | None = Relationship(back_populates="strategy_results")


class SignalBase(SQLModel):
    """Base model for trading signals"""

    symbol: str = Field(index=True, max_length=10)
    direction: str = Field(max_length=10)  # 'buy', 'sell'
    confidence_score: float
    strength: float
    price_at_signal: float
    strategy_count: int
    contributing_strategies: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    status: str = Field(default="pending", max_length=20)  # 'pending', 'executed', 'rejected', 'expired'


class Signal(SignalBase, table=True):
    """Table for storing aggregated trading signals"""

    __tablename__ = "signals"

    id: int | None = Field(default=None, primary_key=True)
    generated_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), nullable=False))

    # Relationships
    order: Optional["Order"] = Relationship(back_populates="signal")
    risk_filter: Optional["RiskFilterResult"] = Relationship(back_populates="signal")


class RiskFilterResultBase(SQLModel):
    """Base model for risk filter results"""

    result: str = Field(max_length=10)  # 'approved', 'rejected'
    reason: str | None = Field(default=None, max_length=200)
    risk_score: float
    position_size: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None


class RiskFilterResult(RiskFilterResultBase, table=True):
    """Table for storing risk management filter results"""

    __tablename__ = "risk_filter_results"

    id: int | None = Field(default=None, primary_key=True)
    signal_id: int | None = Field(default=None, foreign_key="signals.id")
    filtered_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), nullable=False))

    # Relationships
    signal: Signal | None = Relationship(back_populates="risk_filter")


class OrderBase(SQLModel):
    """Base model for orders"""

    broker_name: str = Field(max_length=20, index=True)  # 'alpaca', 'interactive_brokers', etc.
    broker_order_id: str | None = Field(default=None, max_length=50, index=True)
    symbol: str = Field(index=True, max_length=10)
    side: str = Field(max_length=10)  # 'buy', 'sell'
    quantity: float
    order_type: str = Field(max_length=20)  # 'market', 'limit', 'stop'
    price: float | None = None
    stop_price: float | None = None
    time_in_force: str = Field(default="day", max_length=10)
    status: str = Field(max_length=20)  # 'pending', 'filled', 'cancelled', 'rejected'
    filled_quantity: float = Field(default=0.0)
    filled_price: float | None = None
    commission: float | None = None


class Order(OrderBase, table=True):
    """Table for storing order information"""

    __tablename__ = "orders"

    id: int | None = Field(default=None, primary_key=True)
    signal_id: int | None = Field(default=None, foreign_key="signals.id")
    created_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), nullable=False))
    submitted_at: datetime | None = None
    filled_at: datetime | None = None
    cancelled_at: datetime | None = None

    # Relationships
    signal: Signal | None = Relationship(back_populates="order")
    position: Optional["Position"] = Relationship(back_populates="entry_order")


class PositionBase(SQLModel):
    """Base model for positions"""

    broker_name: str = Field(max_length=20, index=True)  # 'alpaca', 'interactive_brokers', etc.
    symbol: str = Field(index=True, max_length=10)
    quantity: float
    side: str = Field(max_length=10)  # 'long', 'short'
    avg_entry_price: float
    avg_exit_price: float | None = None
    status: str = Field(max_length=20)  # 'open', 'closed', 'partial'
    unrealized_pnl: float = Field(default=0.0)
    realized_pnl: float | None = None
    stop_loss_price: float | None = None
    take_profit_price: float | None = None


class Position(PositionBase, table=True):
    """Table for storing position information"""

    __tablename__ = "positions"

    id: int | None = Field(default=None, primary_key=True)
    entry_order_id: int | None = Field(default=None, foreign_key="orders.id")
    exit_order_id: int | None = Field(default=None, foreign_key="orders.id")
    opened_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), nullable=False))
    closed_at: datetime | None = None

    # Relationships
    entry_order: Order | None = Relationship(
        back_populates="position",
        sa_relationship_kwargs={"foreign_keys": "[Position.entry_order_id]"},
    )
    exit_order: Order | None = Relationship(sa_relationship_kwargs={"foreign_keys": "[Position.exit_order_id]"})
    trade_log: Optional["TradeLog"] = Relationship(back_populates="position")


class TradeLogBase(SQLModel):
    """Base model for trade logs"""

    broker_name: str = Field(max_length=20, index=True)  # 'alpaca', 'interactive_brokers', etc.
    symbol: str = Field(index=True, max_length=10)
    signal_generated_at: datetime
    order_placed_at: datetime
    position_opened_at: datetime
    position_closed_at: datetime | None = None
    entry_price: float
    exit_price: float | None = None
    quantity: float
    holding_period: int | None = None  # in minutes
    gross_pnl: float | None = None
    net_pnl: float | None = None
    return_percent: float | None = None
    commission_paid: float | None = None
    strategy_name: str | None = Field(default=None, max_length=50)
    signal_strength: float | None = None
    market_conditions: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))


class TradeLog(TradeLogBase, table=True):
    """Table for complete trade audit logging"""

    __tablename__ = "trade_logs"

    id: int | None = Field(default=None, primary_key=True)
    position_id: int | None = Field(default=None, foreign_key="positions.id")

    # Relationships
    position: Position | None = Relationship(back_populates="trade_log")


class SystemMetricsBase(SQLModel):
    """Base model for system metrics"""

    total_equity: float | None = None
    available_cash: float | None = None
    total_positions: int | None = None
    daily_pnl: float | None = None
    signals_generated: int | None = None
    orders_placed: int | None = None
    orders_filled: int | None = None
    win_rate: float | None = None
    screening_runtime: float | None = None  # seconds
    strategy_runtime: float | None = None  # seconds
    order_execution_time: float | None = None  # seconds
    market_hours: bool | None = None
    market_volatility: float | None = None


class SystemMetrics(SystemMetricsBase, table=True):
    """Table for storing system performance metrics"""

    __tablename__ = "system_metrics"

    id: int | None = Field(default=None, primary_key=True)
    recorded_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), nullable=False))


class ConfigurationHistoryBase(SQLModel):
    """Base model for configuration history"""

    changed_by: str = Field(default="system", max_length=50)
    config_section: str = Field(max_length=50)
    old_value: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    new_value: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    reason: str | None = Field(default=None, max_length=200)


class ConfigurationHistory(ConfigurationHistoryBase, table=True):
    """Table for tracking configuration changes"""

    __tablename__ = "configuration_history"

    id: int | None = Field(default=None, primary_key=True)
    changed_at: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), nullable=False))


class BrokerAccountBase(SQLModel):
    """Base model for broker account information"""

    broker_name: str = Field(max_length=20, index=True, unique=True)
    account_id: str = Field(max_length=50, index=True)
    buying_power: float = Field(default=0.0)
    cash: float = Field(default=0.0)
    portfolio_value: float = Field(default=0.0)
    equity: float = Field(default=0.0)
    day_trading_power: float | None = None
    pattern_day_trader: bool = Field(default=False)
    account_status: str = Field(default="active", max_length=20)
    paper_trading: bool = Field(default=True)


class BrokerAccount(BrokerAccountBase, table=True):
    """Table for storing broker account information"""

    __tablename__ = "broker_accounts"

    id: int | None = Field(default=None, primary_key=True)
    last_updated: datetime = Field(sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now()))


# Create and update models for API use
class ScreenedStockCreate(ScreenedStockBase):
    pass


class ScreenedStockUpdate(SQLModel):
    symbol: str | None = None
    screening_criteria: dict[str, Any] | None = None
    price: float | None = None
    volume: int | None = None
    daily_change: float | None = None
    market_cap: float | None = None
    sector: str | None = None


class StockScoreCreate(StockScoreBase):
    pass


class StockScoreUpdate(SQLModel):
    score: float | None = None
    rank: int | None = None
    factors_used: dict[str, Any] | None = None
    momentum_score: float | None = None
    volume_score: float | None = None
    volatility_score: float | None = None
    technical_score: float | None = None
    sentiment_score: float | None = None
    fundamentals_score: float | None = None


# Add other Create/Update models as needed for all tables
