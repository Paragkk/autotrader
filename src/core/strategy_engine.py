"""
Strategy Engine - Enhanced with Multi-Strategy Support
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import pandas as pd

from db.repository import SignalRepository

logger = logging.getLogger(__name__)


class TradingStrategy(ABC):
    """Abstract base class for trading strategies"""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", True)
        self.weight = config.get("weight", 1.0)

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> list[dict[str, Any]]:
        """Generate trading signals based on market data"""

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate strategy configuration"""

    def get_metadata(self) -> dict[str, Any]:
        """Get strategy metadata"""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "weight": self.weight,
            "config": self.config,
        }


class MovingAverageCrossoverStrategy(TradingStrategy):
    """Simple moving average crossover strategy"""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self.short_window = config.get("short_window", 10)
        self.long_window = config.get("long_window", 30)
        self.validate_config()

    def validate_config(self) -> bool:
        """Validate strategy configuration"""
        if self.short_window >= self.long_window:
            msg = "Short window must be less than long window"
            raise ValueError(msg)
        return True

    def generate_signals(self, data: pd.DataFrame) -> list[dict[str, Any]]:
        """Generate signals based on moving average crossover"""
        signals = []

        if len(data) < self.long_window:
            return signals

        # Calculate moving averages
        data = data.copy()
        data[f"sma_{self.short_window}"] = data["close"].rolling(window=self.short_window).mean()
        data[f"sma_{self.long_window}"] = data["close"].rolling(window=self.long_window).mean()

        # Generate signals
        for i in range(1, len(data)):
            current_short = data[f"sma_{self.short_window}"].iloc[i]
            current_long = data[f"sma_{self.long_window}"].iloc[i]
            prev_short = data[f"sma_{self.short_window}"].iloc[i - 1]
            prev_long = data[f"sma_{self.long_window}"].iloc[i - 1]

            # Check for crossover
            if prev_short <= prev_long and current_short > current_long:
                # Golden cross - buy signal
                signals.append(
                    {
                        "symbol": data["symbol"].iloc[i],
                        "strategy_name": self.name,
                        "signal_type": "buy",
                        "strength": 0.8,
                        "price": data["close"].iloc[i],
                        "timestamp": data["date"].iloc[i] if "date" in data.columns else datetime.now(),
                        "metadata": {
                            "short_ma": current_short,
                            "long_ma": current_long,
                            "crossover_type": "golden_cross",
                        },
                    }
                )
            elif prev_short >= prev_long and current_short < current_long:
                # Death cross - sell signal
                signals.append(
                    {
                        "symbol": data["symbol"].iloc[i],
                        "strategy_name": self.name,
                        "signal_type": "sell",
                        "strength": 0.8,
                        "price": data["close"].iloc[i],
                        "timestamp": data["date"].iloc[i] if "date" in data.columns else datetime.now(),
                        "metadata": {
                            "short_ma": current_short,
                            "long_ma": current_long,
                            "crossover_type": "death_cross",
                        },
                    }
                )

        return signals


