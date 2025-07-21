"""
Advanced Trading Orchestrator - Integrates all trading components
"""

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from src.db.repository import (
    SignalRepository,
    SQLiteRepository,
    StockDataRepository,
    SymbolRepository,
)
from src.infra.config import create_broker_adapter

from .data_fetcher import DataFetcher
from .news_analyzer import NewsAnalyzer
from .price_forecaster import PriceForecaster
from .risk_management import RiskManager
from .signal_aggregator import SignalAggregator
from .stock_screener import EnhancedStockScreener, ScreeningCriteria
from .strategy_engine import StrategyEngine

logger = logging.getLogger(__name__)


@dataclass
class TradingConfig:
    """Configuration for trading orchestrator"""

    # Broker Configuration
    broker_name: str = "alpaca"  # Support for multiple brokers
    broker_config: dict[str, Any] = field(default_factory=dict)

    # Trading Parameters
    max_positions: int = 10
    max_daily_loss: float = 1000.0
    position_size_percent: float = 0.02  # 2% of portfolio per position

    # Data Configuration
    symbols_to_track: list[str] = field(
        default_factory=lambda: [
            "AAPL",
            "GOOGL",
            "MSFT",
            "AMZN",
            "TSLA",
            "META",
            "NVDA",
            "NFLX",
            "SPY",
            "QQQ",
        ]
    )

    # Stock Screening Configuration
    enable_automated_screening: bool = True
    screening_interval_minutes: int = 60  # Screen every hour
    max_screened_symbols: int = 50
    screening_criteria: dict[str, Any] = field(
        default_factory=lambda: {
            "min_price": 5.0,
            "max_price": 1000.0,
            "min_volume": 100000,
            "min_daily_change": -20.0,
            "max_daily_change": 20.0,
            "max_results": 50,
            "exclude_penny_stocks": True,
        }
    )

    # Strategy Configuration
    strategy_weights: dict[str, float] = field(
        default_factory=lambda: {
            "moving_average_crossover": 0.3,
            "rsi_strategy": 0.3,
            "momentum_strategy": 0.2,
            "news_sentiment": 0.1,
            "price_forecast": 0.1,
        }
    )

    # Risk Management Configuration
    stop_loss_percent: float = 0.02  # 2% stop loss
    take_profit_percent: float = 0.06  # 6% take profit

    # Data Update Intervals
    market_data_update_interval: int = 300  # 5 minutes
    news_update_interval: int = 1800  # 30 minutes
    strategy_evaluation_interval: int = 600  # 10 minutes
    screening_update_interval: int = 3600  # 1 hour for screening


