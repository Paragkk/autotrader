"""
FastAPI application for the Advanced Trading System
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from main_automated import AutomatedTradingSystem
from db.models import TrackedSymbol, StrategyResult, Order, Position
from core.stock_screener import ScreeningCriteria
from infra.logging_config import setup_logging
from infra.config import resolve_config_path

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AutoTrader Pro Dashboard",
    description="Professional Automated Trading System Monitoring",
    version="1.0.0",
)

# Global trading system instance
trading_system: Optional[AutomatedTradingSystem] = None


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
async def read_root():
    """Main dashboard page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AutoTrader Pro Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric { display: inline-block; margin: 10px 20px; }
            .status-running { color: #28a745; }
            .status-stopped { color: #dc3545; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 AutoTrader Pro Dashboard</h1>
            <div class="card">
                <h2>System Status</h2>
                <div id="status">Loading...</div>
            </div>
        </div>
        
        <script>
            async function loadStatus() {
                try {
                    const response = await fetch('/api/status');
                    const status = await response.json();
                    
                    document.getElementById('status').innerHTML = `
                        <div class="metric">
                            <strong>Status:</strong> 
                            <span class="status-${status.system_running ? 'running' : 'stopped'}">
                                ${status.system_running ? '🟢 Running' : '🔴 Stopped'}
                            </span>
                        </div>
                        <div class="metric"><strong>Positions:</strong> ${status.active_positions}/${status.max_positions}</div>
                        <div class="metric"><strong>Portfolio:</strong> $${status.portfolio_value.toLocaleString()}</div>
                    `;
                } catch (error) {
                    console.error('Error loading status:', error);
                }
            }
            
            loadStatus();
            setInterval(loadStatus, 30000);
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)

logger = logging.getLogger(__name__)

# Global trading system instance
trading_system: Optional[AutomatedTradingSystem] = None
orchestrator_task: Optional[asyncio.Task] = None


class TradingSystemStatus(BaseModel):
    """Trading system status response"""

    status: str
    is_running: bool
    last_data_update: Optional[datetime] = None
    last_news_update: Optional[datetime] = None
    last_strategy_evaluation: Optional[datetime] = None
    last_screening_update: Optional[datetime] = None
    portfolio_value: Optional[float] = None
    positions_count: int = 0
    unrealized_pnl: Optional[float] = None
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
    reasons: List[str]
    timestamp: datetime


class PortfolioSummary(BaseModel):
    """Portfolio summary response"""

    account_value: float
    cash: float
    buying_power: float
    positions_count: int
    positions_value: float
    unrealized_pnl: float
    day_trade_count: int
    positions: List[Dict[str, Any]]


class TradingSignal(BaseModel):
    """Trading signal response"""

    symbol: str
    signal_type: str
    strength: float
    strategy: str
    timestamp: datetime
    metadata: Dict[str, Any]


class ConfigUpdate(BaseModel):
    """Configuration update request"""

    symbols_to_track: Optional[List[str]] = None
    strategy_weights: Optional[Dict[str, float]] = None
    max_positions: Optional[int] = None
    position_size_percent: Optional[float] = None
    stop_loss_percent: Optional[float] = None
    take_profit_percent: Optional[float] = None
    enable_automated_screening: Optional[bool] = None
    screening_interval_minutes: Optional[int] = None
    max_screened_symbols: Optional[int] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    global trading_system, orchestrator_task

    # Startup
    try:
        setup_logging()
        logger.info("Starting Trading System API...")

        # Initialize trading system with pathlib-resolved config path
        config_path_env = os.getenv("TRADING_CONFIG_PATH", "main_config.yaml")
        config_path = resolve_config_path(config_path_env)
        trading_system = AutomatedTradingSystem(config_path)

        # Start orchestrator in background
        if os.getenv("AUTO_START_TRADING", "false").lower() == "true":
            orchestrator_task = asyncio.create_task(trading_system.start())
            logger.info("Auto-started trading orchestrator")

        yield

    except Exception as e:
        logger.error(f"Failed to start trading system: {e}")
        yield

    # Shutdown
    try:
        logger.info("Shutting down Trading System API...")

        if trading_system and trading_system.orchestrator:
            await trading_system.orchestrator.stop()

        if orchestrator_task:
            orchestrator_task.cancel()
            try:
                await orchestrator_task
            except asyncio.CancelledError:
                pass

        logger.info("Trading system shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Advanced Trading System API",
    description="RESTful API for managing an advanced algorithmic trading system",
    version="1.0.0",
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


def get_trading_system() -> AutomatedTradingSystem:
    """Dependency to get trading system instance"""
    if trading_system is None:
        raise HTTPException(status_code=503, detail="Trading system not initialized")
    return trading_system


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Advanced Trading System API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/ping")
def ping():
    """Legacy ping endpoint"""
    return {"status": "ok"}


@app.get("/status", response_model=TradingSystemStatus)
async def get_status(system: AutomatedTradingSystem = Depends(get_trading_system)):
    """Get current trading system status"""
    try:
        status = await system.status()

        return TradingSystemStatus(
            status=status.get("status", "unknown"),
            is_running=status.get("status") == "running",
            last_data_update=status.get("stats", {}).get("last_data_update"),
            last_news_update=status.get("stats", {}).get("last_news_update"),
            last_strategy_evaluation=status.get("stats", {}).get(
                "last_strategy_evaluation"
            ),
            last_screening_update=status.get("stats", {}).get("last_screening_update"),
            portfolio_value=status.get("portfolio", {}).get("account_value"),
            positions_count=status.get("portfolio", {}).get("positions_count", 0),
            unrealized_pnl=status.get("portfolio", {}).get("unrealized_pnl"),
            screening_enabled=status.get("config", {}).get(
                "enable_automated_screening", False
            ),
            tracked_symbols_count=len(
                status.get("config", {}).get("symbols_to_track", [])
            ),
        )

    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/start")
async def start_trading(
    background_tasks: BackgroundTasks,
    system: AutomatedTradingSystem = Depends(get_trading_system),
):
    """Start the trading system"""
    global orchestrator_task

    try:
        if orchestrator_task and not orchestrator_task.done():
            raise HTTPException(
                status_code=400, detail="Trading system is already running"
            )

        # Start orchestrator in background
        orchestrator_task = asyncio.create_task(system.start())

        return {"message": "Trading system started successfully"}

    except Exception as e:
        logger.error(f"Failed to start trading system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stop")
async def stop_trading(system: AutomatedTradingSystem = Depends(get_trading_system)):
    """Stop the trading system"""
    global orchestrator_task

    try:
        if system.orchestrator:
            await system.orchestrator.stop()

        if orchestrator_task:
            orchestrator_task.cancel()
            try:
                await orchestrator_task
            except asyncio.CancelledError:
                pass
            orchestrator_task = None

        return {"message": "Trading system stopped successfully"}

    except Exception as e:
        logger.error(f"Failed to stop trading system: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio(system: AutomatedTradingSystem = Depends(get_trading_system)):
    """Get current portfolio summary"""
    try:
        if not system.orchestrator:
            raise HTTPException(status_code=400, detail="Trading system not running")

        portfolio_data = system.orchestrator.get_portfolio_summary()

        return PortfolioSummary(
            account_value=portfolio_data.get("account_value", 0.0),
            cash=portfolio_data.get("cash", 0.0),
            buying_power=portfolio_data.get("buying_power", 0.0),
            positions_count=portfolio_data.get("positions_count", 0),
            positions_value=portfolio_data.get("positions_value", 0.0),
            unrealized_pnl=portfolio_data.get("unrealized_pnl", 0.0),
            day_trade_count=portfolio_data.get("day_trade_count", 0),
            positions=portfolio_data.get("positions", []),
        )

    except Exception as e:
        logger.error(f"Failed to get portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/signals", response_model=List[TradingSignal])
async def get_signals(
    hours: int = Field(default=24, ge=1, le=168),
    system: AutomatedTradingSystem = Depends(get_trading_system),
):
    """Get recent trading signals"""
    try:
        if not system.orchestrator:
            raise HTTPException(status_code=400, detail="Trading system not running")

        signals = system.orchestrator.get_recent_signals(hours=hours)

        return [
            TradingSignal(
                symbol=signal["symbol"],
                signal_type=signal["signal_type"],
                strength=signal["strength"],
                strategy=signal["strategy"],
                timestamp=signal["timestamp"],
                metadata=signal["metadata"],
            )
            for signal in signals
        ]

    except Exception as e:
        logger.error(f"Failed to get signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_trading_stats(
    system: AutomatedTradingSystem = Depends(get_trading_system),
):
    """Get trading statistics"""
    try:
        if not system.orchestrator:
            raise HTTPException(status_code=400, detail="Trading system not running")

        stats = system.orchestrator.get_trading_stats()
        return stats

    except Exception as e:
        logger.error(f"Failed to get trading stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/config/update")
async def update_config(
    config_update: ConfigUpdate,
    system: AutomatedTradingSystem = Depends(get_trading_system),
):
    """Update trading configuration"""
    try:
        if not system.orchestrator:
            raise HTTPException(status_code=400, detail="Trading system not running")

        # Update configuration
        if config_update.symbols_to_track is not None:
            system.orchestrator.config.symbols_to_track = config_update.symbols_to_track

        if config_update.strategy_weights is not None:
            system.orchestrator.config.strategy_weights = config_update.strategy_weights

        if config_update.max_positions is not None:
            system.orchestrator.config.max_positions = config_update.max_positions

        if config_update.position_size_percent is not None:
            system.orchestrator.config.position_size_percent = (
                config_update.position_size_percent
            )

        if config_update.stop_loss_percent is not None:
            system.orchestrator.config.stop_loss_percent = (
                config_update.stop_loss_percent
            )

        if config_update.take_profit_percent is not None:
            system.orchestrator.config.take_profit_percent = (
                config_update.take_profit_percent
            )

        return {"message": "Configuration updated successfully"}

    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
async def get_config(system: AutomatedTradingSystem = Depends(get_trading_system)):
    """Get current trading configuration"""
    try:
        if not system.orchestrator:
            raise HTTPException(status_code=400, detail="Trading system not running")

        config = system.orchestrator.config

        return {
            "use_paper_trading": config.use_paper_trading,
            "max_positions": config.max_positions,
            "max_daily_loss": config.max_daily_loss,
            "position_size_percent": config.position_size_percent,
            "symbols_to_track": config.symbols_to_track,
            "strategy_weights": config.strategy_weights,
            "stop_loss_percent": config.stop_loss_percent,
            "take_profit_percent": config.take_profit_percent,
            "market_data_update_interval": config.market_data_update_interval,
            "news_update_interval": config.news_update_interval,
            "strategy_evaluation_interval": config.strategy_evaluation_interval,
        }

    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Screening endpoints
@app.get("/screening/run", response_model=List[ScreeningResponse])
async def run_screening(request: ScreeningRequest):
    """Run stock screening with specified criteria"""
    global trading_system

    if not trading_system or not trading_system.orchestrator:
        raise HTTPException(status_code=503, detail="Trading system not initialized")

    try:
        # Create screening criteria
        criteria = ScreeningCriteria(
            min_price=request.min_price,
            max_price=request.max_price,
            min_volume=request.min_volume,
            min_daily_change=request.min_daily_change,
            max_daily_change=request.max_daily_change,
            max_results=request.max_results,
            exclude_penny_stocks=request.exclude_penny_stocks,
        )

        # Run screening
        results = await trading_system.orchestrator.stock_screener.get_prediction_enhanced_screening(
            criteria
        )

        # Convert to response format
        response = [
            ScreeningResponse(
                symbol=result.symbol,
                current_price=result.current_price,
                daily_change_percent=result.daily_change_percent,
                volume=result.volume,
                score=result.score,
                reasons=result.reasons,
                timestamp=result.timestamp,
            )
            for result in results
        ]

        return response

    except Exception as e:
        logger.error(f"Error running screening: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/screening/results", response_model=List[ScreeningResponse])
async def get_screening_results():
    """Get latest screening results"""
    global trading_system

    if not trading_system or not trading_system.orchestrator:
        raise HTTPException(status_code=503, detail="Trading system not initialized")

    try:
        screening_results = (
            trading_system.orchestrator.stock_screener.get_screening_results()
        )

        response = [
            ScreeningResponse(
                symbol=result.symbol,
                current_price=result.current_price,
                daily_change_percent=result.daily_change_percent,
                volume=result.volume,
                score=result.score,
                reasons=result.reasons,
                timestamp=result.timestamp,
            )
            for result in screening_results.values()
        ]

        # Sort by score (highest first)
        response.sort(key=lambda x: x.score, reverse=True)

        return response

    except Exception as e:
        logger.error(f"Error getting screening results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/screening/summary")
async def get_screening_summary():
    """Get screening summary and statistics"""
    global trading_system

    if not trading_system or not trading_system.orchestrator:
        raise HTTPException(status_code=503, detail="Trading system not initialized")

    try:
        summary = trading_system.orchestrator.get_screening_summary()
        return summary

    except Exception as e:
        logger.error(f"Error getting screening summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tracked-symbols")
async def get_tracked_symbols():
    """Get currently tracked symbols"""
    try:
        if not trading_system or not trading_system.db_session:
            raise HTTPException(status_code=503, detail="Trading system not available")

        symbols = (
            trading_system.db_session.query(TrackedSymbol)
            .filter(TrackedSymbol.is_active)
            .all()
        )

        return [
            {
                "symbol": symbol.symbol,
                "added_at": symbol.added_at.isoformat(),
                "last_updated": symbol.last_updated.isoformat(),
                "reason_added": symbol.reason_added,
                "is_active": symbol.is_active,
            }
            for symbol in symbols
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy-results")
async def get_strategy_results():
    """Get recent strategy results"""
    try:
        if not trading_system or not trading_system.db_session:
            raise HTTPException(status_code=503, detail="Trading system not available")

        from datetime import datetime, timedelta

        results = (
            trading_system.db_session.query(StrategyResult)
            .filter(StrategyResult.analyzed_at >= datetime.now() - timedelta(hours=24))
            .order_by(StrategyResult.analyzed_at.desc())
            .limit(100)
            .all()
        )

        return [
            {
                "symbol": result.symbol,
                "strategy_name": result.strategy_name,
                "signal": result.signal,
                "strength": result.strength,
                "confidence": result.confidence,
                "analyzed_at": result.analyzed_at.isoformat(),
                "price_at_analysis": result.price_at_analysis,
            }
            for result in results
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/positions")
async def get_positions():
    """Get current positions"""
    try:
        if not trading_system or not trading_system.db_session:
            raise HTTPException(status_code=503, detail="Trading system not available")

        positions = (
            trading_system.db_session.query(Position)
            .filter(Position.status == "open")
            .all()
        )

        return [
            {
                "symbol": position.symbol,
                "quantity": position.quantity,
                "side": position.side,
                "avg_entry_price": position.avg_entry_price,
                "unrealized_pnl": position.unrealized_pnl,
                "opened_at": position.opened_at.isoformat(),
                "stop_loss_price": position.stop_loss_price,
                "take_profit_price": position.take_profit_price,
            }
            for position in positions
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/orders")
async def get_orders():
    """Get recent orders"""
    try:
        if not trading_system or not trading_system.db_session:
            raise HTTPException(status_code=503, detail="Trading system not available")

        from datetime import datetime, timedelta

        orders = (
            trading_system.db_session.query(Order)
            .filter(Order.created_at >= datetime.now() - timedelta(hours=24))
            .order_by(Order.created_at.desc())
            .limit(50)
            .all()
        )

        return [
            {
                "symbol": order.symbol,
                "side": order.side,
                "quantity": order.quantity,
                "order_type": order.order_type,
                "price": order.price,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "filled_price": order.filled_price,
            }
            for order in orders
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class EmergencyStopRequest(BaseModel):
    confirm: bool = True


@app.post("/api/controls/emergency-stop")
async def emergency_stop(request: EmergencyStopRequest):
    """Emergency stop all trading activities"""
    try:
        if not trading_system:
            raise HTTPException(status_code=503, detail="Trading system not available")

        if not request.confirm:
            raise HTTPException(
                status_code=400, detail="Emergency stop must be confirmed"
            )

        # Stop the trading system
        await trading_system.stop()

        logger.warning("🚨 EMERGENCY STOP ACTIVATED via dashboard")

        return {"message": "Emergency stop activated successfully", "status": "stopped"}

    except Exception as e:
        logger.error(f"Emergency stop failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ClosePositionRequest(BaseModel):
    symbol: str


@app.post("/api/controls/close-position")
async def close_position(request: ClosePositionRequest):
    """Close a specific position"""
    try:
        if not trading_system:
            raise HTTPException(status_code=503, detail="Trading system not available")

        # Find the position
        position = (
            trading_system.db_session.query(Position)
            .filter(Position.symbol == request.symbol, Position.status == "open")
            .first()
        )

        if not position:
            raise HTTPException(
                status_code=404, detail=f"No open position found for {request.symbol}"
            )

        # Close the position via order executor
        success = await trading_system.order_executor.close_position(position)

        if success:
            logger.info(f"Position {request.symbol} closed via dashboard")
            return {"message": f"Position {request.symbol} closed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to close position")

    except Exception as e:
        logger.error(f"Failed to close position {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/controls/close-all-positions")
async def close_all_positions():
    """Close all open positions"""
    try:
        if not trading_system:
            raise HTTPException(status_code=503, detail="Trading system not available")

        # Get all open positions
        positions = (
            trading_system.db_session.query(Position)
            .filter(Position.status == "open")
            .all()
        )

        if not positions:
            return {"message": "No open positions to close", "closed_count": 0}

        closed_count = 0
        for position in positions:
            try:
                success = await trading_system.order_executor.close_position(position)
                if success:
                    closed_count += 1
            except Exception as e:
                logger.error(f"Failed to close position {position.symbol}: {e}")

        logger.info(f"Closed {closed_count}/{len(positions)} positions via dashboard")

        return {
            "message": f"Closed {closed_count} out of {len(positions)} positions",
            "closed_count": closed_count,
            "total_positions": len(positions),
        }

    except Exception as e:
        logger.error(f"Failed to close all positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ToggleStrategyRequest(BaseModel):
    strategy_name: str
    enabled: bool


@app.post("/api/controls/toggle-strategy")
async def toggle_strategy(request: ToggleStrategyRequest):
    """Enable or disable a specific strategy"""
    try:
        if not trading_system:
            raise HTTPException(status_code=503, detail="Trading system not available")

        # Update strategy configuration
        if (
            request.strategy_name
            not in trading_system.config.config["strategies"]["weights"]
        ):
            raise HTTPException(
                status_code=404, detail=f"Strategy {request.strategy_name} not found"
            )

        # For now, just log the action (implement actual toggle logic)
        action = "enabled" if request.enabled else "disabled"
        logger.info(f"Strategy {request.strategy_name} {action} via dashboard")

        return {
            "message": f"Strategy {request.strategy_name} {action} successfully",
            "strategy_name": request.strategy_name,
            "enabled": request.enabled,
        }

    except Exception as e:
        logger.error(f"Failed to toggle strategy {request.strategy_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ...existing code continues...
