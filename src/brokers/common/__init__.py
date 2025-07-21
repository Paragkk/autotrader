"""
Common broker utilities and enhanced base interfaces
Extensions to the base broker interface for common functionality
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Protocol

from ...infra.http_client import BrokerHTTPClient
from ...infra.model_utils import create_dataclass_from_dict
from ..base import AccountInfo, BrokerAdapter, OrderRequest, OrderResponse, Position

logger = logging.getLogger(__name__)


class DataFetchable(Protocol):
    """Protocol for data fetching capabilities"""

    async def get_market_screener_data(self, **criteria) -> list[dict[str, Any]]:
        """Get market screener data"""
        ...

    async def get_news(self, symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Get market news"""
        ...

    async def get_assets(self, **filters) -> list[dict[str, Any]]:
        """Get tradeable assets"""
        ...


class WatchlistManageable(Protocol):
    """Protocol for watchlist management"""

    async def get_watchlists(self) -> list[dict[str, Any]]:
        """Get user watchlists"""
        ...

    async def create_watchlist(self, name: str, symbols: list[str]) -> bool:
        """Create new watchlist"""
        ...

    async def add_to_watchlist(self, watchlist_id: str, symbol: str) -> bool:
        """Add symbol to watchlist"""
        ...


class EnhancedBrokerAdapter(BrokerAdapter, ABC):
    """
    Enhanced broker adapter with common functionality
    Provides base implementation for common broker operations
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize with config"""
        self.config = config
        self._client: BrokerHTTPClient | None = None
        self._connected = False

    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return broker name"""

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return base API URL"""

    @property
    @abstractmethod
    def auth_headers(self) -> dict[str, str]:
        """Return authentication headers"""

    def _get_client(self) -> BrokerHTTPClient:
        """Get or create HTTP client"""
        if not self._client:
            self._client = BrokerHTTPClient(base_url=self.base_url, auth_headers=self.auth_headers)
        return self._client

    def _ensure_connected(self) -> None:
        """Ensure broker connection is active"""
        if not self._connected:
            msg = f"Not connected to {self.broker_name}. Call connect() first."
            raise ConnectionError(msg)

    async def disconnect(self) -> None:
        """Disconnect from broker"""
        if self._client:
            self._client.close()
            self._client = None
        self._connected = False
        logger.info(f"Disconnected from {self.broker_name}")

    async def is_connected(self) -> bool:
        """Check connection status"""
        return self._connected

    # Common utility methods
    def _convert_to_standard_position(self, broker_position: dict[str, Any]) -> Position:
        """Convert broker-specific position to standard Position object"""
        # This should be implemented by each broker adapter
        # but can provide common field mappings
        from ...infra.model_utils import get_field_mappings

        mappings = get_field_mappings(self.broker_name)
        return create_dataclass_from_dict(broker_position, Position, mappings)

    def _convert_to_standard_order(self, broker_order: dict[str, Any]) -> OrderResponse:
        """Convert broker-specific order to standard OrderResponse object"""
        from ...infra.model_utils import get_field_mappings

        mappings = get_field_mappings(self.broker_name)
        return create_dataclass_from_dict(broker_order, OrderResponse, mappings)

    def _convert_to_standard_account(self, broker_account: dict[str, Any]) -> AccountInfo:
        """Convert broker-specific account to standard AccountInfo object"""
        from ...infra.model_utils import get_field_mappings

        mappings = get_field_mappings(self.broker_name)
        return create_dataclass_from_dict(broker_account, AccountInfo, mappings)

    # Common error handling
    def _handle_api_error(self, error: Exception, operation: str) -> None:
        """Handle and log API errors consistently"""
        logger.error(f"{self.broker_name} API error during {operation}: {error}")

        # Convert to appropriate broker error type
        from ..base import BrokerConnectionError, BrokerDataError, BrokerOrderError

        if "connection" in str(error).lower() or "timeout" in str(error).lower():
            msg = f"{self.broker_name} connection error: {error}"
            raise BrokerConnectionError(msg)
        if "order" in str(error).lower():
            msg = f"{self.broker_name} order error: {error}"
            raise BrokerOrderError(msg)
        msg = f"{self.broker_name} data error: {error}"
        raise BrokerDataError(msg)


class RESTBrokerAdapter(EnhancedBrokerAdapter):
    """
    REST API based broker adapter with common REST operations
    """

    async def _get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make GET request to broker API"""
        try:
            self._ensure_connected()
            client = self._get_client()
            response = client.get(endpoint, params=params)
            return response.json()
        except Exception as e:
            self._handle_api_error(e, f"GET {endpoint}")

    async def _get_without_connection_check(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make GET request to broker API without connection check (for initial connection)"""
        try:
            client = self._get_client()
            response = client.get(endpoint, params=params)
            return response.json()
        except Exception as e:
            self._handle_api_error(e, f"GET {endpoint}")

    async def _post(self, endpoint: str, data: dict | None = None) -> dict[str, Any]:
        """Make POST request to broker API"""
        try:
            self._ensure_connected()
            client = self._get_client()
            response = client.post(endpoint, json=data)
            return response.json()
        except Exception as e:
            self._handle_api_error(e, f"POST {endpoint}")

    async def _put(self, endpoint: str, data: dict | None = None) -> dict[str, Any]:
        """Make PUT request to broker API"""
        try:
            self._ensure_connected()
            client = self._get_client()
            response = client.put(endpoint, json=data)
            return response.json()
        except Exception as e:
            self._handle_api_error(e, f"PUT {endpoint}")

    async def _delete(self, endpoint: str) -> dict[str, Any]:
        """Make DELETE request to broker API"""
        try:
            self._ensure_connected()
            client = self._get_client()
            response = client.delete(endpoint)
            return response.json() if response.content else {}
        except Exception as e:
            self._handle_api_error(e, f"DELETE {endpoint}")


