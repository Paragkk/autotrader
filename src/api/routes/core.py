"""
Core API Routes
Main system endpoints for status, portfolio, and account information
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.broker_manager import get_broker_manager

router = APIRouter(tags=["core"])


# Response Models
class SystemStatusResponse(BaseModel):
    system_running: bool
    active_positions: int
    max_positions: int
    pending_signals: int
    portfolio_value: float
    available_cash: float
    market_hours: bool
    last_update: datetime


class PortfolioSummary(BaseModel):
    """Portfolio summary response"""

    account_value: float
    cash: float
    buying_power: float
    positions_count: int
    positions_value: float
    unrealized_pnl: float
    daily_pnl: float | None = None
    day_trade_count: int
    positions: list[dict[str, Any]]
    last_updated: datetime


class PositionDetail(BaseModel):
    """Individual position details"""

    symbol: str
    quantity: float
    side: str
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    cost_basis: float
    portfolio_percentage: float
    day_change: float
    day_change_percent: float
    asset_class: str
    exchange: str


class OrderDetail(BaseModel):
    """Order details response"""

    order_id: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    status: str
    filled_quantity: float
    price: float | None = None
    filled_price: float | None = None
    created_at: datetime
    updated_at: datetime | None = None
    time_in_force: str


class AccountInfo(BaseModel):
    """Account information response"""

    account_id: str
    account_type: str
    buying_power: float
    cash: float
    portfolio_value: float
    equity: float
    day_trading_power: float
    pattern_day_trader: bool
    day_trade_count: int
    account_status: str


# Utility functions
def get_broker_or_none():
    """Get connected broker or return None if not available"""
    try:
        broker_manager = get_broker_manager()
        return broker_manager.get_active_broker()
    except Exception:
        return None


def get_broker_or_raise():
    """Get connected broker or raise HTTPException if not available"""
    broker_manager = get_broker_manager()
    broker = broker_manager.get_active_broker()
    if not broker:
        active_broker_name = broker_manager.get_active_broker_name()
        if active_broker_name:
            raise HTTPException(
                status_code=503,
                detail=f"Broker {active_broker_name} is not properly connected",
            )
        raise HTTPException(status_code=503, detail="No broker is currently connected")
    return broker


# Core API Endpoints
@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get current system status"""
    return SystemStatusResponse(
        system_running=True,
        active_positions=0,
        max_positions=10,
        pending_signals=0,
        portfolio_value=100000.0,
        available_cash=50000.0,
        market_hours=True,
        last_update=datetime.now(),
    )


@router.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio_summary():
    """Get current portfolio summary including all positions from active broker"""
    try:
        broker = get_broker_or_none()
        broker_manager = get_broker_manager()

        if not broker:
            return PortfolioSummary(
                account_value=0.0,
                cash=0.0,
                buying_power=0.0,
                positions_count=0,
                positions_value=0.0,
                unrealized_pnl=0.0,
                day_trade_count=0,
                positions=[],
                last_updated=datetime.now(),
            )

        # Get account info and positions directly from broker manager
        account = await broker_manager.get_account_info()
        positions = await broker_manager.get_positions()

        return PortfolioSummary(
            account_value=float(account.portfolio_value),
            cash=float(account.cash),
            buying_power=float(account.buying_power),
            positions_count=len(positions),
            positions_value=sum(float(p.market_value) for p in positions),
            unrealized_pnl=sum(float(p.unrealized_pl) for p in positions),
            daily_pnl=sum(float(getattr(p, "unrealized_intraday_pl", 0)) for p in positions),
            day_trade_count=getattr(account, "day_trade_count", 0),
            positions=[
                {
                    "symbol": p.symbol,
                    "quantity": float(p.qty),
                    "market_value": float(p.market_value),
                    "unrealized_pnl": float(p.unrealized_pl),
                }
                for p in positions
            ],
            last_updated=datetime.now(),
        )

    except Exception as e:
        return PortfolioSummary(
            account_value=0.0,
            cash=0.0,
            buying_power=0.0,
            positions_count=0,
            positions_value=0.0,
            unrealized_pnl=0.0,
            day_trade_count=0,
            positions=[],
            last_updated=datetime.now(),
        )