class TradingOrchestrator:
    """
    Main orchestrator that coordinates all trading components
    """

    def __init__(self, config: TradingConfig) -> None:
        self.config = config
        self.is_running = False
        self.last_data_update = None
        self.last_news_update = None
        self.last_strategy_evaluation = None
        self.last_screening_update = None
        self.screening_task = None

        # Initialize components
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize all trading components"""
        try:
            # Initialize broker using config
            self.broker_adapter = create_broker_adapter(broker_name=self.config.broker_name, config=self.config.broker_config)

            # Initialize repositories
            self.db_repo = SQLiteRepository("trading.db")
            self.stock_data_repo = StockDataRepository(self.db_repo)
            self.symbol_repo = SymbolRepository(self.db_repo)
            self.signal_repo = SignalRepository(self.db_repo)

            # Initialize data fetcher
            self.data_fetcher = DataFetcher(
                stock_data_repo=self.stock_data_repo,
                symbol_repo=self.symbol_repo,
                broker_adapter=self.broker_adapter,
            )

            # Initialize strategy engine
            self.strategy_engine = StrategyEngine(data_fetcher=self.data_fetcher, signal_repo=self.signal_repo)

            # Initialize signal aggregator
            self.signal_aggregator = SignalAggregator(
                signal_repo=self.signal_repo,
                strategy_weights=self.config.strategy_weights,
            )

            # Initialize risk manager
            self.risk_manager = RiskManager(
                broker_adapter=self.broker_adapter,
                max_positions=self.config.max_positions,
                max_daily_loss=self.config.max_daily_loss,
                position_size_percent=self.config.position_size_percent,
            )

            # Initialize news analyzer
            self.news_analyzer = NewsAnalyzer(self.broker_adapter)

            # Initialize price forecaster
            self.price_forecaster = PriceForecaster(self.broker_adapter)

            # Initialize enhanced stock screener
            self.stock_screener = EnhancedStockScreener(
                data_fetcher=self.data_fetcher,
                symbol_repo=self.symbol_repo,
                stock_data_repo=self.stock_data_repo,
            )

            logger.info("Trading orchestrator initialized successfully")

        except Exception as e:
            logger.exception(f"Failed to initialize trading orchestrator: {e}")
            raise

    async def start(self) -> None:
        """Start the trading orchestrator"""
        if self.is_running:
            logger.warning("Trading orchestrator is already running")
            return

        self.is_running = True
        logger.info("Starting trading orchestrator...")

        try:
            # Initialize data
            await self._initialize_data()

            # Start automated screening if enabled
            if self.config.enable_automated_screening:
                await self._start_automated_screening()

            # Start main trading loop
            await self._main_trading_loop()

        except Exception as e:
            logger.exception(f"Error in trading orchestrator: {e}")
            raise
        finally:
            self.is_running = False
            logger.info("Trading orchestrator stopped")

    async def stop(self) -> None:
        """Stop the trading orchestrator"""
        self.is_running = False

        # Stop automated screening
        if self.screening_task:
            self.screening_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.screening_task

        logger.info("Stopping trading orchestrator...")

    async def _initialize_data(self) -> None:
        """Initialize required data for trading"""
        try:
            # Fetch initial symbol list
            logger.info("Fetching symbol list...")

            # Fetch historical data for tracked symbols
            logger.info("Fetching historical data...")
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)  # 1 year of data

            for symbol in self.config.symbols_to_track:
                try:
                    self.data_fetcher.fetch_daily_data(
                        symbol=symbol,
                        start_date=str(start_date),
                        end_date=str(end_date),
                    )
                except Exception as e:
                    logger.warning(f"Failed to fetch data for {symbol}: {e}")

            logger.info("Data initialization completed")

        except Exception as e:
            logger.exception(f"Failed to initialize data: {e}")
            raise

    async def _main_trading_loop(self) -> None:
        """Main trading loop"""
        logger.info("Starting main trading loop...")

        while self.is_running:
            try:
                current_time = datetime.now()

                # Check if market is open
                if not await self._is_market_open():
                    logger.debug("Market is closed, sleeping...")
                    await asyncio.sleep(60)  # Check every minute
                    continue

                # Update market data
                if self._should_update_data(current_time):
                    await self._update_market_data()
                    self.last_data_update = current_time

                # Update news data
                if self._should_update_news(current_time):
                    await self._update_news_data()
                    self.last_news_update = current_time

                # Update screening data
                if self.config.enable_automated_screening and self._should_update_screening(current_time):
                    await self._update_screening_data()
                    self.last_screening_update = current_time

                # Evaluate strategies and generate signals
                if self._should_evaluate_strategies(current_time):
                    await self._evaluate_strategies()
                    self.last_strategy_evaluation = current_time

                # Update screening data and tracked symbols
                if self.config.enable_automated_screening and self._should_update_screening(current_time):
                    await self._update_screening_data()

                # Execute trades based on signals
                await self._execute_trades()

                # Sleep before next iteration
                await asyncio.sleep(30)  # 30 second intervals

            except Exception as e:
                logger.exception(f"Error in main trading loop: {e}")
                await asyncio.sleep(60)  # Sleep longer on error

    async def _is_market_open(self) -> bool:
        """Check if market is currently open"""
        try:
            clock = self.alpaca_client.trading.market.clock()
            return clock.is_open
        except Exception as e:
            logger.warning(f"Failed to check market status: {e}")
            return False

    def _should_update_data(self, current_time: datetime) -> bool:
        """Check if market data should be updated"""
        if self.last_data_update is None:
            return True

        time_diff = current_time - self.last_data_update
        return time_diff.total_seconds() >= self.config.market_data_update_interval

    def _should_update_news(self, current_time: datetime) -> bool:
        """Check if news data should be updated"""
        if self.last_news_update is None:
            return True

        time_diff = current_time - self.last_news_update
        return time_diff.total_seconds() >= self.config.news_update_interval

    def _should_evaluate_strategies(self, current_time: datetime) -> bool:
        """Check if strategies should be evaluated"""
        if self.last_strategy_evaluation is None:
            return True

        time_diff = current_time - self.last_strategy_evaluation
        return time_diff.total_seconds() >= self.config.strategy_evaluation_interval

    def _should_update_screening(self, current_time: datetime) -> bool:
        """Check if screening should be updated"""
        if self.last_screening_update is None:
            return True

        time_diff = current_time - self.last_screening_update
        return time_diff.total_seconds() >= self.config.screening_update_interval

    async def _update_market_data(self) -> None:
        """Update market data for tracked symbols"""
        try:
            logger.info("Updating market data...")

            # Update incremental data
            results = self.data_fetcher.fetch_incremental_data(symbols=self.config.symbols_to_track, days_back=1)

            logger.info(f"Updated data for {len(results)} symbols")

        except Exception as e:
            logger.exception(f"Failed to update market data: {e}")

    async def _update_news_data(self) -> None:
        """Update news data for tracked symbols"""
        try:
            logger.info("Updating news data...")

            # Fetch news for tracked symbols
            news_articles = self.data_fetcher.fetch_market_news(symbols=self.config.symbols_to_track, limit=50)

            # Analyze news sentiment
            for symbol in self.config.symbols_to_track:
                symbol_news = [n for n in news_articles if n["symbol"] == symbol]
                if symbol_news:
                    sentiment_analysis = self.news_analyzer.analyze_news_sentiment(symbol_news)

                    # Generate news-based signals
                    news_signals = self.news_analyzer.generate_news_signals(
                        symbol=symbol,
                        news_articles=symbol_news,
                        sentiment_analysis=sentiment_analysis,
                    )

                    # Store signals
                    for signal in news_signals:
                        self.signal_repo.add_signal(signal)

            logger.info("News data updated successfully")

        except Exception as e:
            logger.exception(f"Failed to update news data: {e}")

    async def _evaluate_strategies(self) -> None:
        """Evaluate all strategies and generate signals"""
        try:
            logger.info("Evaluating strategies...")

            for symbol in self.config.symbols_to_track:
                # Run traditional strategies
                self.strategy_engine.evaluate_symbol(symbol)

                # Generate price forecasts
                try:
                    # Get historical data
                    end_date = datetime.now().date()
                    start_date = end_date - timedelta(days=90)

                    data = self.data_fetcher.get_cached_data(
                        symbol=symbol,
                        start_date=str(start_date),
                        end_date=str(end_date),
                    )

                    if len(data) > 30:  # Need sufficient data for forecasting
                        forecasts = self.price_forecaster.forecast_prices(symbol=symbol, data=data, days_ahead=5)

                        # Generate forecast-based signals
                        forecast_signals = self.price_forecaster.generate_forecast_signals(
                            symbol=symbol,
                            forecasts=forecasts,
                            current_price=data["close"].iloc[-1],
                        )

                        # Store signals
                        for signal in forecast_signals:
                            self.signal_repo.add_signal(signal)

                except Exception as e:
                    logger.warning(f"Failed to generate forecasts for {symbol}: {e}")

            logger.info("Strategy evaluation completed")

        except Exception as e:
            logger.exception(f"Failed to evaluate strategies: {e}")

    async def _execute_trades(self) -> None:
        """Execute trades based on aggregated signals"""
        try:
            logger.info("Executing trades...")

            # Get current positions
            current_positions = self.broker_adapter.get_positions()
            current_symbols = {pos.symbol for pos in current_positions}

            # Process each tracked symbol
            for symbol in self.config.symbols_to_track:
                # Get aggregated signal
                aggregated_signal = self.signal_aggregator.aggregate_signals(symbol=symbol, lookback_hours=1)

                if aggregated_signal is None:
                    continue

                # Check risk management
                risk_check = self.risk_manager.check_trade_risk(
                    symbol=symbol,
                    side=aggregated_signal.signal_type,
                    quantity=aggregated_signal.strength * 100,  # Convert to shares
                )

                if not risk_check.approved:
                    logger.warning(f"Trade for {symbol} rejected by risk management: {risk_check.reason}")
                    continue

                # Execute trade based on signal
                if aggregated_signal.signal_type == "BUY" and symbol not in current_symbols:
                    await self._execute_buy_order(symbol, aggregated_signal)
                elif aggregated_signal.signal_type == "SELL" and symbol in current_symbols:
                    await self._execute_sell_order(symbol, aggregated_signal)

            logger.info("Trade execution completed")

        except Exception as e:
            logger.exception(f"Failed to execute trades: {e}")

    async def _execute_buy_order(self, symbol: str, signal) -> None:
        """Execute a buy order"""
        try:
            # Calculate position size
            account_info = self.broker_adapter.get_account_info()
            position_value = account_info.buying_power * self.config.position_size_percent

            # Get current price
            current_price = self._get_current_price(symbol)
            if current_price is None:
                logger.warning(f"Unable to get current price for {symbol}")
                return

            quantity = int(position_value / current_price)

            if quantity <= 0:
                logger.warning(f"Invalid quantity for {symbol}: {quantity}")
                return

            # Calculate stop loss and take profit
            stop_loss_price = current_price * (1 - self.config.stop_loss_percent)
            take_profit_price = current_price * (1 + self.config.take_profit_percent)

            # Submit order
            from .broker_adapter import OrderRequest

            order_request = OrderRequest(
                symbol=symbol,
                quantity=quantity,
                side="buy",
                order_type="market",
                stop_loss=stop_loss_price,
                take_profit=take_profit_price,
            )

            order_response = self.broker_adapter.submit_order(order_request)
            logger.info(f"Buy order submitted for {symbol}: {order_response.order_id}")

        except Exception as e:
            logger.exception(f"Failed to execute buy order for {symbol}: {e}")

    async def _execute_sell_order(self, symbol: str, signal) -> None:
        """Execute a sell order"""
        try:
            # Get current position
            positions = self.broker_adapter.get_positions()
            position = next((p for p in positions if p.symbol == symbol), None)

            if position is None:
                logger.warning(f"No position found for {symbol}")
                return

            # Submit sell order
            from .broker_adapter import OrderRequest

            order_request = OrderRequest(
                symbol=symbol,
                quantity=abs(position.quantity),
                side="sell",
                order_type="market",
            )

            order_response = self.broker_adapter.submit_order(order_request)
            logger.info(f"Sell order submitted for {symbol}: {order_response.order_id}")

        except Exception as e:
            logger.exception(f"Failed to execute sell order for {symbol}: {e}")

    async def _start_automated_screening(self) -> None:
        """Start automated stock screening"""
        logger.info("Starting automated stock screening...")

        # Create screening criteria from config
        screening_criteria = ScreeningCriteria(
            min_price=self.config.screening_criteria.get("min_price", 5.0),
            max_price=self.config.screening_criteria.get("max_price", 1000.0),
            min_volume=self.config.screening_criteria.get("min_volume", 100000),
            min_daily_change=self.config.screening_criteria.get("min_daily_change", -20.0),
            max_daily_change=self.config.screening_criteria.get("max_daily_change", 20.0),
            max_results=self.config.screening_criteria.get("max_results", 50),
            exclude_penny_stocks=self.config.screening_criteria.get("exclude_penny_stocks", True),
        )

        # Start screening task
        self.screening_task = asyncio.create_task(
            self.stock_screener.run_automated_screening(
                criteria=screening_criteria,
                interval_minutes=self.config.screening_interval_minutes,
            )
        )

        logger.info("Automated screening started")

    async def _update_tracked_symbols(self) -> None:
        """Update tracked symbols from screening results"""
        try:
            # Get symbols from screener
            screened_symbols = self.stock_screener.get_tracked_symbols()

            # Combine with original symbols
            all_symbols = set(self.config.symbols_to_track)
            all_symbols.update(screened_symbols)

            # Limit to maximum number of symbols
            if len(all_symbols) > self.config.max_screened_symbols:
                # Keep top scored symbols from screening
                screening_results = self.stock_screener.get_screening_results()
                top_symbols = sorted(
                    screening_results.items(),
                    key=lambda x: x[1].score if x[1] else 0,
                    reverse=True,
                )[: self.config.max_screened_symbols - len(self.config.symbols_to_track)]

                screened_symbols = {item[0] for item in top_symbols}
                all_symbols = set(self.config.symbols_to_track)
                all_symbols.update(screened_symbols)

            # Update the symbols to track
            self.config.symbols_to_track = list(all_symbols)

            logger.info(f"Updated tracked symbols: {len(self.config.symbols_to_track)} total symbols")

        except Exception as e:
            logger.exception(f"Error updating tracked symbols: {e}")

    async def _update_screening_data(self) -> None:
        """Update screening data and tracked symbols"""
        try:
            logger.info("Updating screening data...")

            # Update tracked symbols from screening results
            await self._update_tracked_symbols()

            # Run a fresh screening if needed
            if self._should_update_screening(datetime.now()):
                screening_criteria = ScreeningCriteria(
                    min_price=self.config.screening_criteria.get("min_price", 5.0),
                    max_price=self.config.screening_criteria.get("max_price", 1000.0),
                    min_volume=self.config.screening_criteria.get("min_volume", 100000),
                    min_daily_change=self.config.screening_criteria.get("min_daily_change", -20.0),
                    max_daily_change=self.config.screening_criteria.get("max_daily_change", 20.0),
                    max_results=self.config.screening_criteria.get("max_results", 50),
                    exclude_penny_stocks=self.config.screening_criteria.get("exclude_penny_stocks", True),
                )

                # Get enhanced screening results
                results = await self.stock_screener.get_prediction_enhanced_screening(screening_criteria)

                self.last_screening_update = datetime.now()
                logger.info(f"Screening completed: {len(results)} stocks identified")

        except Exception as e:
            logger.exception(f"Error updating screening data: {e}")

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Get current portfolio summary"""
        try:
            account_info = self.broker_adapter.get_account_info()
            positions = self.broker_adapter.get_positions()

            total_value = sum(pos.market_value for pos in positions)
            total_pnl = sum(pos.unrealized_pl for pos in positions)

            return {
                "account_value": account_info.portfolio_value,
                "cash": account_info.cash,
                "buying_power": account_info.buying_power,
                "positions_count": len(positions),
                "positions_value": total_value,
                "unrealized_pnl": total_pnl,
                "day_trade_count": account_info.day_trade_count,
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "quantity": pos.quantity,
                        "market_value": pos.market_value,
                        "unrealized_pl": pos.unrealized_pl,
                        "unrealized_pl_percent": pos.unrealized_pl_percent,
                    }
                    for pos in positions
                ],
            }
        except Exception as e:
            logger.exception(f"Failed to get portfolio summary: {e}")
            return {}

    def get_recent_signals(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get recent trading signals"""
        try:
            since_time = datetime.now() - timedelta(hours=hours)
            signals = self.signal_repo.get_signals_by_time_range(start_time=since_time, end_time=datetime.now())

            return [
                {
                    "symbol": signal.symbol,
                    "signal_type": signal.signal_type,
                    "strength": signal.strength,
                    "strategy": signal.strategy,
                    "timestamp": signal.timestamp,
                    "metadata": signal.metadata,
                }
                for signal in signals
            ]
        except Exception as e:
            logger.exception(f"Failed to get recent signals: {e}")
            return []

    def get_trading_stats(self) -> dict[str, Any]:
        """Get trading statistics"""
        try:
            # Get recent signals
            recent_signals = self.get_recent_signals(hours=24)

            # Calculate signal statistics
            signal_counts = {}
            for signal in recent_signals:
                strategy = signal["strategy"]
                if strategy not in signal_counts:
                    signal_counts[strategy] = {"buy": 0, "sell": 0}
                signal_counts[strategy][signal["signal_type"].lower()] += 1

            # Get portfolio summary
            portfolio = self.get_portfolio_summary()

            return {
                "is_running": self.is_running,
                "last_data_update": self.last_data_update,
                "last_news_update": self.last_news_update,
                "last_strategy_evaluation": self.last_strategy_evaluation,
                "signal_counts": signal_counts,
                "portfolio": portfolio,
                "config": {
                    "symbols_tracked": len(self.config.symbols_to_track),
                    "max_positions": self.config.max_positions,
                    "position_size_percent": self.config.position_size_percent,
                    "stop_loss_percent": self.config.stop_loss_percent,
                    "take_profit_percent": self.config.take_profit_percent,
                },
            }
        except Exception as e:
            logger.exception(f"Failed to get trading stats: {e}")
            return {}

    def get_screening_summary(self) -> dict[str, Any]:
        """Get summary of screening results"""
        try:
            return {
                "screening_enabled": self.config.enable_automated_screening,
                "screening_interval_minutes": self.config.screening_interval_minutes,
                "last_screening_update": self.last_screening_update,
                "tracked_symbols_count": len(self.config.symbols_to_track),
                "screening_statistics": self.stock_screener.get_screening_statistics(),
                "screening_results": [
                    {
                        "symbol": result.symbol,
                        "score": result.score,
                        "daily_change": result.daily_change_percent,
                        "reasons": result.reasons,
                    }
                    for result in sorted(
                        self.stock_screener.get_screening_results().values(),
                        key=lambda x: x.score,
                        reverse=True,
                    )[:10]  # Top 10 results
                ],
            }
        except Exception as e:
            logger.exception(f"Error getting screening summary: {e}")
            return {}
