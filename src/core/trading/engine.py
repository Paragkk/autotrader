"""
Enhanced Trading Engine - Integrates with orchestrator and advanced strategies
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from ..broker_adapter import BrokerAdapter, OrderRequest
from .indicators import TechnicalIndicators
from .portfolio import Portfolio
from .trade import Trade

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """Enhanced trading signal with metadata"""

    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    strategy: str
    price: float
    metadata: dict[str, Any]


@dataclass
class TradingRule:
    """Trading rule configuration"""

    name: str
    conditions: list[dict[str, Any]]
    action: str
    weight: float
    enabled: bool = True


class TradingEngine:
    """
    Enhanced trading engine that manages strategy execution and trading decisions.
    """

    def __init__(self, broker: BrokerAdapter, portfolio: Portfolio) -> None:
        self.broker = broker
        self.portfolio = portfolio
        self._active_trades: dict[str, Trade] = {}
        self._indicators: TechnicalIndicators | None = None
        self._trading_data = pd.DataFrame()
        self._trading_rules: list[TradingRule] = []
        self._signal_history: list[TradingSignal] = []
        self._strategy_config = {}

    def update_market_data(self, market_data: pd.DataFrame) -> None:
        """Update market data and recalculate indicators."""
        try:
            self._trading_data = pd.concat([self._trading_data, market_data])

            # Keep only recent data to avoid memory issues
            if len(self._trading_data) > 10000:
                self._trading_data = self._trading_data.tail(5000)

            # Initialize or update indicators
            if self._indicators is None:
                self._indicators = TechnicalIndicators(self._trading_data)
            else:
                self._indicators.data = self._trading_data

            logger.debug(f"Updated market data with {len(market_data)} new rows")

        except Exception as e:
            logger.exception(f"Failed to update market data: {e}")
            raise

    def setup_strategy(self, strategy_config: dict) -> None:
        """Setup trading strategy with indicators and signals."""
        try:
            if not self._indicators:
                msg = "No market data available. Call update_market_data first."
                raise ValueError(msg)

            self._strategy_config = strategy_config

            # Setup indicators based on configuration
            for indicator in strategy_config.get("indicators", []):
                if indicator["type"] == "sma":
                    self._indicators.add_sma(period=indicator["period"])
                elif indicator["type"] == "ema":
                    self._indicators.add_ema(period=indicator["period"])
                elif indicator["type"] == "rsi":
                    self._indicators.add_rsi(period=indicator["period"])
                elif indicator["type"] == "macd":
                    self._indicators.add_macd(
                        fast_period=indicator.get("fast_period", 12),
                        slow_period=indicator.get("slow_period", 26),
                        signal_period=indicator.get("signal_period", 9),
                    )
                elif indicator["type"] == "bollinger":
                    self._indicators.add_bollinger_bands(
                        period=indicator.get("period", 20),
                        std_dev=indicator.get("std_dev", 2),
                    )
                elif indicator["type"] == "stochastic":
                    self._indicators.add_stochastic(
                        k_period=indicator.get("k_period", 14),
                        d_period=indicator.get("d_period", 3),
                    )
                elif indicator["type"] == "volume":
                    self._indicators.add_volume_indicators()

            # Setup trading rules
            self._setup_trading_rules(strategy_config.get("rules", []))

            logger.info(f"Strategy setup completed with {len(self._trading_rules)} rules")

        except Exception as e:
            logger.exception(f"Failed to setup strategy: {e}")
            raise

    def _setup_trading_rules(self, rules_config: list[dict]) -> None:
        """Setup trading rules from configuration"""
        self._trading_rules = []

        for rule_config in rules_config:
            rule = TradingRule(
                name=rule_config["name"],
                conditions=rule_config["conditions"],
                action=rule_config["action"],
                weight=rule_config.get("weight", 1.0),
                enabled=rule_config.get("enabled", True),
            )
            self._trading_rules.append(rule)

    def generate_signals(self, symbol: str, current_price: float) -> list[TradingSignal]:
        """Generate trading signals based on current market conditions"""
        try:
            signals = []

            if not self._indicators or len(self._trading_data) < 50:
                logger.warning(f"Insufficient data for signal generation: {symbol}")
                return signals

            # Get latest indicator values
            latest_data = self._indicators.data.iloc[-1]

            # Evaluate each trading rule
            for rule in self._trading_rules:
                if not rule.enabled:
                    continue

                # Check if all conditions are met
                conditions_met = True
                confidence = 0.0

                for condition in rule.conditions:
                    if not self._evaluate_condition(condition, latest_data, current_price):
                        conditions_met = False
                        break
                    confidence += condition.get("weight", 1.0)

                if conditions_met:
                    # Calculate signal strength based on rule weight and confidence
                    strength = min(rule.weight * confidence / len(rule.conditions), 1.0)

                    signal = TradingSignal(
                        symbol=symbol,
                        signal_type=rule.action,
                        strength=strength,
                        confidence=confidence / len(rule.conditions),
                        timestamp=datetime.now(),
                        strategy=rule.name,
                        price=current_price,
                        metadata={
                            "rule": rule.name,
                            "conditions_met": len(rule.conditions),
                            "indicator_values": latest_data.to_dict(),
                        },
                    )

                    signals.append(signal)
                    logger.debug(f"Generated signal: {signal.signal_type} for {symbol} from {rule.name}")

            # Store signals in history
            self._signal_history.extend(signals)

            # Keep only recent signals
            if len(self._signal_history) > 1000:
                self._signal_history = self._signal_history[-500:]

            return signals

        except Exception as e:
            logger.exception(f"Failed to generate signals for {symbol}: {e}")
            return []

    def _evaluate_condition(self, condition: dict[str, Any], data: pd.Series, current_price: float) -> bool:
        """Evaluate a single trading condition"""
        try:
            condition_type = condition["type"]

            if condition_type == "price_above":
                return current_price > condition["value"]
            if condition_type == "price_below":
                return current_price < condition["value"]
            if condition_type == "sma_crossover":
                sma_short = data.get(f"sma_{condition['short_period']}")
                sma_long = data.get(f"sma_{condition['long_period']}")
                if sma_short is not None and sma_long is not None:
                    return sma_short > sma_long
            elif condition_type == "rsi_oversold":
                rsi = data.get(f"rsi_{condition.get('period', 14)}")
                if rsi is not None:
                    return rsi < condition.get("threshold", 30)
            elif condition_type == "rsi_overbought":
                rsi = data.get(f"rsi_{condition.get('period', 14)}")
                if rsi is not None:
                    return rsi > condition.get("threshold", 70)
            elif condition_type == "volume_spike":
                volume = data.get("volume")
                avg_volume = data.get("volume_sma_20")
                if volume is not None and avg_volume is not None:
                    return volume > avg_volume * condition.get("multiplier", 2.0)
            elif condition_type == "bollinger_breakout":
                price = current_price
                upper_band = data.get("bb_upper")
                lower_band = data.get("bb_lower")
                if upper_band is not None and lower_band is not None:
                    return price > upper_band or price < lower_band
            elif condition_type == "macd_signal":
                macd = data.get("macd")
                macd_signal = data.get("macd_signal")
                if macd is not None and macd_signal is not None:
                    return macd > macd_signal if condition.get("direction") == "bullish" else macd < macd_signal

            return False

        except Exception as e:
            logger.warning(f"Failed to evaluate condition {condition}: {e}")
            return False

    def execute_trade(
        self,
        signal: TradingSignal,
        position_size: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> Trade | None:
        """Execute a trade based on a signal"""
        try:
            # Check if we already have a position
            if signal.symbol in self._active_trades:
                logger.warning(f"Already have active trade for {signal.symbol}")
                return None

            # Calculate order details
            if signal.signal_type == "BUY":
                side = "buy"
                quantity = int(position_size / signal.price)
            elif signal.signal_type == "SELL":
                side = "sell"
                quantity = int(position_size / signal.price)
            else:
                logger.warning(f"Unknown signal type: {signal.signal_type}")
                return None

            if quantity <= 0:
                logger.warning(f"Invalid quantity for {signal.symbol}: {quantity}")
                return None

            # Create order request
            order_request = OrderRequest(
                symbol=signal.symbol,
                quantity=quantity,
                side=side,
                order_type="market",
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

            # Submit order
            order_response = self.broker.submit_order(order_request)

            # Create trade record
            trade = Trade(
                symbol=signal.symbol,
                side=side,
                quantity=quantity,
                entry_price=signal.price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                order_id=order_response.order_id,
                strategy=signal.strategy,
                timestamp=datetime.now(),
            )

            self._active_trades[signal.symbol] = trade

            logger.info(f"Executed trade: {side} {quantity} {signal.symbol} at {signal.price}")

            return trade

        except Exception as e:
            logger.exception(f"Failed to execute trade for {signal.symbol}: {e}")
            return None

    def close_trade(self, symbol: str, reason: str = "Manual close") -> bool:
        """Close an active trade"""
        try:
            if symbol not in self._active_trades:
                logger.warning(f"No active trade found for {symbol}")
                return False

            trade = self._active_trades[symbol]

            # Create closing order
            close_side = "sell" if trade.side == "buy" else "buy"
            order_request = OrderRequest(
                symbol=symbol,
                quantity=trade.quantity,
                side=close_side,
                order_type="market",
            )

            # Submit closing order
            order_response = self.broker.submit_order(order_request)

            # Update trade record
            trade.exit_price = order_response.avg_fill_price
            trade.exit_time = datetime.now()
            trade.close_reason = reason

            # Calculate P&L
            if trade.side == "buy":
                trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
            else:
                trade.pnl = (trade.entry_price - trade.exit_price) * trade.quantity

            # Remove from active trades
            del self._active_trades[symbol]

            logger.info(f"Closed trade: {symbol} P&L: ${trade.pnl:.2f}")

            return True

        except Exception as e:
            logger.exception(f"Failed to close trade for {symbol}: {e}")
            return False

    def get_active_trades(self) -> list[Trade]:
        """Get all active trades"""
        return list(self._active_trades.values())

    def get_trade_performance(self) -> dict[str, Any]:
        """Get trading performance metrics"""
        try:
            active_trades = self.get_active_trades()

            # Calculate unrealized P&L
            unrealized_pnl = 0.0
            for trade in active_trades:
                try:
                    current_price = self._get_current_price(trade.symbol)
                    if current_price:
                        if trade.side == "buy":
                            unrealized_pnl += (current_price - trade.entry_price) * trade.quantity
                        else:
                            unrealized_pnl += (trade.entry_price - current_price) * trade.quantity
                except Exception:
                    continue

            # Calculate signal statistics
            recent_signals = [s for s in self._signal_history if s.timestamp > datetime.now() - timedelta(hours=24)]
            signal_counts = {}

            for signal in recent_signals:
                strategy = signal.strategy
                if strategy not in signal_counts:
                    signal_counts[strategy] = {"buy": 0, "sell": 0, "hold": 0}
                signal_counts[strategy][signal.signal_type.lower()] += 1

            return {
                "active_trades": len(active_trades),
                "unrealized_pnl": unrealized_pnl,
                "signals_24h": len(recent_signals),
                "signal_breakdown": signal_counts,
                "strategies_active": len(self._trading_rules),
                "data_points": len(self._trading_data),
            }

        except Exception as e:
            logger.exception(f"Failed to get trade performance: {e}")
            return {}

    def _get_current_price(self, symbol: str) -> float | None:
        """Get current price for a symbol"""
        try:
            # This would normally query real-time data
            # For now, return the last known price from trading data
            if not self._trading_data.empty:
                return self._trading_data["close"].iloc[-1]
            return None
        except Exception:
            return None

    def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """Clean up old trading data and signals"""
        try:
            # Clean up old trading data
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            if not self._trading_data.empty and "timestamp" in self._trading_data.columns:
                self._trading_data = self._trading_data[self._trading_data["timestamp"] > cutoff_date]

            # Clean up old signals
            self._signal_history = [s for s in self._signal_history if s.timestamp > cutoff_date]

            logger.info(f"Cleaned up data older than {days_to_keep} days")

        except Exception as e:
            logger.exception(f"Failed to cleanup old data: {e}")

    def get_strategy_config(self) -> dict[str, Any]:
        """Get current strategy configuration"""
        return {
            "config": self._strategy_config,
            "rules": [
                {
                    "name": rule.name,
                    "action": rule.action,
                    "weight": rule.weight,
                    "enabled": rule.enabled,
                    "conditions": len(rule.conditions),
                }
                for rule in self._trading_rules
            ],
            "indicators": len(self._indicators.data.columns) if self._indicators else 0,
        }

    def _get_current_price(self, symbol: str) -> float:
        """Get the current market price for a symbol."""
        return self._trading_data.loc[symbol]["close"].iloc[-1]

    def get_trading_metrics(self) -> dict:
        """Get current trading metrics and performance."""
        current_prices = {symbol: self._get_current_price(symbol) for symbol in set(list(self.portfolio.positions.keys()) + list(self._active_trades.keys()))}

        return {
            "portfolio_metrics": self.portfolio.get_portfolio_metrics(current_prices),
            "active_trades": len(self._active_trades),
            "total_trades": len(self._active_trades),  # Add historical trades count here
            "current_positions": len(self.portfolio.positions),
        }