@router.get("/positions", response_model=list[PositionDetail])
async def get_current_positions():
    """Get detailed list of all current positions from active broker"""
    try:
        broker = get_broker_or_none()
        if not broker:
            return []

        broker_manager = get_broker_manager()
        # Get positions from broker manager
        positions = await broker_manager.get_positions()

        position_details = []
        for position in positions:
            # Get current price for calculations
            try:
                current_price = await broker_manager.get_current_price(position.symbol)
            except Exception:
                current_price = position.market_value / abs(position.qty) if position.qty != 0 else 0

            position_detail = PositionDetail(
                symbol=position.symbol,
                quantity=float(position.qty),
                side=position.side,
                avg_entry_price=float(position.avg_entry_price),
                current_price=current_price,
                market_value=float(position.market_value),
                unrealized_pnl=float(position.unrealized_pl),
                unrealized_pnl_percent=float(position.unrealized_plpc) * 100,
                cost_basis=float(position.cost_basis),
                portfolio_percentage=float(getattr(position, "portfolio_pct", 0)) * 100,
                day_change=float(getattr(position, "unrealized_intraday_pl", 0)),
                day_change_percent=float(getattr(position, "unrealized_intraday_plpc", 0)) * 100,
                asset_class=getattr(position, "asset_class", "stock"),
                exchange=getattr(position, "exchange", "NASDAQ"),
            )
            position_details.append(position_detail)

        return position_details

    except Exception as e:
        return []


