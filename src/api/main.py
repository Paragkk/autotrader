"""
FastAPI application for the Advanced Trading System
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from api.routes import brokers_router, trading_router
from core.broker_manager import get_broker_manager, initialize_default_brokers
from dashboard.manager import DashboardManager
from infra.logging_config import setup_logging

logger = logging.getLogger(__name__)

# Global instances
dashboard_manager: DashboardManager | None = None


# Utility functions for reducing redundancy
def get_broker_or_none():
    """Get connected broker or return None if not available"""
    try:
        broker_manager = get_broker_manager()
        return broker_manager.get_active_broker()
    except Exception as e:
        logger.warning(f"Failed to get active broker: {e}")
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    global dashboard_manager

    # Startup
    try:
        setup_logging()
        logger.info("Starting AutoTrader Pro API...")

        # Initialize broker manager and connect to default broker
        broker_initialized = await initialize_default_brokers()
        if broker_initialized:
            broker_manager = get_broker_manager()
            active_broker_name = broker_manager.get_active_broker_name()
            logger.info(f"[SUCCESS] Connected to active broker: {active_broker_name}")
        else:
            logger.warning("[WARNING] No broker connected - system will run in limited mode")

        # Initialize dashboard manager
        dashboard_manager = DashboardManager(dashboard_port=8501, api_base_url="http://localhost:8080")

        # Try to start dashboard (non-blocking)
        try:
            if dashboard_manager.start_dashboard():
                logger.info("[SUCCESS] Dashboard started successfully at http://localhost:8501")
            else:
                logger.warning("[WARNING] Dashboard failed to start - continuing without dashboard")
                logger.info("[INFO] You can start the dashboard manually by running: uv run streamlit run src/dashboard/main.py --server.port 8501")
        except Exception as e:
            logger.warning(f"[WARNING] Dashboard startup failed: {e} - continuing without dashboard")
            logger.info("[INFO] You can start the dashboard manually by running: uv run streamlit run src/dashboard/main.py --server.port 8501")

        yield

    except Exception as e:
        logger.exception(f"Failed to start API: {e}")
        yield

    # Shutdown
    try:
        logger.info("Shutting down AutoTrader Pro API...")

        # Disconnect from active broker
        try:
            broker_manager = get_broker_manager()
            active_broker_name = broker_manager.get_active_broker_name()
            if active_broker_name:
                await broker_manager.disconnect_all_brokers()
                logger.info(f"[SUCCESS] Disconnected from active broker: {active_broker_name}")
        except Exception as e:
            logger.exception(f"Error disconnecting broker: {e}")

        # Stop dashboard
        if dashboard_manager:
            dashboard_manager.stop_dashboard()
            logger.info("[SUCCESS] Dashboard stopped")

        logger.info("[COMPLETE] AutoTrader Pro shutdown complete")

    except Exception as e:
        logger.exception(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="AutoTrader Pro API",
    description="Professional automated trading system with multi-broker support",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(trading_router)
app.include_router(brokers_router)


class SystemStatusResponse(BaseModel):
    system_running: bool
    active_positions: int
    max_positions: int
    pending_signals: int
    portfolio_value: float
    available_cash: float
    market_hours: bool
    last_update: datetime


@app.get("/", response_class=HTMLResponse)
async def read_root() -> str:
    """Main dashboard page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AutoTrader Pro Dashboard</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; color: white; margin-bottom: 30px; }
            .header h1 { font-size: 3rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
            .header p { font-size: 1.2rem; opacity: 0.9; }
            .card { background: rgba(255,255,255,0.95); padding: 25px; margin: 20px 0; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); backdrop-filter: blur(10px); }
            .card h2 { color: #333; margin-top: 0; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
            .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
            .metric { background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 20px; border-radius: 10px; text-align: center; }
            .metric h3 { margin: 0 0 10px 0; font-size: 0.9rem; opacity: 0.8; }
            .metric .value { font-size: 1.8rem; font-weight: bold; }
            .status-running { color: #28a745; }
            .status-stopped { color: #dc3545; }
            .broker-status { padding: 15px; background: #f8f9fa; border-radius: 8px; margin: 15px 0; border-left: 4px solid #007bff; }
            .btn { display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 6px; margin: 5px; transition: all 0.3s; }
            .btn:hover { background: #5a6fd8; transform: translateY(-2px); }
            .links { display: flex; justify-content: center; gap: 20px; margin: 20px 0; flex-wrap: wrap; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 AutoTrader Pro</h1>
                <p>Professional Multi-Broker Trading System</p>
            </div>

            <div class="card">
                <h2>📊 System Overview</h2>
                <div id="systemStatus">Loading system status...</div>
                <div class="metrics" id="metrics"></div>
            </div>

            <div class="card">
                <h2>🏦 Broker Status</h2>
                <div id="brokerStatus">Loading broker information...</div>
            </div>

            <div class="card">
                <h2>🔗 Quick Links</h2>
                <div class="links">
                    <a href="/docs" class="btn">📚 API Documentation</a>
                    <a href="http://localhost:8501" class="btn">📈 Trading Dashboard</a>
                    <a href="/api/brokers/status" class="btn">🏦 Broker Status</a>
                    <a href="/api/account" class="btn">💰 Account Info</a>
                </div>
                <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px; text-align: center;">
                    <p style="margin: 0; color: white; opacity: 0.8;">
                        💡 <strong>Dashboard Alternative:</strong> If the Streamlit dashboard link above doesn't work,
                        you can start it manually by running:<br>
                        <code style="background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px; margin: 8px;">
                            uv run streamlit run src/dashboard/main.py --server.port 8501
                        </code>
                    </p>
                </div>
            </div>
        </div>

        <script>
            async function loadSystemStatus() {
                try {
                    const response = await fetch('/api/status');
                    const status = await response.json();

                    document.getElementById('systemStatus').innerHTML = `
                        <div class="broker-status">
                            <strong>System Status:</strong>
                            <span class="status-${status.system_running ? 'running' : 'stopped'}">
                                ${status.system_running ? '🟢 Running' : '🔴 Stopped'}
                            </span>
                        </div>
                    `;

                    document.getElementById('metrics').innerHTML = `
                        <div class="metric">
                            <h3>Active Positions</h3>
                            <div class="value">${status.active_positions}/${status.max_positions}</div>
                        </div>
                        <div class="metric">
                            <h3>Portfolio Value</h3>
                            <div class="value">$${status.portfolio_value.toLocaleString()}</div>
                        </div>
                        <div class="metric">
                            <h3>Available Cash</h3>
                            <div class="value">$${status.available_cash.toLocaleString()}</div>
                        </div>
                        <div class="metric">
                            <h3>Market Status</h3>
                            <div class="value">${status.market_hours ? '🟢 Open' : '🔴 Closed'}</div>
                        </div>
                    `;
                } catch (error) {
                    console.error('Error loading system status:', error);
                    document.getElementById('systemStatus').innerHTML = '<div class="broker-status">❌ Error loading system status</div>';
                }
            }

            async function loadBrokerStatus() {
                try {
                    const response = await fetch('/api/brokers/status');
                    const brokerData = await response.json();

                    let brokerHtml = '';

                    if (brokerData.connected_brokers && brokerData.connected_brokers.length > 0) {
                        const activeBroker = brokerData.connected_brokers[0];
                        brokerHtml += `
                            <div class="broker-status">
                                <strong>Active Broker:</strong> ${activeBroker}
                                <span class="status-running">🟢 Connected</span>
                            </div>
                        `;
                    } else {
                        brokerHtml += '<div class="broker-status">⚠️ No broker connected</div>';
                    }

                    brokerHtml += '<h3>Available Brokers:</h3>';
                    brokerData.available_brokers.forEach(broker => {
                        const statusIcon = broker.connected ? '🟢' : '⚪';
                        const paperText = broker.paper_trading ? ' (Paper)' : ' (Live)';
                        const activeText = broker.connected ? ' - ACTIVE' : '';
                        brokerHtml += `
                            <div class="broker-status">
                                ${statusIcon} <strong>${broker.display_name}</strong>${paperText}${activeText}
                            </div>
                        `;
                    });

                    document.getElementById('brokerStatus').innerHTML = brokerHtml;
                } catch (error) {
                    console.error('Error loading broker status:', error);
                    document.getElementById('brokerStatus').innerHTML = '<div class="broker-status">❌ Error loading broker information</div>';
                }
            }

            // Load data on page load
            loadSystemStatus();
            loadBrokerStatus();

            // Auto-refresh every 30 seconds
            setInterval(() => {
                loadSystemStatus();
                loadBrokerStatus();
            }, 30000);
        </script>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now()}


@app.get("/api/status", response_model=SystemStatusResponse)
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


class TradingSystemStatus(BaseModel):
    """Trading system status response"""

    status: str
    is_running: bool
    last_data_update: datetime | None = None
    last_news_update: datetime | None = None
    last_strategy_evaluation: datetime | None = None
    last_screening_update: datetime | None = None
    portfolio_value: float | None = None
    positions_count: int = 0
    unrealized_pnl: float | None = None
    screening_enabled: bool = False
    tracked_symbols_count: int = 0


class ScreeningRequest(BaseModel):
    """Stock screening request"""

    min_price: float = 5.0
    max_price: float = 1000.0
    min_volume: int = 100000
    min_daily_change: float = -20.0
    max_daily_change: float = 20.0
    max_results: int = 50
    exclude_penny_stocks: bool = True


class ScreeningResponse(BaseModel):
    """Stock screening response"""

    symbol: str
    current_price: float
    daily_change_percent: float
    volume: int
    score: float
    reasons: list[str]
    timestamp: datetime


class TradingSignal(BaseModel):
    """Trading signal response"""

    symbol: str
    signal_type: str
    strength: float
    strategy: str
    timestamp: datetime
    metadata: dict[str, Any]


class ConfigUpdate(BaseModel):
    """Configuration update request"""

    symbols_to_track: list[str] | None = None
    strategy_weights: dict[str, float] | None = None
    max_positions: int | None = None
    position_size_percent: float | None = None
    stop_loss_percent: float | None = None
    take_profit_percent: float | None = None
    enable_automated_screening: bool | None = None
    screening_interval_minutes: int | None = None
    max_screened_symbols: int | None = None


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


# Portfolio and Position APIs
@app.get("/api/portfolio", response_model=PortfolioSummary)
async def get_portfolio_summary():
    """Get current portfolio summary including all positions from active broker"""
    try:
        broker = get_broker_or_none()
        broker_manager = get_broker_manager()

        if not broker:
            logger.warning("No active broker connected")
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
        logger.exception(f"Failed to get portfolio summary: {e}")
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


@app.get("/api/positions", response_model=list[PositionDetail])
async def get_current_positions():
    """Get detailed list of all current positions from active broker"""
    try:
        broker = get_broker_or_none()
        if not broker:
            logger.warning("No active broker connected")
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
        logger.exception(f"Failed to get positions: {e}")
        return []


@app.get("/api/account", response_model=AccountInfo)
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
        logger.exception(f"Failed to get account info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get account info: {e!s}")


@app.get("/api/orders", response_model=list[OrderDetail])
async def get_recent_orders(limit: int = 50):
    """Get recent orders from active broker"""
    try:
        broker = get_broker_or_none()
        if not broker:
            logger.warning("No active broker connected")
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
        logger.exception(f"Failed to get orders: {e}")
        return []


@app.get("/api/positions/{symbol}", response_model=PositionDetail)
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
        logger.exception(f"Failed to get position for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get position: {e!s}")


@app.get("/api/performance", response_model=dict[str, Any])
async def get_performance_metrics():
    """Get portfolio performance metrics from active broker"""
    try:
        broker = get_broker_or_none()
        broker_manager = get_broker_manager()
        active_broker_name = broker_manager.get_active_broker_name()

        if not broker:
            logger.warning("No active broker connected")
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
        logger.exception(f"Failed to get performance metrics: {e}")
        return {
            "error": str(e),
            "current_portfolio_value": 0.0,
            "cash": 0.0,
            "total_unrealized_pnl": 0.0,
            "total_positions": 0,
            "last_updated": datetime.now(),
        }


# Trading Control APIs
@app.post("/api/start")
async def start_trading():
    """Start the automated trading system"""
    logger.info("Trading system start requested")
    raise HTTPException(
        status_code=501,
        detail="Automated trading system not implemented yet. Use broker-specific trading endpoints instead.",
    )


@app.post("/api/stop")
async def stop_trading():
    """Stop the automated trading system"""
    logger.info("Trading system stop requested")
    raise HTTPException(
        status_code=501,
        detail="Automated trading system not implemented yet. Use broker-specific trading endpoints instead.",
    )


@app.get("/api/market-status")
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
        logger.exception(f"Failed to get market status: {e}")
        return {
            "is_open": False,
            "error": str(e),
            "last_updated": datetime.now().isoformat(),
        }