class RSIStrategy(TradingStrategy):
    """RSI-based trading strategy"""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self.period = config.get("period", 14)
        self.oversold_threshold = config.get("oversold_threshold", 30)
        self.overbought_threshold = config.get("overbought_threshold", 70)
        self.validate_config()

    def validate_config(self) -> bool:
        """Validate strategy configuration"""
        if self.oversold_threshold >= self.overbought_threshold:
            msg = "Oversold threshold must be less than overbought threshold"
            raise ValueError(msg)
        return True

    def _calculate_rsi(self, prices: pd.Series) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def generate_signals(self, data: pd.DataFrame) -> list[dict[str, Any]]:
        """Generate signals based on RSI"""
        signals = []

        if len(data) < self.period:
            return signals

        # Calculate RSI
        data = data.copy()
        data["rsi"] = self._calculate_rsi(data["close"])

        # Generate signals
        for i in range(1, len(data)):
            current_rsi = data["rsi"].iloc[i]
            prev_rsi = data["rsi"].iloc[i - 1]

            if pd.isna(current_rsi) or pd.isna(prev_rsi):
                continue

            # Check for oversold condition (buy signal)
            if prev_rsi <= self.oversold_threshold and current_rsi > self.oversold_threshold:
                signals.append(
                    {
                        "symbol": data["symbol"].iloc[i],
                        "strategy_name": self.name,
                        "signal_type": "buy",
                        "strength": min(1.0, (self.oversold_threshold - prev_rsi) / 10),
                        "price": data["close"].iloc[i],
                        "timestamp": data["date"].iloc[i] if "date" in data.columns else datetime.now(),
                        "metadata": {"rsi": current_rsi, "condition": "oversold_exit"},
                    }
                )
            # Check for overbought condition (sell signal)
            elif prev_rsi >= self.overbought_threshold and current_rsi < self.overbought_threshold:
                signals.append(
                    {
                        "symbol": data["symbol"].iloc[i],
                        "strategy_name": self.name,
                        "signal_type": "sell",
                        "strength": min(1.0, (prev_rsi - self.overbought_threshold) / 10),
                        "price": data["close"].iloc[i],
                        "timestamp": data["date"].iloc[i] if "date" in data.columns else datetime.now(),
                        "metadata": {
                            "rsi": current_rsi,
                            "condition": "overbought_exit",
                        },
                    }
                )

        return signals


class MomentumStrategy(TradingStrategy):
    """Price momentum-based strategy"""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self.lookback_period = config.get("lookback_period", 20)
        self.momentum_threshold = config.get("momentum_threshold", 0.05)  # 5%
        self.validate_config()

    def validate_config(self) -> bool:
        """Validate strategy configuration"""
        if self.lookback_period <= 0:
            msg = "Lookback period must be positive"
            raise ValueError(msg)
        return True

    def generate_signals(self, data: pd.DataFrame) -> list[dict[str, Any]]:
        """Generate signals based on price momentum"""
        signals = []

        if len(data) < self.lookback_period:
            return signals

        # Calculate momentum
        data = data.copy()
        data["momentum"] = data["close"].pct_change(periods=self.lookback_period)

        # Generate signals
        for i in range(self.lookback_period, len(data)):
            momentum = data["momentum"].iloc[i]

            if pd.isna(momentum):
                continue

            # Strong positive momentum - buy signal
            if momentum > self.momentum_threshold:
                signals.append(
                    {
                        "symbol": data["symbol"].iloc[i],
                        "strategy_name": self.name,
                        "signal_type": "buy",
                        "strength": min(1.0, momentum / (self.momentum_threshold * 2)),
                        "price": data["close"].iloc[i],
                        "timestamp": data["date"].iloc[i] if "date" in data.columns else datetime.now(),
                        "metadata": {
                            "momentum": momentum,
                            "condition": "positive_momentum",
                        },
                    }
                )
            # Strong negative momentum - sell signal
            elif momentum < -self.momentum_threshold:
                signals.append(
                    {
                        "symbol": data["symbol"].iloc[i],
                        "strategy_name": self.name,
                        "signal_type": "sell",
                        "strength": min(1.0, abs(momentum) / (self.momentum_threshold * 2)),
                        "price": data["close"].iloc[i],
                        "timestamp": data["date"].iloc[i] if "date" in data.columns else datetime.now(),
                        "metadata": {
                            "momentum": momentum,
                            "condition": "negative_momentum",
                        },
                    }
                )

        return signals