@router.get("/account", response_model=AccountInfo)
async def get_account_info():
    """Get current account information from active broker"""
    try:
        get_broker_or_raise()  # Just check that broker is available
        broker_manager = get_broker_manager()

        # Get account info from broker manager
        account = await broker_manager.get_account_info()

        return AccountInfo(
            account_id=account.account_id,
            account_type=getattr(account, "account_type", "margin"),
            buying_power=float(account.buying_power),
            cash=float(account.cash),
            portfolio_value=float(account.portfolio_value),
            equity=float(account.equity),
            day_trading_power=float(getattr(account, "day_trading_power", account.buying_power)),
            pattern_day_trader=getattr(account, "pattern_day_trader", False),
            day_trade_count=getattr(account, "day_trade_count", 0),
            account_status=getattr(account, "status", "active"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get account info: {e!s}")


@router.get("/orders", response_model=list[OrderDetail])
async def get_recent_orders(limit: int = 50):
    """Get recent orders from active broker"""
    try:
        broker = get_broker_or_none()
        if not broker:
            return []

        broker_manager = get_broker_manager()
        # Get orders from broker manager
        orders = await broker_manager.get_orders(limit=limit)

        order_details = []
        for order in orders:
            order_detail = OrderDetail(
                order_id=order.id,
                symbol=order.symbol,
                side=order.side,
                quantity=float(order.qty),
                order_type=order.order_type,
                status=order.status,
                filled_quantity=float(order.filled_qty),
                price=float(order.limit_price) if order.limit_price else None,
                filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                created_at=order.created_at,
                updated_at=order.updated_at,
                time_in_force=order.time_in_force,
            )
            order_details.append(order_detail)

        return order_details

    except Exception as e:
        return []


@router.get("/positions/{symbol}", response_model=PositionDetail)
async def get_position_by_symbol(symbol: str):
    """Get detailed position information for a specific symbol from active broker"""
    try:
        get_broker_or_raise()  # Just check that broker is available
        broker_manager = get_broker_manager()

        # Get specific position
        position = await broker_manager.get_position(symbol.upper())

        if not position:
            raise HTTPException(status_code=404, detail=f"Position for {symbol} not found")

        # Get current price
        try:
            current_price = await broker_manager.get_current_price(position.symbol)
        except Exception:
            current_price = position.market_value / abs(position.qty) if position.qty != 0 else 0

        return PositionDetail(
            symbol=position.symbol,
            quantity=float(position.qty),
            side=position.side,
            avg_entry_price=float(position.avg_entry_price),
            current_price=current_price,
            market_value=float(position.market_value),
            unrealized_pnl=float(position.unrealized_pl),
            unrealized_pnl_percent=float(position.unrealized_plpc) * 100,
            cost_basis=float(position.cost_basis),
            portfolio_percentage=float(getattr(position, "portfolio_pct", 0)) * 100,
            day_change=float(getattr(position, "unrealized_intraday_pl", 0)),
            day_change_percent=float(getattr(position, "unrealized_intraday_plpc", 0)) * 100,
            asset_class=getattr(position, "asset_class", "stock"),
            exchange=getattr(position, "exchange", "NASDAQ"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get position: {e!s}")


@router.get("/performance", response_model=dict[str, Any])
async def get_performance_metrics():
    """Get portfolio performance metrics from active broker"""
    try:
        broker = get_broker_or_none()
        broker_manager = get_broker_manager()
        active_broker_name = broker_manager.get_active_broker_name()

        if not broker:
            return {
                "error": "No active broker connected",
                "current_portfolio_value": 0.0,
                "cash": 0.0,
                "total_unrealized_pnl": 0.0,
                "total_positions": 0,
                "last_updated": datetime.now(),
            }

        # Get account info and positions from broker manager
        account = await broker_manager.get_account_info()
        positions = await broker_manager.get_positions()

        # Get performance data
        return {
            "current_portfolio_value": float(account.portfolio_value),
            "cash": float(account.cash),
            "total_unrealized_pnl": sum(float(p.unrealized_pl) for p in positions),
            "total_positions": len(positions),
            "day_trade_count": getattr(account, "day_trade_count", 0),
            "active_broker": active_broker_name,
            "positions_summary": {
                "long_positions": len([p for p in positions if float(p.qty) > 0]),
                "short_positions": len([p for p in positions if float(p.qty) < 0]),
                "total_market_value": sum(float(p.market_value) for p in positions),
            },
            "last_updated": datetime.now(),
        }

    except Exception as e:
        return {
            "error": str(e),
            "current_portfolio_value": 0.0,
            "cash": 0.0,
            "total_unrealized_pnl": 0.0,
            "total_positions": 0,
            "last_updated": datetime.now(),
        }


# Trading Control APIs
@router.post("/start")
async def start_trading():
    """Start the automated trading system"""
    raise HTTPException(
        status_code=501,
        detail="Automated trading system not implemented yet. Use broker-specific trading endpoints instead.",
    )


@router.post("/stop")
async def stop_trading():
    """Stop the automated trading system"""
    raise HTTPException(
        status_code=501,
        detail="Automated trading system not implemented yet. Use broker-specific trading endpoints instead.",
    )


@router.get("/market-status")
async def get_market_status():
    """Get current market status from active broker"""
    try:
        broker = get_broker_or_none()
        broker_manager = get_broker_manager()
        active_broker_name = broker_manager.get_active_broker_name()

        if not broker:
            return {
                "is_open": False,
                "error": "No active broker connected",
                "last_updated": datetime.now().isoformat(),
            }

        # Get market clock from broker manager
        clock = await broker_manager.get_market_clock()

        return {
            "is_open": clock.is_open,
            "next_open": clock.next_open.isoformat() if clock.next_open else None,
            "next_close": clock.next_close.isoformat() if clock.next_close else None,
            "timezone": getattr(clock, "timezone", "America/New_York"),
            "active_broker": active_broker_name,
            "last_updated": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "is_open": False,
            "error": str(e),
            "last_updated": datetime.now().isoformat(),
        }


@router.get("/debug/broker-status")
async def get_broker_status():
    """Get current broker manager status for debugging"""
    broker_manager = get_broker_manager()

    return {
        "active_broker": str(broker_manager.active_broker) if broker_manager.active_broker else None,
        "active_broker_name": broker_manager.active_broker_name,
        "available_brokers": {
            name: {
                "connected": info.get("connected", False),
                "config": bool(info.get("config")),
                "adapter_class": str(info.get("adapter_class")) if info.get("adapter_class") else None,
            }
            for name, info in broker_manager.available_brokers.items()
        },
    }
