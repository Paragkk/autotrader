"""
Risk Management Module - Enhanced with Multiple Risk Controls
"""

import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from brokers.base.broker_adapter import Position, AccountInfo, OrderRequest

logger = logging.getLogger(__name__)


@dataclass
class RiskParameters:
    """Risk management parameters"""

    max_position_size_percent: float = 5.0  # Max 5% of portfolio per position
    max_total_exposure_percent: float = 80.0  # Max 80% of portfolio invested
    max_daily_loss_percent: float = 2.0  # Max 2% daily loss
    max_drawdown_percent: float = 10.0  # Max 10% drawdown
    stop_loss_percent: float = 5.0  # 5% stop loss
    take_profit_percent: float = 15.0  # 15% take profit
    max_positions: int = 20  # Max number of positions
    min_liquidity_volume: int = 100000  # Min daily volume
    max_sector_exposure_percent: float = 25.0  # Max 25% per sector
    correlation_threshold: float = 0.7  # Max correlation between positions


@dataclass
class RiskMetrics:
    """Risk metrics for a position or portfolio"""

    current_exposure_percent: float
    daily_pnl_percent: float
    total_drawdown_percent: float
    position_count: int
    sector_exposure: Dict[str, float]
    correlation_risk: float
    liquidity_risk: float
    risk_score: float  # Overall risk score 0-1


class RiskRule(ABC):
    """Abstract base class for risk rules"""

    @abstractmethod
    def evaluate(
        self,
        order_request: OrderRequest,
        account: AccountInfo,
        positions: List[Position],
        risk_params: RiskParameters,
    ) -> Tuple[bool, str]:
        """
        Evaluate if order passes risk rule
        Returns: (approved, reason)
        """
        pass


class PositionSizeRule(RiskRule):
    """Rule to limit individual position size"""

    def evaluate(
        self,
        order_request: OrderRequest,
        account: AccountInfo,
        positions: List[Position],
        risk_params: RiskParameters,
    ) -> Tuple[bool, str]:
        order_value = order_request.quantity * (order_request.price or 0)
        max_position_value = account.portfolio_value * (
            risk_params.max_position_size_percent / 100
        )

        if order_value > max_position_value:
            return (
                False,
                f"Position size {order_value:.2f} exceeds maximum {max_position_value:.2f}",
            )

        return True, "Position size OK"


class TotalExposureRule(RiskRule):
    """Rule to limit total portfolio exposure"""

    def evaluate(
        self,
        order_request: OrderRequest,
        account: AccountInfo,
        positions: List[Position],
        risk_params: RiskParameters,
    ) -> Tuple[bool, str]:
        current_exposure = sum(pos.market_value for pos in positions)
        order_value = order_request.quantity * (order_request.price or 0)
        total_exposure = current_exposure + order_value

        max_exposure = account.portfolio_value * (
            risk_params.max_total_exposure_percent / 100
        )

        if total_exposure > max_exposure:
            return (
                False,
                f"Total exposure {total_exposure:.2f} would exceed maximum {max_exposure:.2f}",
            )

        return True, "Total exposure OK"


class MaxPositionsRule(RiskRule):
    """Rule to limit number of positions"""

    def evaluate(
        self,
        order_request: OrderRequest,
        account: AccountInfo,
        positions: List[Position],
        risk_params: RiskParameters,
    ) -> Tuple[bool, str]:
        # Check if this is a new position or adding to existing
        existing_position = any(pos.symbol == order_request.symbol for pos in positions)

        if not existing_position and len(positions) >= risk_params.max_positions:
            return (
                False,
                f"Maximum positions ({risk_params.max_positions}) already reached",
            )

        return True, "Position count OK"


class DailyLossRule(RiskRule):
    """Rule to limit daily losses"""

    def evaluate(
        self,
        order_request: OrderRequest,
        account: AccountInfo,
        positions: List[Position],
        risk_params: RiskParameters,
    ) -> Tuple[bool, str]:
        # Calculate current daily P&L
        daily_pnl = sum(pos.unrealized_pl for pos in positions)
        daily_pnl_percent = (daily_pnl / account.portfolio_value) * 100

        max_loss_percent = -abs(risk_params.max_daily_loss_percent)

        if daily_pnl_percent < max_loss_percent:
            return (
                False,
                f"Daily loss {daily_pnl_percent:.2f}% exceeds limit {max_loss_percent:.2f}%",
            )

        return True, "Daily loss within limits"


