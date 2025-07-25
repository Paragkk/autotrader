"""
Data Fetcher Module - Enhanced with Database Integration
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from brokers.base import BrokerAdapter
from db.repository import StockDataRepository, SymbolRepository

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Fetches market data from various sources and stores in database
    """

    def __init__(
        self,
        stock_data_repo: StockDataRepository,
        symbol_repo: SymbolRepository,
        broker_adapter: BrokerAdapter,
    ) -> None:
        self.stock_data_repo = stock_data_repo
        self.symbol_repo = symbol_repo
        self.broker_adapter = broker_adapter

    def fetch_symbol_list(self, exchanges: list[str] | None = None) -> list[str]:
        """Fetch and store list of tradeable symbols"""
        try:
            # Get assets from broker
            assets = self.broker_adapter.get_assets()

            # Filter by exchanges if specified
            if exchanges:
                assets = [asset for asset in assets if asset.exchange in exchanges]

            symbols = [asset.symbol for asset in assets]

            # Store symbols in database
            for asset in assets:
                self.symbol_repo.add_or_update(
                    {
                        "symbol": asset.symbol,
                        "name": asset.name,
                        "exchange": asset.exchange,
                        "asset_class": asset.asset_class,
                        "tradable": asset.tradable,
                        "marginable": asset.marginable,
                        "shortable": asset.shortable,
                        "easy_to_borrow": asset.easy_to_borrow,
                        "fractionable": asset.fractionable,
                        "last_updated": datetime.now(),
                    }
                )

            logger.info(f"Fetched and stored {len(symbols)} symbols")
            return symbols

        except Exception as e:
            logger.exception(f"Error fetching symbol list: {e}")
            raise

    def fetch_daily_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch daily market data for a symbol"""
        try:
            # Get data from broker
            bars = self.broker_adapter.get_historical_bars(symbol=symbol, start=start_date, end=end_date, timeframe="1day")

            # Convert to DataFrame for storage
            data_records = []
            for bar in bars:
                data_records.append(
                    {
                        "date": bar.timestamp,
                        "open": bar.open,
                        "high": bar.high,
                        "low": bar.low,
                        "close": bar.close,
                        "volume": bar.volume,
                        "vwap": bar.vwap,
                        "trade_count": bar.trade_count,
                    }
                )

            data = pd.DataFrame(data_records)

            # Store in database
            for _, row in data.iterrows():
                self.stock_data_repo.add_or_update(
                    {
                        "symbol": symbol,
                        "date": row["date"],
                        "open": row["open"],
                        "high": row["high"],
                        "low": row["low"],
                        "close": row["close"],
                        "volume": row["volume"],
                        "vwap": row["vwap"],
                        "trade_count": row["trade_count"],
                        "last_updated": datetime.now(),
                    }
                )

            logger.info(f"Fetched daily data for {symbol} from {start_date} to {end_date}")
            return data

        except Exception as e:
            logger.exception(f"Error fetching daily data for {symbol}: {e}")
            raise

    def fetch_incremental_data(self, symbols: list[str] | None = None, days_back: int = 1) -> dict[str, pd.DataFrame]:
        """Fetch incremental data for symbols (last N days)"""
        try:
            if symbols is None:
                symbols = self.symbol_repo.get_active_symbols()

            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)

            results = {}

            for symbol in symbols:
                try:
                    # Check if we already have recent data
                    latest_data = self.stock_data_repo.get_latest_date(symbol)

                    if latest_data and latest_data >= start_date:
                        logger.debug(f"Skipping {symbol}, data is up to date")
                        continue

                    # Fetch new data
                    data = self.fetch_daily_data(symbol, str(start_date), str(end_date))
                    results[symbol] = data

                except Exception as e:
                    logger.warning(f"Failed to fetch data for {symbol}: {e}")
                    continue

            logger.info(f"Fetched incremental data for {len(results)} symbols")
            return results

        except Exception as e:
            logger.exception(f"Error fetching incremental data: {e}")
            raise

    def fetch_intraday_data(self, symbol: str, timeframe: str = "1min", limit: int = 1000) -> pd.DataFrame:
        """Fetch intraday data for a symbol"""
        try:
            # Get intraday data from broker
            bars = self.broker_adapter.get_historical_bars(
                symbol=symbol,
                start=None,  # Use default lookback
                end=None,
                timeframe=timeframe,
            )

            # Convert to DataFrame
            data_records = []
            for bar in bars:
                data_records.append(
                    {
                        "timestamp": bar.timestamp,
                        "open": bar.open,
                        "high": bar.high,
                        "low": bar.low,
                        "close": bar.close,
                        "volume": bar.volume,
                        "vwap": bar.vwap,
                        "trade_count": bar.trade_count,
                    }
                )

            data = pd.DataFrame(data_records)

            logger.info(f"Fetched intraday data for {symbol} with timeframe {timeframe}")
            return data

        except Exception as e:
            logger.exception(f"Error fetching intraday data for {symbol}: {e}")
            raise

    def fetch_market_news(self, symbols: list[str] | None = None, limit: int = 50) -> list[dict]:
        """Fetch market news for symbols"""
        try:
            all_news = []

            if symbols is None:
                symbols = self.symbol_repo.get_active_symbols()[:10]  # Limit to avoid API throttling

            for symbol in symbols:
                try:
                    # Get news from broker adapter
                    news_data = self.broker_adapter.get_news(symbol=symbol, limit=limit // len(symbols))
                    for article in news_data:
                        all_news.append(
                            {
                                "symbol": symbol,
                                "title": article.get("title", ""),
                                "content": article.get("content", ""),
                                "url": article.get("url", ""),
                                "publish_date": article.get("publish_date", ""),
                                "source": article.get("source", ""),
                                "sentiment": None,  # Will be calculated by news analyzer
                                "last_updated": datetime.now(),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Failed to fetch news for {symbol}: {e}")
                    continue

            logger.info(f"Fetched {len(all_news)} news articles")
            return all_news

        except Exception as e:
            logger.exception(f"Error fetching market news: {e}")
            raise

    def fetch_market_screener_data(self, price_min: float = 5.0, volume_min: int = 20000, limit: int = 100) -> dict[str, pd.DataFrame]:
        """Fetch market screener data (gainers/losers)"""
        try:
            # Get gainers and losers from broker adapter
            gainers = self.broker_adapter.get_gainers(
                price_greater_than=price_min,
                volume_greater_than=volume_min,
                limit=limit,
            )

            losers = self.broker_adapter.get_losers(
                price_greater_than=price_min,
                volume_greater_than=volume_min,
                limit=limit,
            )

            logger.info(f"Fetched {len(gainers)} gainers and {len(losers)} losers")
            return {"gainers": gainers, "losers": losers}

        except Exception as e:
            logger.exception(f"Error fetching screener data: {e}")
            raise

    def get_cached_data(self, symbol: str, start_date: str | None = None, end_date: str | None = None) -> pd.DataFrame:
        """Get cached data from database"""
        try:
            return self.stock_data_repo.get_data_by_symbol_and_date_range(symbol=symbol, start_date=start_date, end_date=end_date)
        except Exception as e:
            logger.exception(f"Error getting cached data for {symbol}: {e}")
            raise

    def update_symbol_metadata(self, symbol: str, metadata: dict[str, Any]) -> None:
        """Update metadata for a symbol"""
        try:
            self.symbol_repo.update_metadata(symbol, metadata)
            logger.debug(f"Updated metadata for {symbol}")
        except Exception as e:
            logger.exception(f"Error updating metadata for {symbol}: {e}")
            raise
