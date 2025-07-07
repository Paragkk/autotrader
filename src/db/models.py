"""
Database models for the automated trading system
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class ScreenedStock(Base):
    """Table for storing screened stocks"""

    __tablename__ = "screened_stocks"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    screened_at = Column(DateTime, default=func.now(), nullable=False)
    screening_criteria = Column(JSON, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    daily_change = Column(Float, nullable=False)
    market_cap = Column(Float)
    sector = Column(String(50))

    # Relationships
    scores = relationship("StockScore", back_populates="screened_stock")


class StockScore(Base):
    """Table for storing stock scores and rankings"""

    __tablename__ = "stock_scores"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    screened_stock_id = Column(Integer, ForeignKey("screened_stocks.id"))
    scored_at = Column(DateTime, default=func.now(), nullable=False)
    score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    factors_used = Column(JSON, nullable=False)

    # Factor scores
    momentum_score = Column(Float)
    volume_score = Column(Float)
    volatility_score = Column(Float)
    technical_score = Column(Float)
    sentiment_score = Column(Float)
    fundamentals_score = Column(Float)

    # Relationships
    screened_stock = relationship("ScreenedStock", back_populates="scores")
    tracked_symbol = relationship("TrackedSymbol", back_populates="stock_score")


class TrackedSymbol(Base):
    """Table for dynamically tracked symbols"""

    __tablename__ = "tracked_symbols"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    stock_score_id = Column(Integer, ForeignKey("stock_scores.id"))
    added_at = Column(DateTime, default=func.now(), nullable=False)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False)
    reason_added = Column(String(100))  # 'screening', 'manual', 'news'

    # Relationships
    stock_score = relationship("StockScore", back_populates="tracked_symbol")
    strategy_results = relationship("StrategyResult", back_populates="tracked_symbol")


class StrategyResult(Base):
    """Table for storing strategy analysis results"""

    __tablename__ = "strategy_results"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    tracked_symbol_id = Column(Integer, ForeignKey("tracked_symbols.id"))
    strategy_name = Column(String(50), nullable=False)
    signal = Column(String(10), nullable=False)  # 'buy', 'sell', 'hold'
    strength = Column(Float, nullable=False)  # 0.0 to 1.0
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    analyzed_at = Column(DateTime, default=func.now(), nullable=False)
    price_at_analysis = Column(Float, nullable=False)

    # Strategy-specific data
    strategy_data = Column(JSON)  # Store strategy-specific parameters

    # Relationships
    tracked_symbol = relationship("TrackedSymbol", back_populates="strategy_results")


class Signal(Base):
    """Table for storing aggregated trading signals"""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # 'buy', 'sell'
    confidence_score = Column(Float, nullable=False)
    strength = Column(Float, nullable=False)
    generated_at = Column(DateTime, default=func.now(), nullable=False)
    price_at_signal = Column(Float, nullable=False)

    # Aggregation details
    strategy_count = Column(Integer, nullable=False)
    contributing_strategies = Column(JSON, nullable=False)

    # Status tracking
    status = Column(
        String(20), default="pending"
    )  # 'pending', 'executed', 'rejected', 'expired'

    # Relationships
    order = relationship("Order", back_populates="signal", uselist=False)
    risk_filter = relationship(
        "RiskFilterResult", back_populates="signal", uselist=False
    )


class RiskFilterResult(Base):
    """Table for storing risk management filter results"""

    __tablename__ = "risk_filter_results"

    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    symbol = Column(String(10), nullable=False, index=True)
    filtered_at = Column(DateTime, default=func.now(), nullable=False)
    passed = Column(Boolean, nullable=False)
    rejection_reason = Column(String(200))

    # Risk metrics
    position_size = Column(Float)
    exposure_percent = Column(Float)
    portfolio_risk = Column(Float)
    sector_exposure = Column(Float)
    correlation_risk = Column(Float)

    # Relationships
    signal = relationship("Signal", back_populates="risk_filter")


class Order(Base):
    """Table for storing order information"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    broker_order_id = Column(String(50), unique=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # 'buy', 'sell'
    quantity = Column(Float, nullable=False)
    order_type = Column(String(20), nullable=False)  # 'market', 'limit', 'stop'
    price = Column(Float)
    stop_price = Column(Float)
    time_in_force = Column(String(10), default="day")

    # Order lifecycle
    status = Column(
        String(20), nullable=False
    )  # 'pending', 'filled', 'cancelled', 'rejected'
    created_at = Column(DateTime, default=func.now(), nullable=False)
    submitted_at = Column(DateTime)
    filled_at = Column(DateTime)
    cancelled_at = Column(DateTime)

    # Execution details
    filled_quantity = Column(Float, default=0.0)
    filled_price = Column(Float)
    commission = Column(Float)

    # Relationships
    signal = relationship("Signal", back_populates="order")
    position = relationship(
        "Position", back_populates="entry_order", foreign_keys="Position.entry_order_id"
    )


