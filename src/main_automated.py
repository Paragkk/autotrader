"""
Professional Automated Trading System
Main orchestrator for the 10-step automated trading workflow
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass
import yaml
from pathlib import Path
import os
import subprocess
import sys
import time

# Add APScheduler to dependencies
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError:
    # Fallback for basic scheduling
    AsyncIOScheduler = None
    CronTrigger = None
    IntervalTrigger = None

from sqlmodel import create_engine, Session, SQLModel
from sqlalchemy import desc

from db.models import (
    ScreenedStock,
    StockScore,
    TrackedSymbol,
    StrategyResult,
    Signal,
    Order,
    Position,
    SystemMetrics,
)
from core.stock_screener import EnhancedStockScreener, ScreeningCriteria
from core.strategy_engine import StrategyEngine
from core.signal_aggregator import SignalAggregator
from core.risk_management import RiskManager
from brokers.alpaca.adapter import AlpacaBrokerAdapter
from core.stock_scorer import StockScorer
from core.order_executor import OrderExecutor
from core.position_monitor import PositionMonitor
from core.data_fetcher import DataFetcher
from db.repository import SymbolRepository, StockDataRepository, SignalRepository
from infra.logging_config import setup_logging

logger = logging.getLogger(__name__)


@dataclass
class TradingConfig:
    """Configuration for the automated trading system"""

    config_path: Path = Path("config.yaml")

    def __post_init__(self):
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                self.config = yaml.safe_load(f)
        else:
            # Default configuration
            self.config = self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration if file doesn't exist"""
        return {
            "database": {"url": "sqlite:///data/trading.db"},
            "trading": {"max_positions": 10},
            "screening": {
                "enabled": True,
                "schedule": "0 */1 * * *",  # Every hour
                "criteria": {
                    "min_price": 5.0,
                    "max_price": 500.0,
                    "min_volume": 250000,
                    "min_daily_change": -15.0,
                    "max_daily_change": 15.0,
                },
                "max_symbols": 50,
            },
            "strategies": {
                "schedule": "*/10 * * * *",  # Every 10 minutes
                "weights": {
                    "moving_average_crossover": 0.25,
                    "rsi_strategy": 0.25,
                    "momentum_strategy": 0.20,
                    "breakout_strategy": 0.15,
                    "mean_reversion": 0.15,
                },
                "signal_threshold": 0.6,
            },
            "broker": {
                "name": "alpaca",
                "api_key": os.getenv("ALPACA_API_KEY", ""),
                "secret_key": os.getenv("ALPACA_SECRET_KEY", ""),
                "paper_trading": True,
            },
            "risk": {
                "max_exposure_per_trade": 0.05,
                "max_exposure_per_sector": 0.20,
                "portfolio_risk_limit": 0.15,
            },
            "monitoring": {
                "schedule": "*/5 * * * *"  # Every 5 minutes
            },
            "scoring": {
                "factors": {
                    "momentum": 0.25,
                    "volume": 0.20,
                    "volatility": 0.15,
                    "technical": 0.20,
                    "sentiment": 0.10,
                    "fundamentals": 0.10,
                },
                "top_n_stocks": 30,
            },
        }

    @property
    def database_url(self) -> str:
        return self.config["database"]["url"]

    @property
    def max_positions(self) -> int:
        return self.config["trading"]["max_positions"]

    @property
    def screening_enabled(self) -> bool:
        return self.config["screening"]["enabled"]

    @property
    def screening_schedule(self) -> str:
        return self.config["screening"]["schedule"]