class BrokerDataCache:
    """
    Common caching mechanism for broker data
    """

    def __init__(self, default_ttl: int = 300) -> None:
        """
        Initialize cache

        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache: dict[str, dict[str, Any]] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Get cached value"""
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now().timestamp() < entry["expires"]:
                return entry["data"]
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set cached value"""
        ttl = ttl or self.default_ttl
        self._cache[key] = {"data": value, "expires": datetime.now().timestamp() + ttl}

    def clear(self) -> None:
        """Clear all cached data"""
        self._cache.clear()

    def remove(self, key: str) -> None:
        """Remove specific key from cache"""
        self._cache.pop(key, None)


class OrderValidationMixin:
    """
    Mixin for common order validation logic
    """

    @staticmethod
    def validate_order_request(order_request: OrderRequest) -> None:
        """
        Validate order request

        Args:
            order_request: Order request to validate

        Raises:
            ValueError: If order request is invalid
        """
        if not order_request.symbol:
            msg = "Symbol is required"
            raise ValueError(msg)

        if order_request.quantity <= 0:
            msg = "Quantity must be positive"
            raise ValueError(msg)

        if order_request.order_type.value == "limit" and not order_request.price:
            msg = "Limit price required for limit orders"
            raise ValueError(msg)

        if order_request.order_type.value == "stop" and not order_request.stop_price:
            msg = "Stop price required for stop orders"
            raise ValueError(msg)

        if order_request.order_type.value == "stop_limit":
            if not order_request.price:
                msg = "Limit price required for stop-limit orders"
                raise ValueError(msg)
            if not order_request.stop_price:
                msg = "Stop price required for stop-limit orders"
                raise ValueError(msg)


class PositionTrackingMixin:
    """
    Mixin for common position tracking functionality
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._position_cache = BrokerDataCache(default_ttl=60)  # 1 minute cache

    async def get_cached_positions(self, force_refresh: bool = False) -> list[Position]:
        """Get positions with caching"""
        cache_key = "positions"

        if not force_refresh:
            cached = self._position_cache.get(cache_key)
            if cached is not None:
                return cached

        # Fetch fresh positions
        positions = await self.get_positions()
        self._position_cache.set(cache_key, positions)
        return positions

    def _invalidate_position_cache(self) -> None:
        """Invalidate position cache after order execution"""
        self._position_cache.remove("positions")


class BrokerConfigurationMixin:
    """
    Mixin for common broker configuration and validation
    """

    @staticmethod
    def validate_api_credentials(api_key: str, api_secret: str, broker_name: str) -> None:
        """
        Validate API credentials for a broker

        Args:
            api_key: API key
            api_secret: API secret
            broker_name: Name of the broker for error messages

        Raises:
            ValueError: If credentials are invalid
        """
        placeholder_patterns = ["your_", "_here", "example", "test", "demo"]

        if not api_key:
            msg = f"Missing {broker_name.upper()}_API_KEY"
            raise ValueError(msg)

        if not api_secret:
            msg = f"Missing {broker_name.upper()}_SECRET_KEY"
            raise ValueError(msg)

        # Check for placeholder values
        for pattern in placeholder_patterns:
            if pattern in api_key.lower():
                msg = (
                    f"Invalid {broker_name.upper()}_API_KEY. Please:\n"
                    f"1. Sign up for {broker_name} account\n"
                    f"2. Get your API key from the dashboard\n"
                    f"3. Set {broker_name.upper()}_API_KEY in your .env file"
                )
                raise ValueError(msg)
            if pattern in api_secret.lower():
                msg = (
                    f"Invalid {broker_name.upper()}_SECRET_KEY. Please:\n"
                    f"1. Sign up for {broker_name} account\n"
                    f"2. Get your secret key from the dashboard\n"
                    f"3. Set {broker_name.upper()}_SECRET_KEY in your .env file"
                )
                raise ValueError(msg)

    @staticmethod
    def extract_broker_credentials(config: dict[str, Any], broker_name: str) -> tuple[str, str]:
        """
        Extract API credentials from config using common patterns

        Args:
            config: Configuration dictionary
            broker_name: Name of the broker

        Returns:
            Tuple of (api_key, api_secret)
        """
        api_key = config.get("api_key") or config.get(f"{broker_name}_api_key") or config.get(f"{broker_name.upper()}_API_KEY")

        api_secret = config.get("api_secret") or config.get("secret_key") or config.get(f"{broker_name}_secret_key") or config.get(f"{broker_name.upper()}_SECRET_KEY")

        return api_key, api_secret


# Update the __all__ export list
__all__ = [
    # ...existing exports...
    "BrokerConfigurationMixin",
]