class Position(Base):
    """Table for storing position information"""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    entry_order_id = Column(Integer, ForeignKey("orders.id"))
    exit_order_id = Column(Integer, ForeignKey("orders.id"))

    # Position details
    quantity = Column(Float, nullable=False)
    side = Column(String(10), nullable=False)  # 'long', 'short'
    avg_entry_price = Column(Float, nullable=False)
    avg_exit_price = Column(Float)

    # Lifecycle
    status = Column(String(20), nullable=False)  # 'open', 'closed', 'partial'
    opened_at = Column(DateTime, default=func.now(), nullable=False)
    closed_at = Column(DateTime)

    # P&L tracking
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float)

    # Stop loss and take profit
    stop_loss_price = Column(Float)
    take_profit_price = Column(Float)

    # Relationships
    entry_order = relationship(
        "Order", foreign_keys=[entry_order_id], back_populates="position"
    )
    exit_order = relationship("Order", foreign_keys=[exit_order_id])
    trade_log = relationship("TradeLog", back_populates="position", uselist=False)


class TradeLog(Base):
    """Table for complete trade audit logging"""

    __tablename__ = "trade_logs"

    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("positions.id"))
    symbol = Column(String(10), nullable=False, index=True)

    # Trade timeline
    signal_generated_at = Column(DateTime, nullable=False)
    order_placed_at = Column(DateTime, nullable=False)
    position_opened_at = Column(DateTime, nullable=False)
    position_closed_at = Column(DateTime)

    # Trade details
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    quantity = Column(Float, nullable=False)
    holding_period = Column(Integer)  # in minutes

    # Performance metrics
    gross_pnl = Column(Float)
    net_pnl = Column(Float)
    return_percent = Column(Float)
    commission_paid = Column(Float)

    # Strategy attribution
    strategy_name = Column(String(50))
    signal_strength = Column(Float)

    # Market context
    market_conditions = Column(JSON)

    # Relationships
    position = relationship("Position", back_populates="trade_log")


class SystemMetrics(Base):
    """Table for storing system performance metrics"""

    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True)
    recorded_at = Column(DateTime, default=func.now(), nullable=False)

    # Portfolio metrics
    total_equity = Column(Float)
    available_cash = Column(Float)
    total_positions = Column(Integer)
    daily_pnl = Column(Float)

    # Trading metrics
    signals_generated = Column(Integer)
    orders_placed = Column(Integer)
    orders_filled = Column(Integer)
    win_rate = Column(Float)

    # System health
    screening_runtime = Column(Float)  # seconds
    strategy_runtime = Column(Float)  # seconds
    order_execution_time = Column(Float)  # seconds

    # Market data
    market_hours = Column(Boolean)
    market_volatility = Column(Float)


class ConfigurationHistory(Base):
    """Table for tracking configuration changes"""

    __tablename__ = "configuration_history"

    id = Column(Integer, primary_key=True)
    changed_at = Column(DateTime, default=func.now(), nullable=False)
    changed_by = Column(String(50), default="system")
    config_section = Column(String(50), nullable=False)
    old_value = Column(JSON)
    new_value = Column(JSON)
    reason = Column(String(200))
