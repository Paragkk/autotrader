"""
Order Executor - Executes trading orders with retry logic and monitoring
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from brokers.base.broker_adapter import BrokerAdapter
from db.models import Position, Signal

logger = logging.getLogger(__name__)


@dataclass
class OrderConfig:
    """Order execution configuration"""

    max_retries: int = 3
    retry_delay: int = 5  # seconds
    order_timeout: int = 60  # seconds
    default_order_type: str = "market"
    default_time_in_force: str = "day"


class OrderExecutor:
    """
    Handles order execution with retry logic and monitoring
    """

    def __init__(self, broker_adapter: BrokerAdapter, config: OrderConfig | None = None) -> None:
        self.broker_adapter = broker_adapter
        self.config = config or OrderConfig()

    async def execute_signal(self, signal: Signal, position_size: float) -> dict[str, Any]:
        """
        Execute a trading signal as an order

        Args:
            signal: Trading signal to execute
            position_size: Position size in dollars

        Returns:
            Dictionary with order execution results
        """
        logger.info(f"💼 Executing signal: {signal.symbol} {signal.direction}")

        try:
            # Calculate order parameters
            order_params = await self._calculate_order_params(signal, position_size)

            # Execute order with retry logic
            order_result = await self._execute_order_with_retry(order_params)

            logger.info(f"✅ Order executed successfully: {signal.symbol}")
            return order_result

        except Exception as e:
            logger.exception(f"❌ Order execution failed for {signal.symbol}: {e}")
            return {"status": "failed", "error": str(e), "symbol": signal.symbol}

    async def _calculate_order_params(self, signal: Signal, position_size: float) -> dict[str, Any]:
        """Calculate order parameters"""

        # Get current price
        current_price = await self.broker_adapter.get_current_price(signal.symbol)

        # Calculate quantity
        quantity = position_size / current_price

        # Round to appropriate precision
        quantity = round(quantity, 2)

        # Determine order type and price
        order_type = self.config.default_order_type
        price = None

        if order_type == "limit":
            # Add small buffer for limit orders
            price_buffer = 0.01 if signal.direction == "buy" else -0.01
            price = current_price + price_buffer

        return {
            "symbol": signal.symbol,
            "side": signal.direction,
            "quantity": quantity,
            "order_type": order_type,
            "price": price,
            "time_in_force": self.config.default_time_in_force,
        }

    async def _execute_order_with_retry(self, order_params: dict[str, Any]) -> dict[str, Any]:
        """Execute order with retry logic"""

        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"🔄 Order attempt {attempt + 1}/{self.config.max_retries}")

                # Submit order
                order_id = await self.broker_adapter.submit_order(**order_params)

                # Monitor order status
                order_status = await self._monitor_order_status(order_id)

                return {
                    "order_id": order_id,
                    "status": order_status["status"],
                    "quantity": order_params["quantity"],
                    "order_type": order_params["order_type"],
                    "price": order_params.get("price"),
                    "filled_quantity": order_status.get("filled_quantity", 0),
                    "filled_price": order_status.get("filled_price"),
                }

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Order attempt {attempt + 1} failed: {e}")

                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)

        # All retries failed
        raise last_error

    async def _monitor_order_status(self, order_id: str) -> dict[str, Any]:
        """Monitor order status until filled or timeout"""

        start_time = datetime.now()
        timeout = timedelta(seconds=self.config.order_timeout)

        while datetime.now() - start_time < timeout:
            try:
                order_status = await self.broker_adapter.get_order_status(order_id)

                if order_status["status"] in ["filled", "cancelled", "rejected"]:
                    return order_status

                # Wait before checking again
                await asyncio.sleep(2)

            except Exception as e:
                logger.exception(f"❌ Error checking order status: {e}")
                break

        # Timeout reached
        logger.warning(f"⏰ Order monitoring timeout for {order_id}")
        return {"status": "timeout", "order_id": order_id}

    async def exit_position(self, position: Position) -> dict[str, Any]:
        """Exit an existing position"""
        logger.info(f"🚪 Exiting position: {position.symbol}")

        try:
            # Determine exit order parameters
            exit_side = "sell" if position.side == "long" else "buy"

            order_params = {
                "symbol": position.symbol,
                "side": exit_side,
                "quantity": abs(position.quantity),
                "order_type": "market",
                "time_in_force": "day",
            }

            # Execute exit order
            order_result = await self._execute_order_with_retry(order_params)

            logger.info(f"✅ Position exit executed: {position.symbol}")
            return order_result

        except Exception as e:
            logger.exception(f"❌ Position exit failed for {position.symbol}: {e}")
            return {"status": "failed", "error": str(e), "symbol": position.symbol}

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        logger.info(f"❌ Cancelling order: {order_id}")

        try:
            await self.broker_adapter.cancel_order(order_id)
            logger.info(f"✅ Order cancelled: {order_id}")
            return True

        except Exception as e:
            logger.exception(f"❌ Order cancellation failed: {e}")
            return False

    async def get_order_history(self, days: int = 7) -> list[dict[str, Any]]:
        """Get recent order history"""
        try:
            orders = await self.broker_adapter.get_order_history(days)
            return [
                {
                    "order_id": order.id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": order.quantity,
                    "status": order.status,
                    "created_at": order.created_at,
                    "filled_at": order.filled_at,
                }
                for order in orders
            ]

        except Exception as e:
            logger.exception(f"❌ Failed to get order history: {e}")
            return []

    async def get_execution_metrics(self) -> dict[str, Any]:
        """Get order execution performance metrics"""
        try:
            # Get recent orders
            orders = await self.get_order_history(days=30)

            if not orders:
                return {"message": "No orders found"}

            # Calculate metrics
            total_orders = len(orders)
            filled_orders = len([o for o in orders if o["status"] == "filled"])
            cancelled_orders = len([o for o in orders if o["status"] == "cancelled"])

            fill_rate = filled_orders / total_orders if total_orders > 0 else 0

            # Calculate average execution time
            execution_times = []
            for order in orders:
                if order["filled_at"] and order["created_at"]:
                    exec_time = (order["filled_at"] - order["created_at"]).total_seconds()
                    execution_times.append(exec_time)

            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

            return {
                "total_orders": total_orders,
                "filled_orders": filled_orders,
                "cancelled_orders": cancelled_orders,
                "fill_rate": fill_rate,
                "avg_execution_time_seconds": avg_execution_time,
            }

        except Exception as e:
            logger.exception(f"❌ Failed to calculate execution metrics: {e}")
            return {"error": str(e)}

    async def validate_order(self, order_params: dict[str, Any]) -> dict[str, Any]:
        """Validate order parameters before execution"""

        validation_results = {"valid": True, "errors": [], "warnings": []}

        # Check required parameters
        required_params = ["symbol", "side", "quantity"]
        for param in required_params:
            if param not in order_params:
                validation_results["errors"].append(f"Missing required parameter: {param}")
                validation_results["valid"] = False

        # Validate quantity
        if order_params.get("quantity", 0) <= 0:
            validation_results["errors"].append("Quantity must be positive")
            validation_results["valid"] = False

        # Validate side
        if order_params.get("side") not in ["buy", "sell"]:
            validation_results["errors"].append("Side must be 'buy' or 'sell'")
            validation_results["valid"] = False

        # Check market hours
        try:
            market_open = await self.broker_adapter.is_market_open()
            if not market_open:
                validation_results["warnings"].append("Market is currently closed")
        except Exception as e:
            validation_results["warnings"].append(f"Could not check market hours: {e}")

        return validation_results
