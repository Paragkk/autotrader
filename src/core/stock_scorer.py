"""
Stock Scorer - Comprehensive Stock Scoring System
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
import pandas as pd
from dataclasses import dataclass, field
from sqlmodel import Session

from db.models import StockScore

logger = logging.getLogger(__name__)


@dataclass
class ScoringFactors:
    """Configuration for scoring factors"""

    momentum: float = 0.25
    volume: float = 0.20
    volatility: float = 0.15
    technical: float = 0.20
    sentiment: float = 0.10
    fundamentals: float = 0.10

    def __post_init__(self):
        """Validate that weights sum to 1.0"""
        total = sum(
            [
                self.momentum,
                self.volume,
                self.volatility,
                self.technical,
                self.sentiment,
                self.fundamentals,
            ]
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scoring factors must sum to 1.0, got {total}")


@dataclass
class StockScoreResult:
    """Result of stock scoring"""

    symbol: str
    total_score: float
    factor_scores: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class StockScorer:
    """Comprehensive stock scoring system"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.factors = ScoringFactors(**config.get("factors", {}))
        self.top_n_stocks = config.get("top_n_stocks", 30)
        self.min_score_threshold = config.get("min_score_threshold", 0.5)

    def score_stocks(
        self, screened_stocks: List[Dict[str, Any]]
    ) -> List[StockScoreResult]:
        """Score a list of screened stocks"""
        if not screened_stocks:
            return []

        logger.info(f"Scoring {len(screened_stocks)} stocks")

        # Convert to DataFrame for easier calculations
        df = pd.DataFrame(screened_stocks)

        # Calculate individual factor scores
        momentum_scores = self._calculate_momentum_scores(df)
        volume_scores = self._calculate_volume_scores(df)
        volatility_scores = self._calculate_volatility_scores(df)
        technical_scores = self._calculate_technical_scores(df)
        sentiment_scores = self._calculate_sentiment_scores(df)
        fundamental_scores = self._calculate_fundamental_scores(df)

        # Combine scores
        results = []
        for i, row in df.iterrows():
            symbol = row["symbol"]

            factor_scores = {
                "momentum": momentum_scores.get(symbol, 0.0),
                "volume": volume_scores.get(symbol, 0.0),
                "volatility": volatility_scores.get(symbol, 0.0),
                "technical": technical_scores.get(symbol, 0.0),
                "sentiment": sentiment_scores.get(symbol, 0.0),
                "fundamentals": fundamental_scores.get(symbol, 0.0),
            }

            # Calculate weighted total score
            total_score = (
                factor_scores["momentum"] * self.factors.momentum
                + factor_scores["volume"] * self.factors.volume
                + factor_scores["volatility"] * self.factors.volatility
                + factor_scores["technical"] * self.factors.technical
                + factor_scores["sentiment"] * self.factors.sentiment
                + factor_scores["fundamentals"] * self.factors.fundamentals
            )

            # Calculate confidence based on data completeness
            confidence = self._calculate_confidence(factor_scores, row)

            results.append(
                StockScoreResult(
                    symbol=symbol,
                    total_score=total_score,
                    factor_scores=factor_scores,
                    confidence=confidence,
                    metadata={
                        "price": row.get("current_price", 0),
                        "volume": row.get("volume", 0),
                        "daily_change": row.get("daily_change", 0),
                        "market_cap": row.get("market_cap", 0),
                    },
                )
            )

        # Sort by total score and return top N
        results.sort(key=lambda x: x.total_score, reverse=True)
        top_results = results[: self.top_n_stocks]

        # Filter by minimum score threshold
        filtered_results = [
            r for r in top_results if r.total_score >= self.min_score_threshold
        ]

        logger.info(
            f"Scored {len(results)} stocks, returning top {len(filtered_results)} with score >= {self.min_score_threshold}"
        )
        return filtered_results

    def _calculate_momentum_scores(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate momentum scores based on price changes"""
        scores = {}

        for _, row in df.iterrows():
            symbol = row["symbol"]
            daily_change = row.get("daily_change", 0)

            # Normalize daily change to 0-1 scale
            # Strong positive momentum gets higher score
            if daily_change > 0:
                score = min(1.0, daily_change / 10.0)  # Cap at 10% change
            else:
                score = max(
                    0.0, 1.0 + daily_change / 10.0
                )  # Decay for negative changes

            scores[symbol] = score

        return scores

    def _calculate_volume_scores(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate volume scores based on trading volume"""
        scores = {}

        # Calculate volume percentiles
        volumes = df["volume"].fillna(0)
        if len(volumes) > 0:
            volume_percentiles = volumes.rank(pct=True)

            for i, (_, row) in enumerate(df.iterrows()):
                scores[row["symbol"]] = volume_percentiles.iloc[i]

        return scores

    def _calculate_volatility_scores(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate volatility scores (moderate volatility preferred)"""
        scores = {}

        for _, row in df.iterrows():
            symbol = row["symbol"]

            # Use daily change as proxy for volatility
            daily_change = abs(row.get("daily_change", 0))

            # Moderate volatility (2-5%) gets highest score
            if 2.0 <= daily_change <= 5.0:
                score = 1.0
            elif daily_change < 2.0:
                score = daily_change / 2.0
            else:
                score = max(0.0, 1.0 - (daily_change - 5.0) / 10.0)

            scores[symbol] = score

        return scores

    def _calculate_technical_scores(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate technical analysis scores"""
        scores = {}

        for _, row in df.iterrows():
            symbol = row["symbol"]

            # Basic technical scoring based on available data
            # This is a simplified version - could be enhanced with more indicators
            score = 0.5  # Default neutral score

            # Price vs moving averages (if available)
            current_price = row.get("current_price", 0)
            if current_price > 0:
                # Simple heuristic: higher prices relative to recent performance
                daily_change = row.get("daily_change", 0)
                if daily_change > 0:
                    score += 0.3
                else:
                    score -= 0.3

            scores[symbol] = max(0.0, min(1.0, score))

        return scores

    def _calculate_sentiment_scores(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate sentiment scores (placeholder for now)"""
        scores = {}

        # Placeholder: Return neutral sentiment for all stocks
        # This could be enhanced with news sentiment analysis
        for _, row in df.iterrows():
            scores[row["symbol"]] = 0.5  # Neutral sentiment

        return scores

    def _calculate_fundamental_scores(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate fundamental analysis scores"""
        scores = {}

        for _, row in df.iterrows():
            symbol = row["symbol"]

            # Basic fundamental scoring
            score = 0.5  # Default neutral score

            # Market cap consideration
            market_cap = row.get("market_cap", 0)
            if market_cap > 1e9:  # Large cap
                score += 0.2
            elif market_cap > 1e8:  # Mid cap
                score += 0.1

            # P/E ratio consideration (if available)
            pe_ratio = row.get("pe_ratio", 0)
            if 0 < pe_ratio < 25:  # Reasonable P/E
                score += 0.2
            elif pe_ratio > 50:  # High P/E
                score -= 0.1

            scores[symbol] = max(0.0, min(1.0, score))

        return scores

    def _calculate_confidence(
        self, factor_scores: Dict[str, float], row: pd.Series
    ) -> float:
        """Calculate confidence score based on data completeness"""
        # Count how many factors have meaningful scores
        meaningful_factors = sum(1 for score in factor_scores.values() if score != 0.5)
        total_factors = len(factor_scores)

        # Base confidence on data completeness
        base_confidence = meaningful_factors / total_factors

        # Adjust based on data quality
        if row.get("volume", 0) > 100000:  # Good volume
            base_confidence += 0.1
        if row.get("market_cap", 0) > 1e8:  # Known market cap
            base_confidence += 0.1

        return min(1.0, base_confidence)

    def save_scores(self, db_session: Session, scores: List[StockScoreResult]) -> None:
        """Save stock scores to database"""
        try:
            for score_result in scores:
                score_record = StockScore(
                    symbol=score_result.symbol,
                    total_score=score_result.total_score,
                    momentum_score=score_result.factor_scores.get("momentum", 0.0),
                    volume_score=score_result.factor_scores.get("volume", 0.0),
                    volatility_score=score_result.factor_scores.get("volatility", 0.0),
                    technical_score=score_result.factor_scores.get("technical", 0.0),
                    sentiment_score=score_result.factor_scores.get("sentiment", 0.0),
                    fundamental_score=score_result.factor_scores.get(
                        "fundamentals", 0.0
                    ),
                    confidence=score_result.confidence,
                    metadata=score_result.metadata,
                    timestamp=score_result.timestamp,
                )

                db_session.add(score_record)

            db_session.commit()
            logger.info(f"Saved {len(scores)} stock scores to database")

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error saving stock scores: {e}")
            raise

    def get_top_scored_stocks(
        self, db_session: Session, limit: int = None
    ) -> List[Dict[str, Any]]:
        """Get top scored stocks from database"""
        try:
            query = db_session.query(StockScore).order_by(
                StockScore.total_score.desc(), StockScore.timestamp.desc()
            )

            if limit:
                query = query.limit(limit)

            results = query.all()

            return [
                {
                    "symbol": score.symbol,
                    "total_score": score.total_score,
                    "confidence": score.confidence,
                    "timestamp": score.timestamp,
                    "metadata": score.metadata,
                }
                for score in results
            ]

        except Exception as e:
            logger.error(f"Error getting top scored stocks: {e}")
            return []
