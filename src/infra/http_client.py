"""
Common HTTP Client Infrastructure
Extracted from broker-specific implementations
"""

from typing import Dict, Optional, Any
import logging
from abc import ABC, abstractmethod

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

logger = logging.getLogger(__name__)


class HTTPClientError(Exception):
    """Base HTTP client error"""

    pass


class HTTPClientConnectionError(HTTPClientError):
    """HTTP connection error"""

    pass


class HTTPClientTimeoutError(HTTPClientError):
    """HTTP timeout error"""

    pass


class BaseHTTPClient(ABC):
    """Abstract base class for HTTP clients"""

    @abstractmethod
    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> requests.Response:
        """Make HTTP request"""
        pass


class ReliableHTTPClient(BaseHTTPClient):
    """
    Production-ready HTTP client with retry logic, timeouts, and error handling
    """

    def __init__(
        self,
        timeout: int = 30,
        retries: int = 3,
        backoff_factor: float = 2.0,
        retry_statuses: list = None,
        acceptable_statuses: list = None,
    ):
        """
        Initialize HTTP client with retry strategy

        Args:
            timeout: Request timeout in seconds
            retries: Number of retry attempts
            backoff_factor: Backoff factor for retries
            retry_statuses: HTTP status codes to retry on
            acceptable_statuses: HTTP status codes considered successful
        """
        if retry_statuses is None:
            retry_statuses = [429, 500, 502, 503, 504]

        if acceptable_statuses is None:
            acceptable_statuses = [200, 201, 204, 207]

        self.timeout = timeout
        self.acceptable_statuses = acceptable_statuses

        # Configure retry strategy
        self.retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=retry_statuses,
            allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        )

        # Setup session with retry adapter
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=self.retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> requests.Response:
        """
        Make HTTP request with error handling

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Optional headers
            params: Optional query parameters
            json: Optional JSON payload
            **kwargs: Additional request arguments

        Returns:
            Response object

        Raises:
            HTTPClientError: For various HTTP errors
        """
        try:
            logger.debug(f"Making {method} request to {url}")

            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                timeout=self.timeout,
                **kwargs,
            )

            # Check if response status is acceptable
            if response.status_code not in self.acceptable_statuses:
                logger.error(f"HTTP {response.status_code}: {response.text}")
                raise HTTPClientError(
                    f"Request failed with status {response.status_code}: {response.text}"
                )

            logger.debug(f"Request successful: {response.status_code}")
            return response

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise HTTPClientTimeoutError(f"Request timeout: {e}")

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise HTTPClientConnectionError(f"Connection error: {e}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise HTTPClientError(f"Request error: {e}")

    def get(self, url: str, **kwargs) -> requests.Response:
        """Make GET request"""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """Make POST request"""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        """Make PUT request"""
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        """Make DELETE request"""
        return self.request("DELETE", url, **kwargs)

    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()


class BrokerHTTPClient(ReliableHTTPClient):
    """
    HTTP client specifically configured for broker APIs
    """

    def __init__(self, base_url: str, auth_headers: Dict[str, str], **kwargs):
        """
        Initialize broker HTTP client

        Args:
            base_url: Base URL for the broker API
            auth_headers: Authentication headers
            **kwargs: Additional HTTPClient arguments
        """
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self.auth_headers = auth_headers or {}

        # Set default headers for all requests
        self.session.headers.update(self.auth_headers)

    def request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> requests.Response:
        """
        Make request to broker API endpoint

        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base_url)
            headers: Optional additional headers
            **kwargs: Additional request arguments

        Returns:
            Response object
        """
        # Combine base URL with endpoint
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Merge headers
        request_headers = self.auth_headers.copy()
        if headers:
            request_headers.update(headers)

        return super().request(method, url, headers=request_headers, **kwargs)