class StrategyEngine:
    """
    Engine for loading and running multiple trading strategies
    """

    def __init__(self, signal_repo: SignalRepository) -> None:
        self.strategies: dict[str, TradingStrategy] = {}
        self.signal_repo = signal_repo

    def load_strategy(self, strategy: TradingStrategy) -> None:
        """Load a strategy into the engine"""
        if strategy.name in self.strategies:
            logger.warning(f"Strategy {strategy.name} already exists, replacing...")

        self.strategies[strategy.name] = strategy
        logger.info(f"Loaded strategy: {strategy.name}")

    def remove_strategy(self, strategy_name: str) -> None:
        """Remove a strategy from the engine"""
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            logger.info(f"Removed strategy: {strategy_name}")
        else:
            logger.warning(f"Strategy {strategy_name} not found")

    def run_all_strategies(self, data: dict[str, pd.DataFrame]) -> dict[str, list[dict[str, Any]]]:
        """Run all loaded strategies on the provided data"""
        all_signals = {}

        for strategy_name, strategy in self.strategies.items():
            if not strategy.enabled:
                logger.debug(f"Skipping disabled strategy: {strategy_name}")
                continue

            strategy_signals = []

            for symbol, symbol_data in data.items():
                try:
                    # Add symbol column if not present
                    if "symbol" not in symbol_data.columns:
                        symbol_data = symbol_data.copy()
                        symbol_data["symbol"] = symbol

                    signals = strategy.generate_signals(symbol_data)
                    strategy_signals.extend(signals)

                    # Store signals in database
                    for signal in signals:
                        self.signal_repo.add(signal)

                except Exception as e:
                    logger.exception(f"Error running strategy {strategy_name} on {symbol}: {e}")
                    continue

            all_signals[strategy_name] = strategy_signals
            logger.info(f"Strategy {strategy_name} generated {len(strategy_signals)} signals")

        return all_signals

    def run_strategy(self, strategy_name: str, data: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
        """Run a specific strategy on the provided data"""
        if strategy_name not in self.strategies:
            msg = f"Strategy {strategy_name} not found"
            raise ValueError(msg)

        strategy = self.strategies[strategy_name]
        if not strategy.enabled:
            logger.warning(f"Strategy {strategy_name} is disabled")
            return []

        all_signals = []

        for symbol, symbol_data in data.items():
            try:
                # Add symbol column if not present
                if "symbol" not in symbol_data.columns:
                    symbol_data = symbol_data.copy()
                    symbol_data["symbol"] = symbol

                signals = strategy.generate_signals(symbol_data)
                all_signals.extend(signals)

                # Store signals in database
                for signal in signals:
                    self.signal_repo.add(signal)

            except Exception as e:
                logger.exception(f"Error running strategy {strategy_name} on {symbol}: {e}")
                continue

        logger.info(f"Strategy {strategy_name} generated {len(all_signals)} signals")
        return all_signals

    def get_strategy_info(self) -> dict[str, dict[str, Any]]:
        """Get information about all loaded strategies"""
        return {name: strategy.get_metadata() for name, strategy in self.strategies.items()}

    def enable_strategy(self, strategy_name: str) -> None:
        """Enable a strategy"""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].enabled = True
            logger.info(f"Enabled strategy: {strategy_name}")
        else:
            logger.warning(f"Strategy {strategy_name} not found")

    def disable_strategy(self, strategy_name: str) -> None:
        """Disable a strategy"""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].enabled = False
            logger.info(f"Disabled strategy: {strategy_name}")
        else:
            logger.warning(f"Strategy {strategy_name} not found")

    def create_strategy_from_config(self, config: dict[str, Any]) -> TradingStrategy:
        """Create a strategy from configuration"""
        strategy_type = config.get("type")
        strategy_name = config.get("name")

        if not strategy_type or not strategy_name:
            msg = "Strategy config must include 'type' and 'name'"
            raise ValueError(msg)

        if strategy_type == "moving_average_crossover":
            return MovingAverageCrossoverStrategy(strategy_name, config)
        if strategy_type == "rsi":
            return RSIStrategy(strategy_name, config)
        if strategy_type == "momentum":
            return MomentumStrategy(strategy_name, config)
        msg = f"Unknown strategy type: {strategy_type}"
        raise ValueError(msg)

    def load_strategies_from_config(self, strategies_config: list[dict[str, Any]]) -> None:
        """Load multiple strategies from configuration"""
        for config in strategies_config:
            try:
                strategy = self.create_strategy_from_config(config)
                self.load_strategy(strategy)
            except Exception as e:
                logger.exception(f"Failed to load strategy from config {config}: {e}")
                continue