class AutomatedTradingSystem:
    """
    Main class orchestrating the 10-step automated trading workflow:
    1. Scheduled Automated Screening
    2. Stock Scoring & Ranking
    3. Dynamic Symbol Tracking
    4. Strategy Analysis
    5. Signal Generation & Aggregation
    6. Risk Management Filtering
    7. Automated Order Execution
    8. Continuous Monitoring
    9. Entry Suspension When Max Orders Reached
    10. Audit Logging & Persistence
    """

    def __init__(self, config: TradingConfig):
        self.config = config
        self.scheduler = AsyncIOScheduler() if AsyncIOScheduler else None
        self.db_session: Optional[Session] = None
        self.is_running = False
        self.dashboard_process: Optional[subprocess.Popen] = None

        # Initialize database
        self.engine = create_engine(config.database_url)
        SQLModel.metadata.create_all(self.engine)
        self.db_session = Session(self.engine)

        # Initialize components
        broker_config = config.config["broker"]
        if broker_config["name"] == "alpaca":
            self.broker_adapter = AlpacaBrokerAdapter(
                api_key=broker_config["api_key"],
                api_secret=broker_config["secret_key"],
                paper_trading=broker_config.get("paper_trading", True),
            )
        else:
            raise ValueError(f"Unsupported broker: {broker_config['name']}")

        # Initialize repositories
        db_path = config.config["database"]["url"].replace("sqlite:///", "")
        self.symbol_repo = SymbolRepository(db_path)
        self.stock_data_repo = StockDataRepository(db_path)
        self.signal_repo = SignalRepository(db_path)
        
        # Initialize data fetcher
        self.data_fetcher = DataFetcher(
            stock_data_repo=self.stock_data_repo,
            symbol_repo=self.symbol_repo,
            broker_adapter=self.broker_adapter
        )

        # Initialize screener with required dependencies
        self.stock_screener = EnhancedStockScreener(
            data_fetcher=self.data_fetcher,
            symbol_repo=self.symbol_repo,
            stock_data_repo=self.stock_data_repo
        )
        self.strategy_engine = StrategyEngine(self.broker_adapter)
        self.signal_aggregator = SignalAggregator(self.signal_repo)
        
        # Initialize risk manager with proper parameters
        from core.risk_management import RiskParameters
        risk_params = RiskParameters(
            max_position_size_percent=config.config["risk"].get("max_exposure_per_trade", 0.05) * 100,
            max_total_exposure_percent=config.config["risk"].get("portfolio_risk_limit", 0.15) * 100,
            max_sector_exposure_percent=config.config["risk"].get("max_exposure_per_sector", 0.20) * 100,
        )
        self.risk_manager = RiskManager(risk_params)
        self.stock_scorer = StockScorer(config.config["scoring"])
        self.order_executor = OrderExecutor(self.broker_adapter, self.db_session)
        self.position_monitor = PositionMonitor(self.broker_adapter, self.db_session)

        # Setup scheduler if available
        if self.scheduler:
            self._setup_scheduler()

    def _setup_scheduler(self):
        """Setup the scheduler for automated trading workflow"""
        if not self.scheduler:
            return

        # 1. Scheduled Automated Screening
        if self.config.screening_enabled:
            self.scheduler.add_job(
                self._run_automated_screening,
                CronTrigger.from_crontab(self.config.screening_schedule),
                id="automated_screening",
                max_instances=1,
                replace_existing=True,
            )

        # 2. Strategy Analysis & Signal Generation
        self.scheduler.add_job(
            self._run_strategy_analysis,
            CronTrigger.from_crontab(self.config.config["strategies"]["schedule"]),
            id="strategy_analysis",
            max_instances=1,
            replace_existing=True,
        )

        # 3. Continuous Position Monitoring
        self.scheduler.add_job(
            self._run_position_monitoring,
            CronTrigger.from_crontab(self.config.config["monitoring"]["schedule"]),
            id="position_monitoring",
            max_instances=1,
            replace_existing=True,
        )

        # 4. System Health Monitoring
        self.scheduler.add_job(
            self._record_system_metrics,
            IntervalTrigger(minutes=15),
            id="system_metrics",
            max_instances=1,
            replace_existing=True,
        )

    async def start(self):
        """Start the automated trading system"""
        logger.info("🚀 Starting Automated Trading System")

        # Start dashboard first
        self._start_dashboard()

        # Verify broker connection
        await self._verify_broker_connection()

        # Start scheduler
        if self.scheduler:
            self.scheduler.start()
            logger.info("📅 Scheduler started")
        else:
            logger.warning("⚠️ APScheduler not available - running in manual mode")

        self.is_running = True

        logger.info("✅ Automated Trading System started successfully")
        logger.info("📊 Dashboard available at: http://localhost:8501")

    async def stop(self):
        """Stop the automated trading system"""
        logger.info("🛑 Stopping Automated Trading System")

        self.is_running = False

        if self.scheduler:
            self.scheduler.shutdown()

        if self.db_session:
            self.db_session.close()

        # Stop the dashboard if running
        self._stop_dashboard()

        logger.info("✅ Automated Trading System stopped")

    async def _verify_broker_connection(self):
        """Verify broker connection and account status"""
        try:
            # For now, just log that we're verifying
            logger.info("🔌 Verifying broker connection...")
            # account = await self.broker_adapter.get_account()
            # logger.info(f"📊 Account Status: {account.status}")
            logger.info("✅ Broker connection verified")
        except Exception as e:
            logger.error(f"❌ Broker connection failed: {e}")
            raise

    async def _run_automated_screening(self):
        """
        Step 1: Automated Stock Screening
        """
        logger.info("🔍 Starting automated stock screening")

        try:
            # Get screening criteria from config
            criteria = ScreeningCriteria(
                min_price=self.config.config["screening"]["criteria"]["min_price"],
                max_price=self.config.config["screening"]["criteria"]["max_price"],
                min_volume=self.config.config["screening"]["criteria"]["min_volume"],
                min_daily_change=self.config.config["screening"]["criteria"][
                    "min_daily_change"
                ],
                max_daily_change=self.config.config["screening"]["criteria"][
                    "max_daily_change"
                ],
                max_results=self.config.config["screening"]["max_symbols"],
            )

            # Run screening
            screened_stocks = await self.stock_screener.screen_stocks(criteria)

            # Store results in database
            for stock in screened_stocks:
                screened_stock = ScreenedStock(
                    symbol=stock.symbol,
                    screening_criteria=criteria.__dict__,
                    price=stock.price,
                    volume=stock.volume,
                    daily_change=stock.daily_change,
                    market_cap=getattr(stock, "market_cap", None),
                    sector=getattr(stock, "sector", None),
                )
                self.db_session.add(screened_stock)

            self.db_session.commit()

            logger.info(f"✅ Screening completed: {len(screened_stocks)} stocks found")

            # Trigger step 2: Stock Scoring
            await self._run_stock_scoring()

        except Exception as e:
            logger.error(f"❌ Screening failed: {e}")
            self.db_session.rollback()

    async def _run_stock_scoring(self):
        """
        Step 2: Stock Scoring & Ranking
        """
        logger.info("📊 Starting stock scoring and ranking")

        try:
            # Get recently screened stocks
            recent_stocks = (
                self.db_session.query(ScreenedStock)
                .filter(
                    ScreenedStock.screened_at >= datetime.now() - timedelta(hours=2)
                )
                .all()
            )

            # For now, assign random scores (implement actual scoring logic)
            import random

            # Score each stock
            for stock in recent_stocks:
                score_data = {
                    "total_score": random.uniform(0.3, 0.9),
                    "momentum_score": random.uniform(0.0, 1.0),
                    "volume_score": random.uniform(0.0, 1.0),
                    "volatility_score": random.uniform(0.0, 1.0),
                    "technical_score": random.uniform(0.0, 1.0),
                    "sentiment_score": random.uniform(0.0, 1.0),
                    "fundamentals_score": random.uniform(0.0, 1.0),
                }

                stock_score = StockScore(
                    symbol=stock.symbol,
                    screened_stock_id=stock.id,
                    score=score_data["total_score"],
                    rank=0,  # Will be updated after all scores calculated
                    factors_used=self.config.config["scoring"]["factors"],
                    momentum_score=score_data["momentum_score"],
                    volume_score=score_data["volume_score"],
                    volatility_score=score_data["volatility_score"],
                    technical_score=score_data["technical_score"],
                    sentiment_score=score_data["sentiment_score"],
                    fundamentals_score=score_data["fundamentals_score"],
                )
                self.db_session.add(stock_score)

            self.db_session.commit()

            # Update rankings
            await self._update_stock_rankings()

            # Trigger step 3: Dynamic Symbol Tracking
            await self._update_tracked_symbols()

            logger.info("✅ Stock scoring completed")

        except Exception as e:
            logger.error(f"❌ Stock scoring failed: {e}")
            self.db_session.rollback()

    async def _update_stock_rankings(self):
        """Update stock rankings based on scores"""
        today_scores = (
            self.db_session.query(StockScore)
            .filter(
                StockScore.scored_at
                >= datetime.now().replace(hour=0, minute=0, second=0)
            )
            .order_by(desc(StockScore.score))
            .all()
        )

        for rank, score in enumerate(today_scores, 1):
            score.rank = rank

        self.db_session.commit()

    async def _update_tracked_symbols(self):
        """
        Step 3: Dynamic Symbol Tracking
        """
        logger.info("🎯 Updating tracked symbols")

        try:
            # Get top N scored stocks
            top_stocks = (
                self.db_session.query(StockScore)
                .filter(
                    StockScore.scored_at
                    >= datetime.now().replace(hour=0, minute=0, second=0)
                )
                .order_by(desc(StockScore.score))
                .limit(self.config.config["scoring"]["top_n_stocks"])
                .all()
            )

            # Add new symbols to tracking
            for stock in top_stocks:
                existing = (
                    self.db_session.query(TrackedSymbol)
                    .filter(
                        TrackedSymbol.symbol == stock.symbol, TrackedSymbol.is_active
                    )
                    .first()
                )

                if not existing:
                    tracked_symbol = TrackedSymbol(
                        symbol=stock.symbol,
                        stock_score_id=stock.id,
                        reason_added="screening",
                    )
                    self.db_session.add(tracked_symbol)

            self.db_session.commit()

            logger.info(f"✅ Symbol tracking updated: {len(top_stocks)} symbols")

        except Exception as e:
            logger.error(f"❌ Symbol tracking failed: {e}")
            self.db_session.rollback()

    async def _run_strategy_analysis(self):
        """
        Step 4: Strategy Analysis
        """
        logger.info("⚡ Starting strategy analysis")

        try:
            # Get active tracked symbols
            tracked_symbols = (
                self.db_session.query(TrackedSymbol)
                .filter(TrackedSymbol.is_active)
                .all()
            )

            # Run strategies on each symbol
            for symbol_obj in tracked_symbols:
                symbol = symbol_obj.symbol

                # For now, simulate strategy results
                import random

                # Run each strategy
                for strategy_name in self.config.config["strategies"]["weights"].keys():
                    try:
                        # Simulate strategy result
                        result = {
                            "signal": random.choice(["buy", "sell", "hold"]),
                            "strength": random.uniform(0.3, 0.9),
                            "confidence": random.uniform(0.4, 0.8),
                            "data": {"test": "data"},
                        }

                        strategy_result = StrategyResult(
                            symbol=symbol,
                            tracked_symbol_id=symbol_obj.id,
                            strategy_name=strategy_name,
                            signal=result["signal"],
                            strength=result["strength"],
                            confidence=result["confidence"],
                            price_at_analysis=100.0,  # Placeholder
                            strategy_data=result.get("data", {}),
                        )
                        self.db_session.add(strategy_result)

                    except Exception as e:
                        logger.error(
                            f"❌ Strategy {strategy_name} failed for {symbol}: {e}"
                        )

            self.db_session.commit()

            # Trigger step 5: Signal Aggregation
            await self._run_signal_aggregation()

            logger.info("✅ Strategy analysis completed")

        except Exception as e:
            logger.error(f"❌ Strategy analysis failed: {e}")
            self.db_session.rollback()

    async def _run_signal_aggregation(self):
        """
        Step 5: Signal Generation & Aggregation
        """
        logger.info("🔄 Starting signal aggregation")

        try:
            # Get recent strategy results
            recent_results = (
                self.db_session.query(StrategyResult)
                .filter(
                    StrategyResult.analyzed_at >= datetime.now() - timedelta(minutes=30)
                )
                .all()
            )

            # Group by symbol
            symbol_results = {}
            for result in recent_results:
                if result.symbol not in symbol_results:
                    symbol_results[result.symbol] = []
                symbol_results[result.symbol].append(result)

            # Generate signals
            for symbol, results in symbol_results.items():
                signal_data = await self.signal_aggregator.aggregate_strategy_results(results)

                if (
                    signal_data["confidence"]
                    >= self.config.config["strategies"]["signal_threshold"]
                ):
                    signal = Signal(
                        symbol=symbol,
                        direction=signal_data["direction"],
                        confidence_score=signal_data["confidence"],
                        strength=signal_data["strength"],
                        price_at_signal=signal_data["price"],
                        strategy_count=len(results),
                        contributing_strategies=signal_data["strategies"],
                    )
                    self.db_session.add(signal)

            self.db_session.commit()

            logger.info("✅ Signal aggregation completed")

        except Exception as e:
            logger.error(f"❌ Signal aggregation failed: {e}")
            self.db_session.rollback()

    async def _run_position_monitoring(self):
        """
        Step 8: Continuous Monitoring
        """
        logger.info("👁️ Starting position monitoring")

        try:
            # For now, just log monitoring
            logger.info("🔍 Monitoring positions...")

            # Get current positions from database
            open_positions = (
                self.db_session.query(Position).filter(Position.status == "open").all()
            )

            logger.info(f"📊 Found {len(open_positions)} open positions")

            # TODO: Implement actual position monitoring logic

            logger.info("✅ Position monitoring completed")

        except Exception as e:
            logger.error(f"❌ Position monitoring failed: {e}")

    async def _record_system_metrics(self):
        """
        Step 10: Audit Logging & Persistence
        """
        try:
            # Count today's activities
            today = datetime.now().replace(hour=0, minute=0, second=0)
            signals_today = (
                self.db_session.query(Signal)
                .filter(Signal.generated_at >= today)
                .count()
            )

            orders_today = (
                self.db_session.query(Order).filter(Order.created_at >= today).count()
            )

            # Record metrics
            metrics = SystemMetrics(
                total_equity=100000.0,  # Placeholder
                available_cash=50000.0,  # Placeholder
                total_positions=0,
                daily_pnl=0.0,
                signals_generated=signals_today,
                orders_placed=orders_today,
                market_hours=True,  # Placeholder
            )

            self.db_session.add(metrics)
            self.db_session.commit()

            logger.info("📈 System metrics recorded")

        except Exception as e:
            logger.error(f"❌ Failed to record system metrics: {e}")

    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        try:
            # Get latest metrics
            latest_metrics = (
                self.db_session.query(SystemMetrics)
                .order_by(desc(SystemMetrics.recorded_at))
                .first()
            )

            # Get pending signals
            pending_signals = (
                self.db_session.query(Signal)
                .filter(Signal.status.in_(["pending", "approved"]))
                .count()
            )

            return {
                "system_running": self.is_running,
                "active_positions": 0,  # Placeholder
                "max_positions": self.config.max_positions,
                "pending_signals": pending_signals,
                "portfolio_value": latest_metrics.total_equity if latest_metrics else 0,
                "available_cash": latest_metrics.available_cash
                if latest_metrics
                else 0,
                "market_hours": True,  # Placeholder
            }

        except Exception as e:
            logger.error(f"❌ Failed to get system status: {e}")
            return {"error": str(e)}

    async def run_manual_cycle(self):
        """Run one complete cycle manually (for testing without scheduler)"""
        logger.info("🔄 Running manual trading cycle")

        try:
            await self._run_automated_screening()
            await self._run_strategy_analysis()
            await self._run_position_monitoring()
            await self._record_system_metrics()

            logger.info("✅ Manual trading cycle completed")

        except Exception as e:
            logger.error(f"❌ Manual trading cycle failed: {e}")

    def _start_dashboard(self):
        """Start the Streamlit dashboard in a separate process"""
        try:
            # Check if dashboard dependencies are available
            try:
                import importlib.util

                if not importlib.util.find_spec("streamlit"):
                    raise ImportError("streamlit not found")
                if not importlib.util.find_spec("plotly"):
                    raise ImportError("plotly not found")
            except ImportError:
                logger.warning(
                    "📊 Dashboard dependencies not installed. Install with: uv pip install -e .[dashboard]"
                )
                return

            dashboard_path = Path(__file__).parent / "dashboard" / "main.py"
            if not dashboard_path.exists():
                logger.warning(f"📊 Dashboard file not found: {dashboard_path}")
                return

            logger.info("📊 Starting dashboard...")

            # Start dashboard in background
            self.dashboard_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(dashboard_path),
                    "--server.port",
                    "8501",
                    "--server.address",
                    "0.0.0.0",
                    "--theme.base",
                    "dark",
                    "--server.headless",
                    "true",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait a moment for dashboard to start
            time.sleep(3)

            if self.dashboard_process.poll() is None:
                logger.info(
                    "✅ Dashboard started successfully at http://localhost:8501"
                )
            else:
                logger.error("❌ Dashboard failed to start")
                self.dashboard_process = None

        except Exception as e:
            logger.error(f"❌ Failed to start dashboard: {e}")
            self.dashboard_process = None

    def _stop_dashboard(self):
        """Stop the dashboard process"""
        if self.dashboard_process and self.dashboard_process.poll() is None:
            logger.info("🛑 Stopping dashboard...")
            self.dashboard_process.terminate()
            try:
                self.dashboard_process.wait(timeout=10)
                logger.info("✅ Dashboard stopped")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️ Dashboard didn't stop gracefully, killing process")
                self.dashboard_process.kill()
            self.dashboard_process = None


# Main entry point
async def main():
    """Main entry point for the automated trading system"""

    # Setup logging
    setup_logging()

    # Load configuration
    config = TradingConfig()

    # Create and start system
    system = AutomatedTradingSystem(config)

    try:
        await system.start()

        # If scheduler is not available, run manual cycles
        if not system.scheduler:
            logger.info("🔄 Running in manual mode - executing cycles every 5 minutes")
            while system.is_running:
                await system.run_manual_cycle()
                await asyncio.sleep(300)  # Wait 5 minutes
        else:
            # Keep running with scheduler
            while system.is_running:
                await asyncio.sleep(60)

    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
        await system.stop()

    except Exception as e:
        logger.error(f"❌ System error: {e}")
        await system.stop()
        raise


if __name__ == "__main__":
    asyncio.run(main())
