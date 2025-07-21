"""
Enhanced Stock Screener with Automated Screening and Dynamic Symbol Management
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from core.data_fetcher import DataFetcher
from db.repository import StockDataRepository, SymbolRepository

logger = logging.getLogger(__name__)


@dataclass
class ScreeningCriteria:
    """Configuration for stock screening criteria"""

    # Basic filtering
    min_price: float = 5.0
    max_price: float = 1000.0
    min_volume: int = 100000
    min_market_cap: float | None = None

    # Performance criteria
    min_daily_change: float = -50.0  # Allow significant losers
    max_daily_change: float = 50.0  # Allow significant gainers
    min_volume_ratio: float = 1.0  # Volume vs average volume

    # Technical criteria
    rsi_min: float | None = None
    rsi_max: float | None = None
    above_sma_20: bool | None = None
    above_sma_50: bool | None = None

    # Fundamental criteria
    min_pe_ratio: float | None = None
    max_pe_ratio: float | None = None
    min_revenue_growth: float | None = None

    # Screening targets
    max_results: int = 50
    exclude_penny_stocks: bool = True
    exclude_etfs: bool = False


@dataclass
class ScreeningResult:
    """Result of stock screening"""

    symbol: str
    current_price: float
    daily_change: float
    daily_change_percent: float
    volume: int
    market_cap: float | None = None
    pe_ratio: float | None = None
    rsi: float | None = None
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class EnhancedStockScreener:
    """
    Enhanced stock screener with automated screening capabilities
    """

    def __init__(
        self,
        data_fetcher: DataFetcher,
        symbol_repo: SymbolRepository,
        stock_data_repo: StockDataRepository,
    ) -> None:
        self.data_fetcher = data_fetcher
        self.symbol_repo = symbol_repo
        self.stock_data_repo = stock_data_repo
        self.tracked_symbols: set[str] = set()
        self.screening_results: dict[str, ScreeningResult] = {}
        self.last_screening_time: datetime | None = None

    async def run_comprehensive_screening(self, criteria: ScreeningCriteria) -> list[ScreeningResult]:
        """Run comprehensive stock screening with multiple criteria"""
        logger.info("Starting comprehensive stock screening...")

        try:
            # Get initial screening results using existing screener
            screener_data = self.data_fetcher.fetch_market_screener_data(
                price_min=criteria.min_price,
                volume_min=criteria.min_volume,
                limit=criteria.max_results * 2,  # Get more to filter later
            )

            # Combine gainers and losers
            all_candidates = pd.concat([screener_data["gainers"], screener_data["losers"]], ignore_index=True)

            # Apply additional filtering
            filtered_candidates = self._apply_advanced_filters(all_candidates, criteria)

            # Score and rank candidates
            screening_results = await self._score_and_rank_candidates(filtered_candidates, criteria)

            # Update internal tracking
            self._update_screening_results(screening_results)
            self.last_screening_time = datetime.now()

            logger.info(f"Screening completed: {len(screening_results)} stocks identified")
            return screening_results[: criteria.max_results]

        except Exception as e:
            logger.exception(f"Error in comprehensive screening: {e}")
            raise

    def _apply_advanced_filters(self, candidates: pd.DataFrame, criteria: ScreeningCriteria) -> pd.DataFrame:
        """Apply advanced filtering criteria"""
        filtered = candidates.copy()

        # Price filters
        if criteria.max_price:
            filtered = filtered[filtered["price"] <= criteria.max_price]

        # Change filters
        filtered = filtered[(filtered["change"] >= criteria.min_daily_change) & (filtered["change"] <= criteria.max_daily_change)]

        # Exclude penny stocks if requested
        if criteria.exclude_penny_stocks:
            filtered = filtered[filtered["price"] >= 1.0]

        return filtered

    async def _score_and_rank_candidates(self, candidates: pd.DataFrame, criteria: ScreeningCriteria) -> list[ScreeningResult]:
        """Score and rank candidates based on multiple factors"""
        results = []

        for _, row in candidates.iterrows():
            try:
                symbol = row["symbol"]

                # Create basic screening result
                result = ScreeningResult(
                    symbol=symbol,
                    current_price=row["price"],
                    daily_change=row["change"],
                    daily_change_percent=row["change"],
                    volume=row["volume"],
                )

                # Calculate score based on multiple factors
                score = self._calculate_candidate_score(row, criteria)
                result.score = score

                # Add scoring reasons
                result.reasons = self._get_scoring_reasons(row, criteria)

                results.append(result)

            except Exception as e:
                logger.warning(f"Error scoring candidate {row.get('symbol', 'unknown')}: {e}")
                continue

        # Sort by score (highest first)
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def _calculate_candidate_score(self, row: pd.Series, criteria: ScreeningCriteria) -> float:
        """Calculate a score for a candidate stock"""
        score = 0.0

        # Volume score (higher volume = higher score)
        volume_score = min(row["volume"] / criteria.min_volume, 5.0)
        score += volume_score * 0.3

        # Price change score (both positive and negative changes can be valuable)
        change_score = abs(row["change"]) / 10.0  # Normalize to 0-1 range typically
        score += change_score * 0.4

        # Price stability score (avoid extreme penny stocks)
        price_score = min(row["price"] / criteria.min_price, 3.0)
        score += price_score * 0.3

        return score

    def _get_scoring_reasons(self, row: pd.Series, criteria: ScreeningCriteria) -> list[str]:
        """Get reasons for scoring a candidate"""
        reasons = []

        if row["volume"] > criteria.min_volume * 2:
            reasons.append("High volume")

        if abs(row["change"]) > 5.0:
            reasons.append("Significant price movement")

        if row["change"] > 0:
            reasons.append("Positive momentum")
        else:
            reasons.append("Potential reversal candidate")

        if row["price"] > criteria.min_price * 2:
            reasons.append("Above minimum price threshold")

        return reasons

    def _update_screening_results(self, results: list[ScreeningResult]) -> None:
        """Update internal screening results"""
        for result in results:
            self.screening_results[result.symbol] = result
            self.tracked_symbols.add(result.symbol)

    async def get_prediction_enhanced_screening(self, criteria: ScreeningCriteria) -> list[ScreeningResult]:
        """Combine screening with prediction analysis"""
        logger.info("Running prediction-enhanced screening...")

        try:
            # Get basic screening results
            basic_results = await self.run_comprehensive_screening(criteria)

            # Enhance with prediction analysis
            enhanced_results = []

            for result in basic_results:
                try:
                    # Get prediction analysis if available
                    predictor = self.data_fetcher.broker_adapter.stock.predictor

                    # Get losers to gainers prediction
                    if result.daily_change_percent < -2.0:  # Significant loser
                        future_gainers = predictor.get_losers_to_gainers(losers_to_scan=10, gain_ratio=5.0, future_periods=5)

                        if result.symbol in future_gainers:
                            result.score += 2.0
                            result.reasons.append("Predicted future gainer")

                    enhanced_results.append(result)

                except Exception as e:
                    logger.warning(f"Error enhancing prediction for {result.symbol}: {e}")
                    enhanced_results.append(result)

            # Re-sort by enhanced scores
            enhanced_results.sort(key=lambda x: x.score, reverse=True)

            logger.info(f"Prediction enhancement completed for {len(enhanced_results)} candidates")
            return enhanced_results

        except Exception as e:
            logger.exception(f"Error in prediction-enhanced screening: {e}")
            raise

    async def run_automated_screening(self, criteria: ScreeningCriteria, interval_minutes: int = 60) -> None:
        """Run automated screening at regular intervals"""
        logger.info(f"Starting automated screening every {interval_minutes} minutes...")

        while True:
            try:
                # Check if market is open (you'd implement this check)
                if await self._is_market_open():
                    # Run screening
                    results = await self.get_prediction_enhanced_screening(criteria)

                    # Process results
                    await self._process_screening_results(results)

                    logger.info(f"Automated screening completed: {len(results)} stocks identified")
                else:
                    logger.debug("Market closed, skipping screening")

                # Wait for next interval
                await asyncio.sleep(interval_minutes * 60)

            except Exception as e:
                logger.exception(f"Error in automated screening: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _is_market_open(self) -> bool:
        """Check if market is currently open"""
        try:
            # You would implement market hours check here
            # For now, return True during typical market hours
            current_time = datetime.now()
            return 9 <= current_time.hour <= 16  # Simple approximation
        except Exception:
            return True

    async def _process_screening_results(self, results: list[ScreeningResult]) -> None:
        """Process screening results and update tracking"""
        try:
            # Update symbol repository with new candidates
            for result in results:
                metadata = {
                    "screening_score": result.score,
                    "screening_reasons": result.reasons,
                    "last_screened": result.timestamp.isoformat(),
                    "daily_change": result.daily_change_percent,
                    "volume": result.volume,
                }

                await self._update_symbol_metadata(result.symbol, metadata)

                # Add to tracking list
                self.tracked_symbols.add(result.symbol)

            logger.info(f"Processed {len(results)} screening results")

        except Exception as e:
            logger.exception(f"Error processing screening results: {e}")

    async def _update_symbol_metadata(self, symbol: str, metadata: dict[str, Any]) -> None:
        """Update symbol metadata in repository"""
        try:
            self.data_fetcher.update_symbol_metadata(symbol, metadata)
        except Exception as e:
            logger.warning(f"Error updating metadata for {symbol}: {e}")

    def get_tracked_symbols(self) -> set[str]:
        """Get currently tracked symbols"""
        return self.tracked_symbols.copy()

    def get_screening_results(self, symbol: str | None = None) -> dict[str, ScreeningResult]:
        """Get screening results for all or specific symbol"""
        if symbol:
            return {symbol: self.screening_results.get(symbol)}
        return self.screening_results.copy()

    def add_custom_screening_criteria(self, name: str, criteria: ScreeningCriteria) -> None:
        """Add custom screening criteria (for future enhancement)"""
        # This would be implemented to support multiple screening configurations

    def get_screening_statistics(self) -> dict[str, Any]:
        """Get screening statistics"""
        return {
            "total_tracked_symbols": len(self.tracked_symbols),
            "last_screening_time": self.last_screening_time,
            "screening_results_count": len(self.screening_results),
            "top_scored_symbols": [{"symbol": r.symbol, "score": r.score} for r in sorted(self.screening_results.values(), key=lambda x: x.score, reverse=True)[:10]],
        }
