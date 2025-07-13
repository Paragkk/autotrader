"""
Shared session utilities for Alpaca API
"""

from requests import Session
from requests_cache import CacheMixin, SQLiteCache
from requests_ratelimiter import LimiterMixin, MemoryQueueBucket
from pyrate_limiter import Duration, RequestRate, Limiter


class CachedLimiterSession(CacheMixin, LimiterMixin, Session):
    """Shared cached and rate-limited session for API calls"""

    pass


def create_session(
    cache_name: str = "yfinance.cache", rate_limit: int = 2, duration: int = 5
):
    """Create a configured session with caching and rate limiting"""
    return CachedLimiterSession(
        limiter=Limiter(RequestRate(rate_limit, Duration.SECOND * duration)),
        bucket_class=MemoryQueueBucket,
        backend=SQLiteCache(cache_name),
    )
