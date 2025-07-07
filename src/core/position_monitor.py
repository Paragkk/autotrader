"""
Position Monitor - Monitors open positions and manages exits
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from brokers.base.broker_adapter import BrokerAdapter

logger = logging.getLogger(__name__)


@dataclass
class ExitCondition:
    """Exit condition configuration"""

    stop_loss_percent: float = 0.03  # 3% stop loss
    take_profit_percent: float = 0.08  # 8% take profit
    trailing_stop_percent: float = 0.02  # 2% trailing stop
    max_holding_period_days: int = 30  # Maximum holding period
    min_holding_period_minutes: int = 60  # Minimum holding period


class PositionMonitor:
    """
    Monitors open positions and manages exit conditions
    """

    def __init__(
        self,
        broker_adapter: BrokerAdapter,
        exit_conditions: Optional[ExitCondition] = None,
    ):
        self.broker_adapter = broker_adapter
        self.exit_conditions = exit_conditions or ExitCondition()

    async def monitor_positions(self) -> Dict[str, Any]:
        """
        Monitor all open positions for exit conditions

        Returns:
            Dictionary with monitoring results
        """
        logger.info("👁️ Monitoring open positions")

        try:
            # Get current positions
            positions = await self.broker_adapter.get_positions()

            if not positions:
                logger.info("📊 No open positions to monitor")
                return {"positions_monitored": 0, "exit_signals": []}

            exit_signals = []

            # Check each position
            for position in positions:
                exit_signal = await self._check_position_exit(position)
                if exit_signal:
                    exit_signals.append(exit_signal)

            logger.info(
                f"✅ Position monitoring completed: {len(positions)} positions, {len(exit_signals)} exit signals"
            )

            return {
                "positions_monitored": len(positions),
                "exit_signals": exit_signals,
                "monitoring_time": datetime.now(),
            }

        except Exception as e:
            logger.error(f"❌ Position monitoring failed: {e}")
            return {"error": str(e)}

    async def _check_position_exit(self, position) -> Optional[Dict[str, Any]]:
        """
        Check if a position should be exited

        Args:
            position: Position object from broker

        Returns:
            Exit signal dictionary if position should be exited, None otherwise
        """
        symbol = position.symbol

        try:
            # Get current price
            current_price = await self.broker_adapter.get_current_price(symbol)

            # Calculate position metrics
            entry_price = float(position.avg_entry_price)
            quantity = float(position.qty)

            # Calculate P&L
            if position.side == "long":
                pnl = (current_price - entry_price) * quantity
                pnl_percent = (current_price - entry_price) / entry_price
            else:  # short position
                pnl = (entry_price - current_price) * quantity
                pnl_percent = (entry_price - current_price) / entry_price

            # Check exit conditions
            exit_reason = None

            # 1. Stop Loss Check
            if pnl_percent <= -self.exit_conditions.stop_loss_percent:
                exit_reason = "stop_loss"

            # 2. Take Profit Check
            elif pnl_percent >= self.exit_conditions.take_profit_percent:
                exit_reason = "take_profit"

            # 3. Maximum Holding Period Check
            elif self._check_max_holding_period(position):
                exit_reason = "max_holding_period"

            # 4. Trailing Stop Check
            elif await self._check_trailing_stop(position, current_price):
                exit_reason = "trailing_stop"

            # 5. Technical Exit Signal Check
            elif await self._check_technical_exit(symbol, position.side):
                exit_reason = "technical_exit"

            if exit_reason:
                logger.info(f"🚪 Exit signal generated: {symbol} - {exit_reason}")

                return {
                    "symbol": symbol,
                    "exit_reason": exit_reason,
                    "current_price": current_price,
                    "entry_price": entry_price,
                    "pnl": pnl,
                    "pnl_percent": pnl_percent,
                    "quantity": quantity,
                    "side": position.side,
                    "urgency": self._get_exit_urgency(exit_reason),
                }

        except Exception as e:
            logger.error(f"❌ Error checking exit for {symbol}: {e}")

        return None

    def _check_max_holding_period(self, position) -> bool:
        """Check if position has exceeded maximum holding period"""
        try:
            # Get position entry time (this would come from your database)
            # For now, assume we can get it from the position object
            if hasattr(position, "created_at"):
                entry_time = position.created_at
                holding_period = datetime.now() - entry_time

                if holding_period.days >= self.exit_conditions.max_holding_period_days:
                    return True

        except Exception as e:
            logger.error(f"❌ Error checking holding period: {e}")

        return False

    async def _check_trailing_stop(self, position, current_price: float) -> bool:
        """Check trailing stop condition"""
        try:
            # This would require tracking the highest price since entry
            # For now, implement basic trailing stop logic
            # TODO: Implement proper trailing stop with peak tracking
            return False

        except Exception as e:
            logger.error(f"❌ Error checking trailing stop: {e}")
            return False

    async def _check_technical_exit(self, symbol: str, side: str) -> bool:
        """Check technical analysis exit signals"""
        try:
            # TODO: Implement technical analysis exit signals
            # - RSI overbought/oversold
            # - Moving average crossovers
            # - Support/resistance breaks
            # - Volume patterns
            return False

        except Exception as e:
            logger.error(f"❌ Error checking technical exit: {e}")
            return False

    def _get_exit_urgency(self, exit_reason: str) -> str:
        """Get urgency level for exit signal"""
        urgency_map = {
            "stop_loss": "high",
            "take_profit": "medium",
            "trailing_stop": "medium",
            "max_holding_period": "low",
            "technical_exit": "medium",
        }

        return urgency_map.get(exit_reason, "medium")

    async def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of all positions"""
        try:
            positions = await self.broker_adapter.get_positions()

            if not positions:
                return {"message": "No open positions"}

            summary = {
                "total_positions": len(positions),
                "long_positions": 0,
                "short_positions": 0,
                "total_market_value": 0,
                "total_unrealized_pnl": 0,
                "positions": [],
            }

            for position in positions:
                # Get current price
                current_price = await self.broker_adapter.get_current_price(
                    position.symbol
                )

                # Calculate metrics
                entry_price = float(position.avg_entry_price)
                quantity = float(position.qty)
                market_value = current_price * abs(quantity)

                if position.side == "long":
                    summary["long_positions"] += 1
                    unrealized_pnl = (current_price - entry_price) * quantity
                else:
                    summary["short_positions"] += 1
                    unrealized_pnl = (entry_price - current_price) * quantity

                summary["total_market_value"] += market_value
                summary["total_unrealized_pnl"] += unrealized_pnl

                # Add position details
                summary["positions"].append(
                    {
                        "symbol": position.symbol,
                        "side": position.side,
                        "quantity": quantity,
                        "entry_price": entry_price,
                        "current_price": current_price,
                        "market_value": market_value,
                        "unrealized_pnl": unrealized_pnl,
                        "pnl_percent": unrealized_pnl / (entry_price * abs(quantity))
                        if entry_price > 0
                        else 0,
                    }
                )

            return summary

        except Exception as e:
            logger.error(f"❌ Failed to get position summary: {e}")
            return {"error": str(e)}

    async def get_position_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts for positions requiring attention"""
        alerts = []

        try:
            positions = await self.broker_adapter.get_positions()

            for position in positions:
                current_price = await self.broker_adapter.get_current_price(
                    position.symbol
                )
                entry_price = float(position.avg_entry_price)

                # Calculate P&L percentage
                if position.side == "long":
                    pnl_percent = (current_price - entry_price) / entry_price
                else:
                    pnl_percent = (entry_price - current_price) / entry_price

                # Check for alert conditions
                if pnl_percent <= -0.05:  # 5% loss
                    alerts.append(
                        {
                            "symbol": position.symbol,
                            "alert_type": "large_loss",
                            "pnl_percent": pnl_percent,
                            "message": f"{position.symbol} down {pnl_percent:.1%}",
                        }
                    )

                elif pnl_percent >= 0.15:  # 15% gain
                    alerts.append(
                        {
                            "symbol": position.symbol,
                            "alert_type": "large_gain",
                            "pnl_percent": pnl_percent,
                            "message": f"{position.symbol} up {pnl_percent:.1%}",
                        }
                    )

                # Check for positions near stop loss
                if (
                    abs(pnl_percent + self.exit_conditions.stop_loss_percent) < 0.005
                ):  # Within 0.5% of stop
                    alerts.append(
                        {
                            "symbol": position.symbol,
                            "alert_type": "near_stop_loss",
                            "pnl_percent": pnl_percent,
                            "message": f"{position.symbol} approaching stop loss",
                        }
                    )

        except Exception as e:
            logger.error(f"❌ Error generating position alerts: {e}")

        return alerts