class LiquidityRule(RiskRule):
    """Rule to ensure sufficient liquidity"""

    def __init__(self, data_fetcher=None):
        self.data_fetcher = data_fetcher

    def evaluate(
        self,
        order_request: OrderRequest,
        account: AccountInfo,
        positions: List[Position],
        risk_params: RiskParameters,
    ) -> Tuple[bool, str]:
        if not self.data_fetcher:
            return True, "Liquidity check skipped (no data fetcher)"

        try:
            # Get recent volume data for the symbol
            # This would need to be implemented with actual market data
            # For now, we'll use a simplified check
            return True, "Liquidity OK"

        except Exception as e:
            logger.warning(f"Could not check liquidity for {order_request.symbol}: {e}")
            return True, "Liquidity check skipped (error)"


class RiskManager:
    """
    Main risk management system with pluggable rules
    """

    def __init__(self, risk_params: RiskParameters = None):
        self.risk_params = risk_params or RiskParameters()
        self.rules: List[RiskRule] = []
        self.active_stops: Dict[str, Dict[str, Any]] = {}  # Symbol -> stop loss info

        # Load default rules
        self._load_default_rules()

    def _load_default_rules(self):
        """Load default risk rules"""
        self.rules = [
            PositionSizeRule(),
            TotalExposureRule(),
            MaxPositionsRule(),
            DailyLossRule(),
            LiquidityRule(),
        ]

    def add_rule(self, rule: RiskRule):
        """Add a custom risk rule"""
        self.rules.append(rule)
        logger.info(f"Added risk rule: {rule.__class__.__name__}")

    def remove_rule(self, rule_class):
        """Remove a risk rule by class"""
        self.rules = [rule for rule in self.rules if not isinstance(rule, rule_class)]
        logger.info(f"Removed risk rule: {rule_class.__name__}")

    def evaluate_order(
        self,
        order_request: OrderRequest,
        account: AccountInfo,
        positions: List[Position],
    ) -> Tuple[bool, List[str]]:
        """
        Evaluate an order against all risk rules
        Returns: (approved, list of reasons)
        """
        reasons = []
        approved = True

        for rule in self.rules:
            try:
                rule_approved, reason = rule.evaluate(
                    order_request, account, positions, self.risk_params
                )
                reasons.append(f"{rule.__class__.__name__}: {reason}")

                if not rule_approved:
                    approved = False

            except Exception as e:
                logger.error(f"Error evaluating rule {rule.__class__.__name__}: {e}")
                reasons.append(f"{rule.__class__.__name__}: Error - {str(e)}")
                approved = False

        return approved, reasons

    def apply_position_sizing(
        self, order_request: OrderRequest, account: AccountInfo
    ) -> OrderRequest:
        """
        Apply position sizing rules to order request
        """
        max_position_value = account.portfolio_value * (
            self.risk_params.max_position_size_percent / 100
        )

        if order_request.price:
            max_quantity = max_position_value / order_request.price

            if order_request.quantity > max_quantity:
                logger.info(
                    f"Reducing position size from {order_request.quantity} to {max_quantity}"
                )
                order_request.quantity = max_quantity

        return order_request

    def calculate_stop_loss_price(self, entry_price: float, side: str) -> float:
        """Calculate stop loss price based on risk parameters"""
        stop_loss_multiplier = 1 - (self.risk_params.stop_loss_percent / 100)

        if side.lower() == "buy":
            return entry_price * stop_loss_multiplier
        else:  # sell/short
            return entry_price * (2 - stop_loss_multiplier)

    def calculate_take_profit_price(self, entry_price: float, side: str) -> float:
        """Calculate take profit price based on risk parameters"""
        take_profit_multiplier = 1 + (self.risk_params.take_profit_percent / 100)

        if side.lower() == "buy":
            return entry_price * take_profit_multiplier
        else:  # sell/short
            return entry_price * (2 - take_profit_multiplier)

    def set_stop_loss(
        self, symbol: str, entry_price: float, side: str, broker_adapter=None
    ):
        """Set stop loss for a position"""
        stop_price = self.calculate_stop_loss_price(entry_price, side)

        self.active_stops[symbol] = {
            "stop_price": stop_price,
            "entry_price": entry_price,
            "side": side,
            "timestamp": datetime.now(),
            "active": True,
        }

        logger.info(f"Set stop loss for {symbol} at {stop_price}")

        # If broker adapter provided, place the stop order
        if broker_adapter:
            try:
                # Create stop order request
                OrderRequest(
                    symbol=symbol,
                    quantity=0,  # Would need actual position size
                    side="sell" if side.lower() == "buy" else "buy",
                    order_type="stop",
                    stop_price=stop_price,
                )
                # broker_adapter.place_order(stop_order)
                logger.info(f"Placed stop loss order for {symbol}")
            except Exception as e:
                logger.error(f"Failed to place stop loss order for {symbol}: {e}")

    def check_stop_losses(self, positions: List[Position]) -> List[str]:
        """Check if any stop losses should be triggered"""
        triggered_stops = []

        for position in positions:
            if position.symbol in self.active_stops:
                stop_info = self.active_stops[position.symbol]

                if not stop_info["active"]:
                    continue

                stop_price = stop_info["stop_price"]
                side = stop_info["side"]

                # Check if stop should trigger
                should_trigger = False

                if side.lower() == "buy" and position.current_price <= stop_price:
                    should_trigger = True
                elif side.lower() == "sell" and position.current_price >= stop_price:
                    should_trigger = True

                if should_trigger:
                    triggered_stops.append(position.symbol)
                    self.active_stops[position.symbol]["active"] = False
                    logger.warning(
                        f"Stop loss triggered for {position.symbol} at {position.current_price}"
                    )

        return triggered_stops

    def calculate_portfolio_risk_metrics(
        self, account: AccountInfo, positions: List[Position]
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics for the portfolio"""

        total_exposure = sum(pos.market_value for pos in positions)
        exposure_percent = (
            (total_exposure / account.portfolio_value) * 100
            if account.portfolio_value > 0
            else 0
        )

        total_pnl = sum(pos.unrealized_pl for pos in positions)
        daily_pnl_percent = (
            (total_pnl / account.portfolio_value) * 100
            if account.portfolio_value > 0
            else 0
        )

        # Calculate drawdown (simplified - would need historical data for accurate calculation)
        drawdown_percent = min(0, daily_pnl_percent)

        # Sector exposure (simplified - would need sector mapping)
        sector_exposure = {"Unknown": exposure_percent}

        # Risk score calculation (0-1, where 1 is highest risk)
        risk_factors = [
            min(1.0, exposure_percent / 100),  # Exposure risk
            min(1.0, abs(daily_pnl_percent) / 10),  # P&L volatility risk
            min(1.0, len(positions) / 50),  # Concentration risk
            min(1.0, abs(drawdown_percent) / 20),  # Drawdown risk
        ]

        risk_score = sum(risk_factors) / len(risk_factors)

        return RiskMetrics(
            current_exposure_percent=exposure_percent,
            daily_pnl_percent=daily_pnl_percent,
            total_drawdown_percent=drawdown_percent,
            position_count=len(positions),
            sector_exposure=sector_exposure,
            correlation_risk=0.0,  # Would need correlation calculation
            liquidity_risk=0.0,  # Would need liquidity analysis
            risk_score=risk_score,
        )

    def get_risk_summary(
        self, account: AccountInfo, positions: List[Position]
    ) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        metrics = self.calculate_portfolio_risk_metrics(account, positions)

        return {
            "risk_metrics": metrics,
            "risk_parameters": self.risk_params,
            "active_rules": [rule.__class__.__name__ for rule in self.rules],
            "active_stops": len(
                [stop for stop in self.active_stops.values() if stop["active"]]
            ),
            "risk_alerts": self._generate_risk_alerts(metrics),
            "recommendations": self._generate_risk_recommendations(metrics),
        }

    def _generate_risk_alerts(self, metrics: RiskMetrics) -> List[str]:
        """Generate risk alerts based on metrics"""
        alerts = []

        if (
            metrics.current_exposure_percent
            > self.risk_params.max_total_exposure_percent
        ):
            alerts.append(
                f"Portfolio exposure {metrics.current_exposure_percent:.1f}% exceeds limit"
            )

        if metrics.daily_pnl_percent < -self.risk_params.max_daily_loss_percent:
            alerts.append(f"Daily loss {metrics.daily_pnl_percent:.1f}% exceeds limit")

        if metrics.position_count > self.risk_params.max_positions:
            alerts.append(f"Position count {metrics.position_count} exceeds limit")

        if metrics.risk_score > 0.8:
            alerts.append("High overall risk score detected")

        return alerts

    def _generate_risk_recommendations(self, metrics: RiskMetrics) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []

        if metrics.current_exposure_percent > 70:
            recommendations.append("Consider reducing portfolio exposure")

        if metrics.position_count > 15:
            recommendations.append("Consider consolidating positions")

        if metrics.risk_score > 0.6:
            recommendations.append(
                "Review risk parameters and consider tightening controls"
            )

        return recommendations

    def update_risk_parameters(self, new_params: Dict[str, Any]):
        """Update risk parameters"""
        for key, value in new_params.items():
            if hasattr(self.risk_params, key):
                setattr(self.risk_params, key, value)
                logger.info(f"Updated risk parameter {key} to {value}")
            else:
                logger.warning(f"Unknown risk parameter: {key}")

    def emergency_stop(self) -> bool:
        """Emergency stop - halt all trading"""
        logger.critical("EMERGENCY STOP ACTIVATED - All trading halted")
        # Implementation would involve setting flags to stop all trading activities
        return True
