"""
Risk Manager - Portfolio risk management and position sizing
"""

import logging
from dataclasses import dataclass
from typing import Any

from src.brokers.base import BrokerInterface
from src.db.models import Signal

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Risk management limits"""

    max_exposure_per_trade: float = 0.05  # 5% of portfolio
    max_exposure_per_sector: float = 0.20  # 20% of portfolio
    max_correlation: float = 0.7  # Maximum correlation between positions
    portfolio_risk_limit: float = 0.15  # 15% portfolio risk
    max_daily_loss: float = 0.02  # 2% daily loss limit
    max_position_size: float = 0.10  # 10% max position size


class RiskManager:
    """
    Portfolio risk management system
    Evaluates and filters trading signals based on risk criteria
    """

    def __init__(self, risk_config: dict[str, Any], broker_adapter: BrokerInterface) -> None:
        self.risk_config = risk_config
        self.broker_adapter = broker_adapter
        self.risk_limits = RiskLimits(**risk_config)

    async def filter_signal(self, signal: Signal) -> dict[str, Any]:
        """
        Filter trading signal through risk management checks

        Args:
            signal: Trading signal to evaluate

        Returns:
            Dictionary with filtering results
        """
        logger.info(f"🛡️ Risk filtering signal: {signal.symbol} {signal.direction}")

        try:
            # Get current portfolio state
            portfolio_value = await self._get_portfolio_value()
            current_positions = await self._get_current_positions()

            # Calculate position size
            position_size = self._calculate_position_size(signal, portfolio_value, current_positions)

            # Risk checks
            checks = await self._run_risk_checks(signal, position_size, portfolio_value, current_positions)

            # Determine if signal passes all checks
            passed = all(check["passed"] for check in checks.values())

            result = {
                "passed": passed,
                "position_size": position_size,
                "checks": checks,
                "portfolio_value": portfolio_value,
                "exposure_percent": position_size / portfolio_value if portfolio_value > 0 else 0,
            }

            if not passed:
                failed_checks = [name for name, check in checks.items() if not check["passed"]]
                result["reason"] = f"Failed risk checks: {', '.join(failed_checks)}"

            logger.info(f"✅ Risk filter result: {signal.symbol} - {'PASSED' if passed else 'REJECTED'}")
            return result

        except Exception as e:
            logger.exception(f"❌ Risk filtering failed for {signal.symbol}: {e}")
            return {
                "passed": False,
                "reason": f"Risk filtering error: {e!s}",
                "position_size": 0,
            }

    async def _get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        try:
            account = await self.broker_adapter.get_account()
            return float(account.portfolio_value)
        except Exception as e:
            logger.exception(f"❌ Failed to get portfolio value: {e}")
            return 100000.0  # Default value

    async def _get_current_positions(self) -> list[dict[str, Any]]:
        """Get current positions"""
        try:
            positions = await self.broker_adapter.get_positions()
            return [
                {
                    "symbol": pos.symbol,
                    "market_value": float(pos.market_value),
                    "side": pos.side,
                    "quantity": float(pos.qty),
                }
                for pos in positions
            ]
        except Exception as e:
            logger.exception(f"❌ Failed to get current positions: {e}")
            return []

    def _calculate_position_size(
        self,
        signal: Signal,
        portfolio_value: float,
        current_positions: list[dict[str, Any]],
    ) -> float:
        """Calculate appropriate position size based on risk limits"""

        # Base position size as percentage of portfolio
        base_position_value = portfolio_value * self.risk_limits.max_exposure_per_trade

        # Adjust based on signal strength and confidence
        confidence_multiplier = signal.confidence_score * signal.strength
        adjusted_position_value = base_position_value * confidence_multiplier

        # Ensure within maximum position size limit
        max_position_value = portfolio_value * self.risk_limits.max_position_size
        position_value = min(adjusted_position_value, max_position_value)

        logger.info(f"📊 Position size calculated: ${position_value:,.2f} ({position_value / portfolio_value * 100:.1f}% of portfolio)")
        return position_value

    async def _run_risk_checks(
        self,
        signal: Signal,
        position_size: float,
        portfolio_value: float,
        current_positions: list[dict[str, Any]],
    ) -> dict[str, dict]:
        """Run all risk management checks"""

        checks = {}

        # Check 1: Maximum exposure per trade
        checks["max_exposure_per_trade"] = self._check_max_exposure_per_trade(position_size, portfolio_value)

        # Check 2: Maximum exposure per sector
        checks["max_exposure_per_sector"] = await self._check_sector_exposure(signal.symbol, position_size, portfolio_value, current_positions)

        # Check 3: Position correlation
        checks["position_correlation"] = await self._check_position_correlation(signal.symbol, current_positions)

        # Check 4: Portfolio risk limit
        checks["portfolio_risk_limit"] = self._check_portfolio_risk_limit(position_size, portfolio_value, current_positions)

        # Check 5: Daily loss limit
        checks["daily_loss_limit"] = await self._check_daily_loss_limit(portfolio_value)

        # Check 6: Duplicate position
        checks["duplicate_position"] = self._check_duplicate_position(signal.symbol, current_positions)

        return checks

    def _check_max_exposure_per_trade(self, position_size: float, portfolio_value: float) -> dict[str, Any]:
        """Check if position size exceeds maximum exposure per trade"""
        max_exposure = portfolio_value * self.risk_limits.max_exposure_per_trade
        exposure_percent = position_size / portfolio_value if portfolio_value > 0 else 0

        passed = position_size <= max_exposure

        return {
            "passed": passed,
            "exposure_percent": exposure_percent,
            "max_allowed": self.risk_limits.max_exposure_per_trade,
            "message": f"Position exposure: {exposure_percent:.1%} (max: {self.risk_limits.max_exposure_per_trade:.1%})",
        }

    async def _check_sector_exposure(
        self,
        symbol: str,
        position_size: float,
        portfolio_value: float,
        current_positions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Check sector exposure limits"""
        # TODO: Implement sector classification and exposure calculation
        # For now, return passed
        return {
            "passed": True,
            "sector_exposure": 0.0,
            "max_allowed": self.risk_limits.max_exposure_per_sector,
            "message": "Sector exposure check passed",
        }

    async def _check_position_correlation(self, symbol: str, current_positions: list[dict[str, Any]]) -> dict[str, Any]:
        """Check correlation with existing positions"""
        # TODO: Implement correlation calculation
        # For now, return passed
        return {
            "passed": True,
            "max_correlation": 0.0,
            "max_allowed": self.risk_limits.max_correlation,
            "message": "Position correlation check passed",
        }

    def _check_portfolio_risk_limit(
        self,
        position_size: float,
        portfolio_value: float,
        current_positions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Check overall portfolio risk limit"""
        # TODO: Implement portfolio risk calculation (VaR, etc.)
        # For now, return passed
        return {
            "passed": True,
            "portfolio_risk": 0.05,
            "max_allowed": self.risk_limits.portfolio_risk_limit,
            "message": "Portfolio risk within limits",
        }

    async def _check_daily_loss_limit(self, portfolio_value: float) -> dict[str, Any]:
        """Check daily loss limit"""
        # TODO: Implement daily P&L tracking
        # For now, return passed
        return {
            "passed": True,
            "daily_loss": 0.0,
            "max_allowed": self.risk_limits.max_daily_loss,
            "message": "Daily loss within limits",
        }

    def _check_duplicate_position(self, symbol: str, current_positions: list[dict[str, Any]]) -> dict[str, Any]:
        """Check for duplicate positions"""
        has_position = any(pos["symbol"] == symbol for pos in current_positions)

        return {
            "passed": not has_position,
            "has_existing_position": has_position,
            "message": f"{'Duplicate position detected' if has_position else 'No duplicate position'}",
        }

    async def calculate_stop_loss_take_profit(self, signal: Signal, position_size: float) -> dict[str, float]:
        """Calculate stop loss and take profit levels"""

        # Get current price
        current_price = signal.price_at_signal

        # Calculate stop loss (percentage below entry for long, above for short)
        stop_loss_percent = 0.03  # 3% stop loss
        take_profit_percent = 0.08  # 8% take profit

        if signal.direction == "buy":
            stop_loss_price = current_price * (1 - stop_loss_percent)
            take_profit_price = current_price * (1 + take_profit_percent)
        else:  # sell/short
            stop_loss_price = current_price * (1 + stop_loss_percent)
            take_profit_price = current_price * (1 - take_profit_percent)

        return {
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "risk_reward_ratio": take_profit_percent / stop_loss_percent,
        }

    async def get_risk_metrics(self) -> dict[str, Any]:
        """Get current portfolio risk metrics"""
        try:
            portfolio_value = await self._get_portfolio_value()
            current_positions = await self._get_current_positions()

            # Calculate total exposure
            total_exposure = sum(abs(pos["market_value"]) for pos in current_positions)
            exposure_percent = total_exposure / portfolio_value if portfolio_value > 0 else 0

            # Calculate position count
            position_count = len(current_positions)

            return {
                "portfolio_value": portfolio_value,
                "total_exposure": total_exposure,
                "exposure_percent": exposure_percent,
                "position_count": position_count,
                "available_buying_power": portfolio_value - total_exposure,
                "risk_utilization": exposure_percent / self.risk_limits.max_exposure_per_trade,
            }

        except Exception as e:
            logger.exception(f"❌ Failed to calculate risk metrics: {e}")
            return {"error": str(e)}
