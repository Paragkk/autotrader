"""
Trading API Routes
Comprehensive trading operations through REST API
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from brokers.base import OrderRequest, OrderSide, OrderType, TimeInForce
from core.broker_manager import get_broker_manager

router = APIRouter(prefix="/trading", tags=["trading"])


# Request/Response Models
class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)")
    side: str = Field(..., description="Order side: buy or sell")
    quantity: float = Field(..., gt=0, description="Number of shares")
    order_type: str = Field(default="market", description="Order type: market, limit, stop, stop_limit")
    price: float | None = Field(None, description="Limit price (required for limit orders)")
    stop_price: float | None = Field(None, description="Stop price (required for stop orders)")
    time_in_force: str = Field(default="day", description="Time in force: day, gtc, ioc, fok")
    extended_hours: bool = Field(default=False, description="Allow extended hours trading")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "side": "buy",
                "quantity": 10,
                "order_type": "market",
                "time_in_force": "day",
            }
        }


class OrderResponse(BaseModel):
    order_id: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    status: str
    price: float | None = None
    executed_price: float | None = None
    executed_quantity: float = 0
    created_at: datetime
    updated_at: datetime


class PositionResponse(BaseModel):
    symbol: str
    quantity: float
    side: str
    market_value: float
    cost_basis: float
    average_entry_price: float
    unrealized_pl: float
    unrealized_plpc: float
    current_price: float


class AccountResponse(BaseModel):
    account_id: str
    cash: float
    portfolio_value: float
    buying_power: float
    day_trade_count: int
    pattern_day_trader: bool
    account_status: str
    currency: str


class QuoteResponse(BaseModel):
    symbol: str
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    timestamp: datetime


@router.post("/orders", response_model=OrderResponse)
async def place_order(order_request: PlaceOrderRequest):
    """
    Place a trading order

    Place buy/sell orders through the active broker. Supports market, limit,
    stop, and stop-limit orders with various time-in-force options.
    """
    try:
        broker_manager = get_broker_manager()

        # Validate broker is connected
        if not broker_manager.active_broker:
            raise HTTPException(status_code=400, detail="No active broker connected")

        # Convert API request to broker order request
        broker_order = OrderRequest(
            symbol=order_request.symbol.upper(),
            side=OrderSide(order_request.side.lower()),
            quantity=order_request.quantity,
            order_type=OrderType(order_request.order_type.lower()),
            price=order_request.price,
            stop_price=order_request.stop_price,
            time_in_force=TimeInForce(order_request.time_in_force.lower()),
            extended_hours=order_request.extended_hours,
        )

        # Place order through broker
        response = await broker_manager.place_order(broker_order)

        return OrderResponse(
            order_id=response.order_id,
            symbol=response.symbol,
            side=response.side.value,
            quantity=response.quantity,
            order_type=response.order_type.value,
            status=response.status.value,
            price=response.price,
            executed_price=response.executed_price,
            executed_quantity=response.executed_quantity,
            created_at=response.created_at,
            updated_at=response.updated_at,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to place order: {e!s}")


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    """
    Cancel an existing order

    Cancel a pending order by its order ID. Only orders that haven't been
    filled can be canceled.
    """
    try:
        broker_manager = get_broker_manager()

        if not broker_manager.active_broker:
            raise HTTPException(status_code=400, detail="No active broker connected")

        success = await broker_manager.cancel_order(order_id)

        if success:
            return {"message": f"Order {order_id} canceled successfully"}
        raise HTTPException(
            status_code=404,
            detail=f"Order {order_id} not found or cannot be canceled",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {e!s}")


@router.get("/orders", response_model=list[OrderResponse])
async def get_orders(status: str | None = None, limit: int = 100):
    """
    Get order history

    Retrieve order history with optional status filter. Returns most recent orders first.
    """
    try:
        broker_manager = get_broker_manager()

        if not broker_manager.active_broker:
            raise HTTPException(status_code=400, detail="No active broker connected")

        # Convert status filter if provided
        status_filter = None
        if status:
            from brokers.base import OrderStatus

            try:
                status_filter = OrderStatus(status.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        orders = await broker_manager.get_orders(status=status_filter, limit=limit)

        return [
            OrderResponse(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side.value,
                quantity=order.quantity,
                order_type=order.order_type.value,
                status=order.status.value,
                price=order.price,
                executed_price=order.executed_price,
                executed_quantity=order.executed_quantity,
                created_at=order.created_at,
                updated_at=order.updated_at,
            )
            for order in orders
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get orders: {e!s}")


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_status(order_id: str):
    """
    Get order status

    Get the current status and details of a specific order.
    """
    try:
        broker_manager = get_broker_manager()

        if not broker_manager.active_broker:
            raise HTTPException(status_code=400, detail="No active broker connected")

        order = await broker_manager.active_broker.get_order_status(order_id)

        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        return OrderResponse(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            order_type=order.order_type.value,
            status=order.status.value,
            price=order.price,
            executed_price=order.executed_price,
            executed_quantity=order.executed_quantity,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order status: {e!s}")


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions():
    """
    Get all positions

    Retrieve all current positions in the account with real-time market values.
    """
    try:
        broker_manager = get_broker_manager()

        if not broker_manager.active_broker:
            raise HTTPException(status_code=400, detail="No active broker connected")

        positions = await broker_manager.get_positions()

        return [
            PositionResponse(
                symbol=pos.symbol,
                quantity=pos.quantity,
                side=pos.side,
                market_value=pos.market_value,
                cost_basis=pos.cost_basis,
                average_entry_price=pos.entry_price,
                unrealized_pl=pos.unrealized_pl,
                unrealized_plpc=pos.unrealized_pl_percent,
                current_price=pos.current_price,
            )
            for pos in positions
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {e!s}")


@router.get("/positions/{symbol}", response_model=PositionResponse)
async def get_position(symbol: str):
    """
    Get position for specific symbol

    Retrieve position details for a specific stock symbol.
    """
    try:
        broker_manager = get_broker_manager()

        if not broker_manager.active_broker:
            raise HTTPException(status_code=400, detail="No active broker connected")

        position = await broker_manager.active_broker.get_position(symbol.upper())

        if not position:
            raise HTTPException(status_code=404, detail=f"No position found for {symbol}")

        return PositionResponse(
            symbol=position.symbol,
            quantity=position.quantity,
            side=position.side,
            market_value=position.market_value,
            cost_basis=position.cost_basis,
            average_entry_price=position.entry_price,
            unrealized_pl=position.unrealized_pl,
            unrealized_plpc=position.unrealized_pl_percent,
            current_price=position.current_price,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get position: {e!s}")


@router.delete("/positions/{symbol}")
async def close_position(symbol: str):
    """
    Close position

    Close all shares of a position by placing a market sell order.
    """
    try:
        broker_manager = get_broker_manager()

        if not broker_manager.active_broker:
            raise HTTPException(status_code=400, detail="No active broker connected")

        # Get current position
        position = await broker_manager.active_broker.get_position(symbol.upper())

        if not position or position.quantity == 0:
            raise HTTPException(status_code=404, detail=f"No position found for {symbol}")

        # Determine order side (opposite of position)
        order_side = OrderSide.SELL if position.quantity > 0 else OrderSide.BUY
        quantity = abs(position.quantity)

        # Create close order
        close_order = OrderRequest(
            symbol=symbol.upper(),
            side=order_side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
        )

        # Place order
        response = await broker_manager.place_order(close_order)

        return {
            "message": f"Position close order placed for {symbol}",
            "order_id": response.order_id,
            "quantity": quantity,
            "side": order_side.value,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close position: {e!s}")


@router.get("/account", response_model=AccountResponse)
async def get_account_info():
    """
    Get account information

    Retrieve account details including cash, portfolio value, and trading permissions.
    """
    try:
        # Simple, direct approach
        from core.broker_manager import get_broker_manager, initialize_default_brokers

        broker_manager = get_broker_manager()

        # Ensure we have an active broker
        if not broker_manager.active_broker:
            success = await initialize_default_brokers()
            if not success or not broker_manager.active_broker:
                raise HTTPException(status_code=503, detail="No broker connection available")

        # Get account info directly
        account_info = await broker_manager.active_broker.get_account_info()

        # Create response with explicit field access and validation
        return AccountResponse(
            account_id=str(account_info.account_id or "unknown"),
            cash=float(account_info.cash or 0.0),
            portfolio_value=float(account_info.portfolio_value or 0.0),
            buying_power=float(account_info.buying_power or 0.0),
            day_trade_count=int(account_info.day_trade_count or 0),
            pattern_day_trader=bool(account_info.pattern_day_trader or False),
            account_status=str(account_info.account_status or "unknown"),
            currency=str(account_info.currency or "USD"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CUSTOM ERROR MESSAGE - Failed to get account info: {e!s}")


@router.get("/account-debug", response_model=AccountResponse)
async def get_account_info_debug():
    """
    DEBUG version of account endpoint with direct broker access
    """
    try:
        from core.broker_manager import get_broker_manager, initialize_default_brokers

        # Force broker initialization
        await initialize_default_brokers()

        broker_manager = get_broker_manager()
        if not broker_manager.active_broker:
            raise HTTPException(status_code=503, detail="No active broker after initialization")

        # Get account info directly from active broker
        account_info = await broker_manager.active_broker.get_account_info()

        # Return with explicit safe defaults
        return AccountResponse(
            account_id=account_info.account_id or "demo_account",
            cash=account_info.cash or 0.0,
            portfolio_value=account_info.portfolio_value or 0.0,
            buying_power=account_info.buying_power or 0.0,
            day_trade_count=account_info.day_trade_count or 0,
            pattern_day_trader=account_info.pattern_day_trader or False,
            account_status=account_info.account_status or "active",
            currency=account_info.currency or "USD",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DEBUG ENDPOINT ERROR: {e!s}")


@router.get("/quotes/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: str):
    """
    Get real-time quote

    Get real-time bid/ask quote for a stock symbol.
    """
    try:
        broker_manager = get_broker_manager()

        if not broker_manager.active_broker:
            raise HTTPException(status_code=400, detail="No active broker connected")

        quote = await broker_manager.get_quote(symbol.upper())

        if not quote:
            raise HTTPException(status_code=404, detail=f"Quote not found for {symbol}")

        return QuoteResponse(
            symbol=quote.symbol,
            bid_price=quote.bid_price,
            ask_price=quote.ask_price,
            bid_size=quote.bid_size,
            ask_size=quote.ask_size,
            timestamp=quote.timestamp,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quote: {e!s}")


@router.get("/market/status")
async def get_market_status():
    """
    Get market status

    Check if the market is currently open for trading.
    """
    try:
        broker_manager = get_broker_manager()

        if not broker_manager.active_broker:
            raise HTTPException(status_code=400, detail="No active broker connected")

        is_open = await broker_manager.is_market_open()

        return {
            "market_open": is_open,
            "timestamp": datetime.now(),
            "broker": broker_manager.get_active_broker_name(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get market status: {e!s}")
