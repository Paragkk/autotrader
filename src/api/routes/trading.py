"""
Trading API Routes
Comprehensive trading operations through REST API
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.broker_manager import get_broker_manager
from brokers.base import OrderRequest, OrderSide, OrderType, TimeInForce

router = APIRouter(prefix="/api/trading", tags=["trading"])


# Request/Response Models
class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)")
    side: str = Field(..., description="Order side: buy or sell")
    quantity: float = Field(..., gt=0, description="Number of shares")
    order_type: str = Field(
        default="market", description="Order type: market, limit, stop, stop_limit"
    )
    price: Optional[float] = Field(
        None, description="Limit price (required for limit orders)"
    )
    stop_price: Optional[float] = Field(
        None, description="Stop price (required for stop orders)"
    )
    time_in_force: str = Field(
        default="day", description="Time in force: day, gtc, ioc, fok"
    )
    extended_hours: bool = Field(
        default=False, description="Allow extended hours trading"
    )

    class Config:
        schema_extra = {
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
    price: Optional[float] = None
    executed_price: Optional[float] = None
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
        raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")


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
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Order {order_id} not found or cannot be canceled",
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}")


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(status: Optional[str] = None, limit: int = 100):
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
        raise HTTPException(status_code=500, detail=f"Failed to get orders: {str(e)}")


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
        raise HTTPException(
            status_code=500, detail=f"Failed to get order status: {str(e)}"
        )


@router.get("/positions", response_model=List[PositionResponse])
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
                average_entry_price=pos.average_entry_price,
                unrealized_pl=pos.unrealized_pl,
                unrealized_plpc=pos.unrealized_plpc,
                current_price=pos.current_price,
            )
            for pos in positions
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get positions: {str(e)}"
        )


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
            raise HTTPException(
                status_code=404, detail=f"No position found for {symbol}"
            )

        return PositionResponse(
            symbol=position.symbol,
            quantity=position.quantity,
            side=position.side,
            market_value=position.market_value,
            cost_basis=position.cost_basis,
            average_entry_price=position.average_entry_price,
            unrealized_pl=position.unrealized_pl,
            unrealized_plpc=position.unrealized_plpc,
            current_price=position.current_price,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get position: {str(e)}")


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
            raise HTTPException(
                status_code=404, detail=f"No position found for {symbol}"
            )

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
        raise HTTPException(
            status_code=500, detail=f"Failed to close position: {str(e)}"
        )


@router.get("/account", response_model=AccountResponse)
async def get_account_info():
    """
    Get account information

    Retrieve account details including cash, portfolio value, and trading permissions.
    """
    try:
        broker_manager = get_broker_manager()

        if not broker_manager.active_broker:
            raise HTTPException(status_code=400, detail="No active broker connected")

        account = await broker_manager.get_account_info()

        return AccountResponse(
            account_id=account.account_id,
            cash=account.cash,
            portfolio_value=account.portfolio_value,
            buying_power=account.buying_power,
            day_trade_count=account.day_trade_count,
            pattern_day_trader=account.pattern_day_trader,
            account_status=account.account_status,
            currency=account.currency,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get account info: {str(e)}"
        )


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
        raise HTTPException(status_code=500, detail=f"Failed to get quote: {str(e)}")


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
        raise HTTPException(
            status_code=500, detail=f"Failed to get market status: {str(e)}"
        )
