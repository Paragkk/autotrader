"""
News Analyzer and Sentiment Analysis Module
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
from textblob import TextBlob
from ..brokers.base import BrokerInterface

logger = logging.getLogger(__name__)


class NewsAnalyzer:
    """
    Analyzes news sentiment and extracts trading signals from news data
    """

    def __init__(self, broker_adapter: BrokerInterface):
        self.broker_adapter = broker_adapter
        self.sentiment_cache = {}

        # Keywords for different sentiment categories
        self.positive_keywords = [
            "bullish",
            "surge",
            "rally",
            "growth",
            "profit",
            "beat",
            "exceed",
            "strong",
            "gain",
            "rise",
            "up",
            "positive",
            "upgrade",
            "outperform",
            "breakthrough",
            "success",
            "expansion",
            "acquisition",
            "merger",
        ]

        self.negative_keywords = [
            "bearish",
            "decline",
            "fall",
            "loss",
            "miss",
            "below",
            "weak",
            "drop",
            "down",
            "negative",
            "downgrade",
            "underperform",
            "concern",
            "risk",
            "lawsuit",
            "investigation",
            "bankruptcy",
            "recession",
        ]

        self.volatility_keywords = [
            "volatile",
            "uncertain",
            "speculation",
            "rumor",
            "pending",
            "investigation",
            "regulatory",
            "lawsuit",
            "earnings",
            "report",
        ]

    def analyze_news_sentiment(
        self, news_articles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of news articles for a symbol

        Args:
            news_articles: List of news articles with title, content, etc.

        Returns:
            Dictionary with sentiment analysis results
        """
        if not news_articles:
            return {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "confidence": 0.0,
                "article_count": 0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
            }

        sentiment_scores = []
        sentiment_labels = []

        for article in news_articles:
            # Combine title and content for analysis
            text = f"{article.get('title', '')} {article.get('content', '')}"

            if not text.strip():
                continue

            # Calculate sentiment using multiple methods
            textblob_sentiment = self._textblob_sentiment(text)
            keyword_sentiment = self._keyword_sentiment(text)

            # Combine sentiments (weighted average)
            combined_sentiment = textblob_sentiment * 0.6 + keyword_sentiment * 0.4
            sentiment_scores.append(combined_sentiment)

            # Classify sentiment
            if combined_sentiment > 0.1:
                sentiment_labels.append("positive")
            elif combined_sentiment < -0.1:
                sentiment_labels.append("negative")
            else:
                sentiment_labels.append("neutral")

        if not sentiment_scores:
            return self._empty_sentiment_result()

        # Calculate aggregate metrics
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)

        positive_count = sentiment_labels.count("positive")
        negative_count = sentiment_labels.count("negative")
        neutral_count = sentiment_labels.count("neutral")

        # Determine overall sentiment label
        if avg_sentiment > 0.1:
            overall_label = "positive"
        elif avg_sentiment < -0.1:
            overall_label = "negative"
        else:
            overall_label = "neutral"

        # Calculate confidence based on agreement between articles
        max_count = max(positive_count, negative_count, neutral_count)
        confidence = max_count / len(sentiment_labels) if sentiment_labels else 0

        return {
            "sentiment_score": avg_sentiment,
            "sentiment_label": overall_label,
            "confidence": confidence,
            "article_count": len(news_articles),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "raw_scores": sentiment_scores,
            "analysis_timestamp": datetime.now(),
        }

    def _textblob_sentiment(self, text: str) -> float:
        """Calculate sentiment using TextBlob"""
        try:
            blob = TextBlob(text)
            # TextBlob polarity ranges from -1 to 1
            return blob.sentiment.polarity
        except Exception as e:
            logger.warning(f"TextBlob sentiment analysis failed: {e}")
            return 0.0

    def _keyword_sentiment(self, text: str) -> float:
        """Calculate sentiment based on keyword matching"""
        text_lower = text.lower()

        positive_matches = sum(
            1 for keyword in self.positive_keywords if keyword in text_lower
        )
        negative_matches = sum(
            1 for keyword in self.negative_keywords if keyword in text_lower
        )

        total_matches = positive_matches + negative_matches

        if total_matches == 0:
            return 0.0

        # Normalize to -1 to 1 range
        sentiment = (positive_matches - negative_matches) / total_matches
        return sentiment

    def _empty_sentiment_result(self) -> Dict[str, Any]:
        """Return empty sentiment result"""
        return {
            "sentiment_score": 0.0,
            "sentiment_label": "neutral",
            "confidence": 0.0,
            "article_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
        }

    def get_news_signals(
        self, symbols: List[str], hours_back: int = 24
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate trading signals based on news sentiment analysis

        Args:
            symbols: List of stock symbols to analyze
            hours_back: Number of hours to look back for news

        Returns:
            Dictionary with signals for each symbol
        """
        signals = {}

        for symbol in symbols:
            try:
                # Get recent news for the symbol
                news_articles = self.alpaca_client.trading.news.get_news(
                    symbol=symbol, limit=20
                )

                # Filter news by time window
                cutoff_time = datetime.now() - timedelta(hours=hours_back)
                recent_articles = []

                for article in news_articles:
                    try:
                        # Parse article timestamp
                        article_time = datetime.fromisoformat(
                            article.get("publish_date", "").replace("Z", "+00:00")
                        )
                        if article_time >= cutoff_time:
                            recent_articles.append(article)
                    except Exception:
                        # If timestamp parsing fails, include the article anyway
                        recent_articles.append(article)

                # Analyze sentiment
                sentiment_result = self.analyze_news_sentiment(recent_articles)

                # Generate trading signal based on sentiment
                signal = self._sentiment_to_signal(symbol, sentiment_result)

                signals[symbol] = {
                    "sentiment_analysis": sentiment_result,
                    "trading_signal": signal,
                    "news_count": len(recent_articles),
                }

            except Exception as e:
                logger.error(f"Error analyzing news for {symbol}: {e}")
                signals[symbol] = {
                    "sentiment_analysis": self._empty_sentiment_result(),
                    "trading_signal": None,
                    "news_count": 0,
                    "error": str(e),
                }

        return signals

    def _sentiment_to_signal(
        self, symbol: str, sentiment_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Convert sentiment analysis to trading signal"""
        sentiment_score = sentiment_result["sentiment_score"]
        confidence = sentiment_result["confidence"]
        article_count = sentiment_result["article_count"]

        # Require minimum confidence and article count
        if confidence < 0.6 or article_count < 3:
            return None

        # Generate signal based on sentiment strength
        if sentiment_score > 0.3 and confidence > 0.7:
            return {
                "symbol": symbol,
                "strategy_name": "news_sentiment",
                "signal_type": "buy",
                "strength": min(1.0, sentiment_score * 2),  # Scale up sentiment
                "confidence": confidence,
                "metadata": {
                    "sentiment_score": sentiment_score,
                    "article_count": article_count,
                    "signal_source": "positive_news_sentiment",
                },
            }
        elif sentiment_score < -0.3 and confidence > 0.7:
            return {
                "symbol": symbol,
                "strategy_name": "news_sentiment",
                "signal_type": "sell",
                "strength": min(1.0, abs(sentiment_score) * 2),
                "confidence": confidence,
                "metadata": {
                    "sentiment_score": sentiment_score,
                    "article_count": article_count,
                    "signal_source": "negative_news_sentiment",
                },
            }

        return None

    def analyze_sector_sentiment(
        self, sector_symbols: Dict[str, List[str]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze sentiment by sector

        Args:
            sector_symbols: Dictionary mapping sector names to lists of symbols

        Returns:
            Dictionary with sentiment analysis for each sector
        """
        sector_sentiment = {}

        for sector, symbols in sector_symbols.items():
            try:
                # Get news signals for all symbols in sector
                symbol_signals = self.get_news_signals(symbols, hours_back=48)

                # Aggregate sector sentiment
                sector_scores = []
                total_articles = 0

                for symbol, signal_data in symbol_signals.items():
                    sentiment = signal_data["sentiment_analysis"]
                    if sentiment["article_count"] > 0:
                        sector_scores.append(sentiment["sentiment_score"])
                        total_articles += sentiment["article_count"]

                if sector_scores:
                    avg_sentiment = sum(sector_scores) / len(sector_scores)

                    sector_sentiment[sector] = {
                        "average_sentiment": avg_sentiment,
                        "symbol_count": len(symbols),
                        "analyzed_symbols": len(sector_scores),
                        "total_articles": total_articles,
                        "sentiment_label": self._score_to_label(avg_sentiment),
                        "symbol_details": symbol_signals,
                    }
                else:
                    sector_sentiment[sector] = {
                        "average_sentiment": 0.0,
                        "symbol_count": len(symbols),
                        "analyzed_symbols": 0,
                        "total_articles": 0,
                        "sentiment_label": "neutral",
                        "symbol_details": {},
                    }

            except Exception as e:
                logger.error(f"Error analyzing sector {sector}: {e}")
                sector_sentiment[sector] = {
                    "error": str(e),
                    "symbol_count": len(symbols),
                    "analyzed_symbols": 0,
                }

        return sector_sentiment

    def _score_to_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score > 0.1:
            return "positive"
        elif score < -0.1:
            return "negative"
        else:
            return "neutral"

    def get_trending_topics(
        self, news_articles: List[Dict[str, Any]], top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Extract trending topics from news articles

        Args:
            news_articles: List of news articles
            top_n: Number of top topics to return

        Returns:
            List of trending topics with frequency and sentiment
        """
        # Simple topic extraction using keyword frequency
        word_freq = {}
        word_sentiment = {}

        # Common words to exclude
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "can",
            "may",
            "might",
            "must",
            "shall",
        }

        for article in news_articles:
            text = f"{article.get('title', '')} {article.get('content', '')}".lower()

            # Simple tokenization and cleaning
            words = re.findall(r"\b[a-zA-Z]{3,}\b", text)

            # Calculate article sentiment
            article_sentiment = self._textblob_sentiment(text)

            for word in words:
                if word not in stop_words and len(word) > 2:
                    word_freq[word] = word_freq.get(word, 0) + 1

                    # Track sentiment for each word
                    if word not in word_sentiment:
                        word_sentiment[word] = []
                    word_sentiment[word].append(article_sentiment)

        # Sort by frequency and create topic list
        trending_topics = []

        for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[
            :top_n
        ]:
            avg_sentiment = sum(word_sentiment[word]) / len(word_sentiment[word])

            trending_topics.append(
                {
                    "topic": word,
                    "frequency": freq,
                    "sentiment_score": avg_sentiment,
                    "sentiment_label": self._score_to_label(avg_sentiment),
                }
            )

        return trending_topics
