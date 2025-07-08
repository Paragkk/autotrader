"""
Database models for the automated trading system using SQLModel
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column, DateTime, JSON
from sqlalchemy.sql import func


class ScreenedStockBase(SQLModel):
    """Base model for screened stocks"""

    symbol: str = Field(index=True, max_length=10)
    screening_criteria: Dict[str, Any] = Field(sa_column=Column(JSON))
    price: float
    volume: int
    daily_change: float
    market_cap: Optional[float] = None
    sector: Optional[str] = Field(default=None, max_length=50)


class ScreenedStock(ScreenedStockBase, table=True):
    """Table for storing screened stocks"""

    __tablename__ = "screened_stocks"

    id: Optional[int] = Field(default=None, primary_key=True)
    screened_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )

    # Relationships
    scores: List["StockScore"] = Relationship(back_populates="screened_stock")


class StockScoreBase(SQLModel):
    """Base model for stock scores"""

    symbol: str = Field(index=True, max_length=10)
    score: float
    rank: int
    factors_used: Dict[str, Any] = Field(sa_column=Column(JSON))
    momentum_score: Optional[float] = None
    volume_score: Optional[float] = None
    volatility_score: Optional[float] = None
    technical_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    fundamentals_score: Optional[float] = None


class StockScore(StockScoreBase, table=True):
    """Table for storing stock scores and rankings"""

    __tablename__ = "stock_scores"

    id: Optional[int] = Field(default=None, primary_key=True)
    screened_stock_id: Optional[int] = Field(
        default=None, foreign_key="screened_stocks.id"
    )
    scored_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )

    # Relationships
    screened_stock: Optional[ScreenedStock] = Relationship(back_populates="scores")
    tracked_symbol: Optional["TrackedSymbol"] = Relationship(
        back_populates="stock_score"
    )


class TrackedSymbolBase(SQLModel):
    """Base model for tracked symbols"""

    symbol: str = Field(index=True, max_length=10, unique=True)
    is_active: bool = Field(default=True)
    reason_added: Optional[str] = Field(default=None, max_length=100)


class TrackedSymbol(TrackedSymbolBase, table=True):
    """Table for dynamically tracked symbols"""

    __tablename__ = "tracked_symbols"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_score_id: Optional[int] = Field(default=None, foreign_key="stock_scores.id")
    added_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )
    last_updated: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now())
    )

    # Relationships
    stock_score: Optional[StockScore] = Relationship(back_populates="tracked_symbol")
    strategy_results: List["StrategyResult"] = Relationship(
        back_populates="tracked_symbol"
    )


class StrategyResultBase(SQLModel):
    """Base model for strategy results"""

    symbol: str = Field(index=True, max_length=10)
    strategy_name: str = Field(max_length=50)
    signal: str = Field(max_length=10)  # 'buy', 'sell', 'hold'
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    price_at_analysis: float
    strategy_data: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )


class StrategyResult(StrategyResultBase, table=True):
    """Table for storing strategy analysis results"""

    __tablename__ = "strategy_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    tracked_symbol_id: Optional[int] = Field(
        default=None, foreign_key="tracked_symbols.id"
    )
    analyzed_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )

    # Relationships
    tracked_symbol: Optional[TrackedSymbol] = Relationship(
        back_populates="strategy_results"
    )


class SignalBase(SQLModel):
    """Base model for trading signals"""

    symbol: str = Field(index=True, max_length=10)
    direction: str = Field(max_length=10)  # 'buy', 'sell'
    confidence_score: float
    strength: float
    price_at_signal: float
    strategy_count: int
    contributing_strategies: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )
    status: str = Field(
        default="pending", max_length=20
    )  # 'pending', 'executed', 'rejected', 'expired'


class Signal(SignalBase, table=True):
    """Table for storing aggregated trading signals"""

    __tablename__ = "signals"

    id: Optional[int] = Field(default=None, primary_key=True)
    generated_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )

    # Relationships
    order: Optional["Order"] = Relationship(back_populates="signal")
    risk_filter: Optional["RiskFilterResult"] = Relationship(back_populates="signal")


class RiskFilterResultBase(SQLModel):
    """Base model for risk filter results"""

    result: str = Field(max_length=10)  # 'approved', 'rejected'
    reason: Optional[str] = Field(default=None, max_length=200)
    risk_score: float
    position_size: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class RiskFilterResult(RiskFilterResultBase, table=True):
    """Table for storing risk management filter results"""

    __tablename__ = "risk_filter_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    signal_id: Optional[int] = Field(default=None, foreign_key="signals.id")
    filtered_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )

    # Relationships
    signal: Optional[Signal] = Relationship(back_populates="risk_filter")


class OrderBase(SQLModel):
    """Base model for orders"""

    broker_name: str = Field(
        max_length=20, index=True
    )  # 'alpaca', 'interactive_brokers', etc.
    broker_order_id: Optional[str] = Field(default=None, max_length=50, index=True)
    symbol: str = Field(index=True, max_length=10)
    side: str = Field(max_length=10)  # 'buy', 'sell'
    quantity: float
    order_type: str = Field(max_length=20)  # 'market', 'limit', 'stop'
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = Field(default="day", max_length=10)
    status: str = Field(max_length=20)  # 'pending', 'filled', 'cancelled', 'rejected'
    filled_quantity: float = Field(default=0.0)
    filled_price: Optional[float] = None
    commission: Optional[float] = None


class Order(OrderBase, table=True):
    """Table for storing order information"""

    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    signal_id: Optional[int] = Field(default=None, foreign_key="signals.id")
    created_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    # Relationships
    signal: Optional[Signal] = Relationship(back_populates="order")
    position: Optional["Position"] = Relationship(back_populates="entry_order")


class PositionBase(SQLModel):
    """Base model for positions"""

    broker_name: str = Field(
        max_length=20, index=True
    )  # 'alpaca', 'interactive_brokers', etc.
    symbol: str = Field(index=True, max_length=10)
    quantity: float
    side: str = Field(max_length=10)  # 'long', 'short'
    avg_entry_price: float
    avg_exit_price: Optional[float] = None
    status: str = Field(max_length=20)  # 'open', 'closed', 'partial'
    unrealized_pnl: float = Field(default=0.0)
    realized_pnl: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None


class Position(PositionBase, table=True):
    """Table for storing position information"""

    __tablename__ = "positions"

    id: Optional[int] = Field(default=None, primary_key=True)
    entry_order_id: Optional[int] = Field(default=None, foreign_key="orders.id")
    exit_order_id: Optional[int] = Field(default=None, foreign_key="orders.id")
    opened_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )
    closed_at: Optional[datetime] = None

    # Relationships
    entry_order: Optional[Order] = Relationship(
        back_populates="position",
        sa_relationship_kwargs={"foreign_keys": "[Position.entry_order_id]"},
    )
    exit_order: Optional[Order] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Position.exit_order_id]"}
    )
    trade_log: Optional["TradeLog"] = Relationship(back_populates="position")


class TradeLogBase(SQLModel):
    """Base model for trade logs"""

    broker_name: str = Field(
        max_length=20, index=True
    )  # 'alpaca', 'interactive_brokers', etc.
    symbol: str = Field(index=True, max_length=10)
    signal_generated_at: datetime
    order_placed_at: datetime
    position_opened_at: datetime
    position_closed_at: Optional[datetime] = None
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float
    holding_period: Optional[int] = None  # in minutes
    gross_pnl: Optional[float] = None
    net_pnl: Optional[float] = None
    return_percent: Optional[float] = None
    commission_paid: Optional[float] = None
    strategy_name: Optional[str] = Field(default=None, max_length=50)
    signal_strength: Optional[float] = None
    market_conditions: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON)
    )


class TradeLog(TradeLogBase, table=True):
    """Table for complete trade audit logging"""

    __tablename__ = "trade_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    position_id: Optional[int] = Field(default=None, foreign_key="positions.id")

    # Relationships
    position: Optional[Position] = Relationship(back_populates="trade_log")


class SystemMetricsBase(SQLModel):
    """Base model for system metrics"""

    total_equity: Optional[float] = None
    available_cash: Optional[float] = None
    total_positions: Optional[int] = None
    daily_pnl: Optional[float] = None
    signals_generated: Optional[int] = None
    orders_placed: Optional[int] = None
    orders_filled: Optional[int] = None
    win_rate: Optional[float] = None
    screening_runtime: Optional[float] = None  # seconds
    strategy_runtime: Optional[float] = None  # seconds
    order_execution_time: Optional[float] = None  # seconds
    market_hours: Optional[bool] = None
    market_volatility: Optional[float] = None


class SystemMetrics(SystemMetricsBase, table=True):
    """Table for storing system performance metrics"""

    __tablename__ = "system_metrics"

    id: Optional[int] = Field(default=None, primary_key=True)
    recorded_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )


class ConfigurationHistoryBase(SQLModel):
    """Base model for configuration history"""

    changed_by: str = Field(default="system", max_length=50)
    config_section: str = Field(max_length=50)
    old_value: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    new_value: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    reason: Optional[str] = Field(default=None, max_length=200)


class ConfigurationHistory(ConfigurationHistoryBase, table=True):
    """Table for tracking configuration changes"""

    __tablename__ = "configuration_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    changed_at: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), nullable=False)
    )


class BrokerAccountBase(SQLModel):
    """Base model for broker account information"""

    broker_name: str = Field(max_length=20, index=True, unique=True)
    account_id: str = Field(max_length=50, index=True)
    buying_power: float = Field(default=0.0)
    cash: float = Field(default=0.0)
    portfolio_value: float = Field(default=0.0)
    equity: float = Field(default=0.0)
    day_trading_power: Optional[float] = None
    pattern_day_trader: bool = Field(default=False)
    account_status: str = Field(default="active", max_length=20)
    paper_trading: bool = Field(default=True)


class BrokerAccount(BrokerAccountBase, table=True):
    """Table for storing broker account information"""

    __tablename__ = "broker_accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    last_updated: datetime = Field(
        sa_column=Column(DateTime, server_default=func.now(), onupdate=func.now())
    )


# Create and update models for API use
class ScreenedStockCreate(ScreenedStockBase):
    pass


class ScreenedStockUpdate(SQLModel):
    symbol: Optional[str] = None
    screening_criteria: Optional[Dict[str, Any]] = None
    price: Optional[float] = None
    volume: Optional[int] = None
    daily_change: Optional[float] = None
    market_cap: Optional[float] = None
    sector: Optional[str] = None


class StockScoreCreate(StockScoreBase):
    pass


class StockScoreUpdate(SQLModel):
    score: Optional[float] = None
    rank: Optional[int] = None
    factors_used: Optional[Dict[str, Any]] = None
    momentum_score: Optional[float] = None
    volume_score: Optional[float] = None
    volatility_score: Optional[float] = None
    technical_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    fundamentals_score: Optional[float] = None


# Add other Create/Update models as needed for all tables
