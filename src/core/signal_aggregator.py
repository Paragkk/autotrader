"""
Signal Aggregator - Enhanced with Multiple Aggregation Methods
"""

import logging
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from db.repository import SignalRepository

logger = logging.getLogger(__name__)


class SignalAggregator:
    """
    Aggregates and combines signals from different strategies
    """

    def __init__(self, signal_repo: SignalRepository) -> None:
        self.signal_repo = signal_repo
        self.aggregation_methods = {
            "weighted_average": self._weighted_average_aggregation,
            "majority_vote": self._majority_vote_aggregation,
            "strongest_signal": self._strongest_signal_aggregation,
            "consensus": self._consensus_aggregation,
        }

    def aggregate_signals(
        self,
        symbols: list[str] | None = None,
        time_window_minutes: int = 60,
        method: str = "weighted_average",
        min_strategies: int = 2,
    ) -> dict[str, dict[str, Any]]:
        """
        Aggregate signals for symbols within a time window

        Args:
            symbols: List of symbols to aggregate (None for all)
            time_window_minutes: Time window to consider for aggregation
            method: Aggregation method to use
            min_strategies: Minimum number of strategies required for aggregation

        Returns:
            Dict with aggregated signals per symbol
        """
        try:
            # Get recent unprocessed signals
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)

            all_signals = self.signal_repo.get_unprocessed_signals()

            # Filter by time and symbols
            filtered_signals = []
            for signal in all_signals:
                signal_time = datetime.fromisoformat(signal["timestamp"].replace("Z", "+00:00"))
                if signal_time >= cutoff_time:
                    if symbols is None or signal["symbol"] in symbols:
                        filtered_signals.append(signal)

            # Group signals by symbol
            signals_by_symbol = defaultdict(list)
            for signal in filtered_signals:
                signals_by_symbol[signal["symbol"]].append(signal)

            # Aggregate signals for each symbol
            aggregated_signals = {}

            if method not in self.aggregation_methods:
                msg = f"Unknown aggregation method: {method}"
                raise ValueError(msg)

            aggregation_func = self.aggregation_methods[method]

            for symbol, symbol_signals in signals_by_symbol.items():
                # Group by signal type
                buy_signals = [s for s in symbol_signals if s["signal_type"] == "buy"]
                sell_signals = [s for s in symbol_signals if s["signal_type"] == "sell"]

                # Check if we have minimum strategies
                total_strategies = len({s["strategy_name"] for s in symbol_signals})
                if total_strategies < min_strategies:
                    logger.debug(f"Skipping {symbol}: only {total_strategies} strategies (min: {min_strategies})")
                    continue

                # Aggregate buy and sell signals separately
                aggregated_buy = aggregation_func(buy_signals) if buy_signals else None
                aggregated_sell = aggregation_func(sell_signals) if sell_signals else None

                # Determine final signal
                final_signal = self._determine_final_signal(aggregated_buy, aggregated_sell)

                if final_signal:
                    aggregated_signals[symbol] = {
                        "symbol": symbol,
                        "final_signal": final_signal,
                        "aggregated_buy": aggregated_buy,
                        "aggregated_sell": aggregated_sell,
                        "contributing_strategies": list({s["strategy_name"] for s in symbol_signals}),
                        "total_signals": len(symbol_signals),
                        "aggregation_method": method,
                        "timestamp": datetime.now(),
                    }

            logger.info(f"Aggregated signals for {len(aggregated_signals)} symbols using {method} method")
            return aggregated_signals

        except Exception as e:
            logger.exception(f"Error aggregating signals: {e}")
            raise

    def _weighted_average_aggregation(self, signals: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Aggregate signals using weighted average"""
        if not signals:
            return None

        # Calculate weighted strength
        total_weight = 0
        weighted_strength = 0
        strategy_weights = {}

        for signal in signals:
            # Get strategy weight (default 1.0)
            weight = strategy_weights.get(signal["strategy_name"], 1.0)
            total_weight += weight
            weighted_strength += signal["strength"] * weight

        if total_weight == 0:
            return None

        avg_strength = weighted_strength / total_weight
        avg_price = statistics.mean([s["price"] for s in signals if s["price"]])

        return {
            "signal_type": signals[0]["signal_type"],
            "strength": avg_strength,
            "price": avg_price,
            "confidence": min(1.0, len(signals) / 5.0),  # Higher confidence with more signals
            "contributing_signals": len(signals),
            "method": "weighted_average",
        }

    def _majority_vote_aggregation(self, signals: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Aggregate signals using majority vote"""
        if not signals:
            return None

        # Count votes
        signal_types = [s["signal_type"] for s in signals]
        signal_counts = defaultdict(int)

        for signal_type in signal_types:
            signal_counts[signal_type] += 1

        # Find majority
        max_votes = max(signal_counts.values())
        majority_signals = [sig_type for sig_type, count in signal_counts.items() if count == max_votes]

        if len(majority_signals) > 1:
            # Tie - no clear majority
            return None

        majority_type = majority_signals[0]
        majority_signals_data = [s for s in signals if s["signal_type"] == majority_type]

        avg_strength = statistics.mean([s["strength"] for s in majority_signals_data])
        avg_price = statistics.mean([s["price"] for s in majority_signals_data if s["price"]])

        return {
            "signal_type": majority_type,
            "strength": avg_strength,
            "price": avg_price,
            "confidence": max_votes / len(signals),
            "contributing_signals": max_votes,
            "method": "majority_vote",
        }

    def _strongest_signal_aggregation(self, signals: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Aggregate by taking the strongest signal"""
        if not signals:
            return None

        # Find strongest signal
        strongest_signal = max(signals, key=lambda s: s["strength"])

        return {
            "signal_type": strongest_signal["signal_type"],
            "strength": strongest_signal["strength"],
            "price": strongest_signal["price"],
            "confidence": strongest_signal["strength"],
            "contributing_signals": 1,
            "method": "strongest_signal",
            "source_strategy": strongest_signal["strategy_name"],
        }

    def _consensus_aggregation(self, signals: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Aggregate requiring consensus (all signals agree)"""
        if not signals:
            return None

        # Check if all signals agree
        signal_types = {s["signal_type"] for s in signals}

        if len(signal_types) > 1:
            # No consensus
            return None

        signal_type = next(iter(signal_types))
        avg_strength = statistics.mean([s["strength"] for s in signals])
        avg_price = statistics.mean([s["price"] for s in signals if s["price"]])

        return {
            "signal_type": signal_type,
            "strength": avg_strength,
            "price": avg_price,
            "confidence": 1.0,  # Full confidence with consensus
            "contributing_signals": len(signals),
            "method": "consensus",
        }

    def _determine_final_signal(self, buy_signal: dict[str, Any] | None = None, sell_signal: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Determine final signal from aggregated buy/sell signals"""
        if buy_signal is None and sell_signal is None:
            return None

        # If only one type of signal
        if buy_signal is None:
            return sell_signal
        if sell_signal is None:
            return buy_signal

        # Both buy and sell signals exist - compare strength and confidence
        buy_score = buy_signal["strength"] * buy_signal["confidence"]
        sell_score = sell_signal["strength"] * sell_signal["confidence"]

        # Require significant difference to avoid trading noise
        threshold = 0.1

        if buy_score > sell_score + threshold:
            return buy_signal
        if sell_score > buy_score + threshold:
            return sell_signal
        # Signals are too close - no action
        return {
            "signal_type": "hold",
            "strength": 0.5,
            "price": (buy_signal["price"] + sell_signal["price"]) / 2,
            "confidence": 0.5,
            "contributing_signals": buy_signal["contributing_signals"] + sell_signal["contributing_signals"],
            "method": "conflict_resolution",
            "reason": "buy_sell_conflict",
        }

    def get_aggregated_signals_by_strength(
        self,
        aggregated_signals: dict[str, dict[str, Any]],
        min_strength: float = 0.6,
        min_confidence: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Filter and sort aggregated signals by strength and confidence"""
        filtered_signals = []

        for symbol, signal_data in aggregated_signals.items():
            final_signal = signal_data["final_signal"]

            if final_signal and final_signal["strength"] >= min_strength and final_signal["confidence"] >= min_confidence and final_signal["signal_type"] != "hold":
                filtered_signals.append({"symbol": symbol, **final_signal, "metadata": signal_data})

        # Sort by combined score (strength * confidence)
        filtered_signals.sort(key=lambda s: s["strength"] * s["confidence"], reverse=True)

        return filtered_signals

    def mark_signals_processed(self, aggregated_signals: dict[str, dict[str, Any]]) -> None:
        """Mark the signals used in aggregation as processed"""
        try:
            all_signal_ids = []

            for symbol, _signal_data in aggregated_signals.items():
                # Get all signals for this symbol that were processed
                recent_signals = self.signal_repo.get_unprocessed_signals(symbol=symbol)

                # Mark them as processed
                signal_ids = [str(s["id"]) for s in recent_signals]
                all_signal_ids.extend(signal_ids)

            if all_signal_ids:
                self.signal_repo.mark_processed(all_signal_ids)
                logger.info(f"Marked {len(all_signal_ids)} signals as processed")

        except Exception as e:
            logger.exception(f"Error marking signals as processed: {e}")

    def get_signal_statistics(self, days_back: int = 7) -> dict[str, Any]:
        """Get statistics about recent signals"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_back)

            # Get recent signals
            all_signals = self.signal_repo.list(limit=10000)  # Large limit to get all recent
            recent_signals = [s for s in all_signals if datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00")) >= cutoff_time]

            # Calculate statistics
            total_signals = len(recent_signals)
            by_type = defaultdict(int)
            by_strategy = defaultdict(int)
            by_symbol = defaultdict(int)

            for signal in recent_signals:
                by_type[signal["signal_type"]] += 1
                by_strategy[signal["strategy_name"]] += 1
                by_symbol[signal["symbol"]] += 1

            return {
                "total_signals": total_signals,
                "time_period_days": days_back,
                "signals_by_type": dict(by_type),
                "signals_by_strategy": dict(by_strategy),
                "most_active_symbols": dict(sorted(by_symbol.items(), key=lambda x: x[1], reverse=True)[:10]),
                "average_signals_per_day": total_signals / days_back if days_back > 0 else 0,
            }

        except Exception as e:
            logger.exception(f"Error getting signal statistics: {e}")
            return {}

    async def aggregate_strategy_results(self, strategy_results: list[Any]) -> dict[str, Any]:
        """
        Aggregate strategy results directly (not from database)

        Args:
            strategy_results: List of StrategyResult objects

        Returns:
            Dict with aggregated signal data
        """
        try:
            if not strategy_results:
                return {
                    "direction": "hold",
                    "confidence": 0.0,
                    "strength": 0.0,
                    "price": 0.0,
                    "strategies": [],
                }

            # Convert strategy results to signal format
            signals = []
            for result in strategy_results:
                signals.append(
                    {
                        "signal_type": result.signal,
                        "strength": result.strength,
                        "confidence": result.confidence,
                        "strategy_name": result.strategy_name,
                        "price": result.price_at_analysis,
                    }
                )

            # Aggregate using weighted average method
            aggregated = self._weighted_average_aggregation(signals)

            return {
                "direction": aggregated["signal_type"] if aggregated else "hold",
                "confidence": aggregated["confidence"] if aggregated else 0.0,
                "strength": aggregated["strength"] if aggregated else 0.0,
                "price": aggregated["price"] if aggregated else 0.0,
                "strategies": [s["strategy_name"] for s in signals],
            }

        except Exception as e:
            logger.exception(f"Error aggregating strategy results: {e}")
            return {
                "direction": "hold",
                "confidence": 0.0,
                "strength": 0.0,
                "price": 0.0,
                "strategies": [],
            }
