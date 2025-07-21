from datetime import datetime


class TradeExecutor:
    """
    Handles the execution of trades through the broker interface.
    """

    def __init__(self, broker_adapter) -> None:
        self.broker = broker_adapter
        self.order_history: dict[str, dict] = {}

    def place_order(self, order_params: dict) -> dict:
        """
        Place a new order through the broker.

        Args:
            order_params: Dictionary containing order parameters:
                - symbol: Trading symbol
                - side: 'buy' or 'sell'
                - order_type: 'market', 'limit', 'stop', 'stop_limit'
                - quantity: Order quantity
                - price: Price for limit orders
                - stop_price: Price for stop orders

        Returns:
            Dictionary containing order details and status
        """
        order_id = f"{order_params['symbol']}_{datetime.now().timestamp()}"

        try:
            response = self.broker.place_order(
                symbol=order_params["symbol"],
                side=order_params["side"],
                order_type=order_params["order_type"],
                quantity=order_params["quantity"],
                price=order_params.get("price"),
                stop_price=order_params.get("stop_price"),
            )

            # Store order details
            self.order_history[order_id] = {
                "params": order_params,
                "response": response,
                "status": "placed",
                "timestamp": datetime.now(),
            }

            return {"order_id": order_id, "status": "placed", "details": response}

        except Exception as e:
            self.order_history[order_id] = {
                "params": order_params,
                "error": str(e),
                "status": "failed",
                "timestamp": datetime.now(),
            }

            return {"order_id": order_id, "status": "failed", "error": str(e)}

    def cancel_order(self, order_id: str) -> dict:
        """Cancel an existing order."""
        if order_id not in self.order_history:
            return {"status": "error", "message": "Order not found"}

        order = self.order_history[order_id]
        if order["status"] != "placed":
            return {
                "status": "error",
                "message": f"Cannot cancel order in {order['status']} status",
            }

        try:
            response = self.broker.cancel_order(order_id)
            order["status"] = "cancelled"
            order["cancel_time"] = datetime.now()
            return {"status": "success", "details": response}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_order_status(self, order_id: str) -> dict | None:
        """Get the current status of an order."""
        if order_id not in self.order_history:
            return None

        order = self.order_history[order_id]

        # If order is still active, fetch latest status from broker
        if order["status"] == "placed":
            try:
                current_status = self.broker.get_order_status(order_id)
                order["status"] = current_status["status"]
                order["last_update"] = datetime.now()
                return current_status
            except Exception:
                return order

        return order

    def get_all_orders(self, symbol: str | None = None, status: str | None = None) -> dict[str, dict]:
        """Get all orders, optionally filtered by symbol and/or status."""
        filtered_orders = {}

        for order_id, order in self.order_history.items():
            if symbol and order["params"]["symbol"] != symbol:
                continue
            if status and order["status"] != status:
                continue
            filtered_orders[order_id] = order

        return filtered_orders
