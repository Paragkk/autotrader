"""
FastAPI application for the Advanced Trading System
"""

import logging
import traceback
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from api.routes import brokers_router, core_router, trading_router
from core.broker_manager import get_broker_manager, initialize_default_brokers
from dashboard.manager import DashboardManager
from infra.config import load_config
from infra.logging_config import setup_logging

logger = logging.getLogger(__name__)

# Global instances
dashboard_manager: DashboardManager | None = None
startup_timestamp: datetime | None = None


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


async def _initialize_broker(require_broker: bool) -> bool:
    """Initialize broker connection"""
    broker_initialized = await initialize_default_brokers()
    if not broker_initialized and require_broker:
        logger.error("[CRITICAL] Failed to connect to any broker - shutting down")
        error_msg = "No broker connection available - cannot continue"
        raise RuntimeError(error_msg)

    if not broker_initialized:
        logger.warning("[WARNING] No broker connected - system will run in limited mode")
        return False

    broker_manager = get_broker_manager()
    active_broker_name = broker_manager.get_active_broker_name()
    logger.info(f"[SUCCESS] Connected to active broker: {active_broker_name}")
    return True


async def _initialize_dashboard(dashboard_manager: DashboardManager, require_dashboard: bool) -> bool:
    """Initialize dashboard"""
    logger.info("Starting dashboard...")
    dashboard_started = dashboard_manager.start_dashboard()

    if not dashboard_started and require_dashboard:
        logger.error("[CRITICAL] Dashboard failed to start - shutting down")
        error_msg = "Dashboard startup failed - cannot continue"
        raise RuntimeError(error_msg)

    if not dashboard_started:
        logger.warning("[WARNING] Dashboard failed to start - continuing without dashboard")
        logger.info("[INFO] You can start the dashboard manually by running: uv run streamlit run src/dashboard/main.py --server.port 8501")
        return False

    logger.info("[SUCCESS] Dashboard started successfully at http://localhost:8501")
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    global dashboard_manager, startup_timestamp

    # Startup
    try:
        # Record startup timestamp
        startup_timestamp = datetime.now()
        logger.info(f"API started at: {startup_timestamp}")

        # Load configuration first
        config = load_config()

        # Setup logging with config values
        logging_config = config.get("logging", {})
        log_level = logging_config.get("level", "INFO")
        setup_logging(log_level=log_level, log_file="trading_system.log", enable_file_logging=True)

        logger.info("Starting AutoTrader Pro API...")
        startup_config = config.get("startup", {})
        require_broker = startup_config.get("require_broker", True)
        require_dashboard = startup_config.get("require_dashboard", True)

        # Initialize components
        await _initialize_broker(require_broker)

        # Initialize dashboard manager
        dashboard_manager = DashboardManager(dashboard_port=8501, api_base_url="http://localhost:8080")
        await _initialize_dashboard(dashboard_manager, require_dashboard)

        logger.info("[SUCCESS] All required components started successfully")

        yield

    except Exception as e:
        logger.exception(f"[CRITICAL] Failed to start API: {e}")
        # Ensure we cleanup before re-raising
        if dashboard_manager:
            dashboard_manager.stop_dashboard()
        raise  # Re-raise the exception to stop the application

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
    debug=True,  # Enable debug mode for detailed error messages
)


# Global exception handler for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to catch and log all unhandled exceptions"""
    # Log the error with full context
    logger.error(f"UNHANDLED EXCEPTION - {type(exc).__name__}: {exc}")
    logger.error(f"Request: {request.method} {request.url}")
    logger.error(f"Headers: {dict(request.headers)}")
    logger.error(f"Path params: {request.path_params}")
    logger.error(f"Query params: {dict(request.query_params)}")

    # Log full traceback
    import traceback

    logger.error(f"Traceback:\n{traceback.format_exc()}")

    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {type(exc).__name__}: {str(exc)}",
            "type": type(exc).__name__,
            "traceback": traceback.format_exc() if app.debug else "Enable debug mode for traceback",
        },
    )


# Custom HTTP exception handler to ensure all HTTP errors are logged
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler to log HTTP errors"""
    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code} ERROR: {exc.detail}")
        logger.error(f"Request: {request.method} {request.url}")
    elif exc.status_code >= 400:
        logger.warning(f"HTTP {exc.status_code} WARNING: {exc.detail}")
        logger.warning(f"Request: {request.method} {request.url}")

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers with /api prefix
app.include_router(core_router, prefix="/api")
app.include_router(trading_router, prefix="/api")
app.include_router(brokers_router, prefix="/api")


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    startup_timestamp: datetime | None = None
    broker_connected: bool
    active_broker: str | None = None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        broker_manager = get_broker_manager()
        active_broker_name = broker_manager.get_active_broker_name()
        broker_connected = broker_manager.active_broker is not None

        return HealthResponse(status="healthy", timestamp=datetime.now(), startup_timestamp=startup_timestamp, broker_connected=broker_connected, active_broker=active_broker_name)
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return HealthResponse(status="unhealthy", timestamp=datetime.now(), startup_timestamp=startup_timestamp, broker_connected=False, active_broker=None)


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

            // Auto-refresh every 10 seconds for faster API restart detection
            setInterval(() => {
                loadSystemStatus();
                loadBrokerStatus();
            }, 10000);
        </script>
    </body>
    </html>
    """
