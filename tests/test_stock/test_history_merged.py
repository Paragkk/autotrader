"""
Comprehensive test suite for stock history data retrieval
Merged from test_history.py and test_history2.py
"""

import pytest
import os
from datetime import datetime

import numpy as np
import pendulum

from src.brokers.alpaca.api import PyAlpacaAPI

# Environment variables for testing
api_key = os.environ.get("ALPACA_API_KEY")
api_secret = os.environ.get("ALPACA_SECRET_KEY")

today = pendulum.now(tz="America/New_York")
previous_day = today.subtract(days=2).format("YYYY-MM-DD")
month_ago = today.subtract(months=1).format("YYYY-MM-DD")


@pytest.fixture
def alpaca():
    """Full Alpaca API client fixture"""
    return PyAlpacaAPI(api_key=api_key, api_secret=api_secret, api_paper=True)


@pytest.fixture
def stock_client():
    """Stock history client fixture"""
    return PyAlpacaAPI(api_key=api_key, api_secret=api_secret).stock.history


class TestGetStockDataValidation:
    """Test input validation and error handling"""

    def test_invalid_timeframe(self, stock_client):
        with pytest.raises(ValueError, match="Invalid timeframe"):
            stock_client.get_stock_data(
                "AAPL", "2022-01-01", "2022-01-31", timeframe="invalid"
            )

    def test_limit_exceeded(self, stock_client):
        with pytest.raises(
            Exception,
            match='Request Error: {"message":"invalid limit: larger than the allowed maximum of 10000"}',
        ):
            stock_client.get_stock_data(
                "AAPL", "2022-01-01", "2022-01-31", limit=100000
            )

    def test_start_date_after_end_date(self, stock_client):
        with pytest.raises(
            Exception,
            match='Request Error: {"message":"end should not be before start"}',
        ):
            stock_client.get_stock_data(
                "AAPL", "2022-01-31", "2022-01-01", timeframe="1d"
            )

    def test_invalid_symbol(self, stock_client):
        with pytest.raises(
            Exception,
            match='Request Error: {"code":40410000,"message":"asset not found for INVALID"}',
        ):
            stock_client.get_stock_data(
                "INVALID", "2022-01-01", "2022-01-31", timeframe="1d"
            )

    def test_data_frame_shape(self, stock_client):
        df = stock_client.get_stock_data(
            "AAPL", "2022-01-01", "2022-01-31", timeframe="1d"
        )
        assert df.shape[0] > 0
        assert df.shape[1] == 9

    def test_data_frame_columns(self, stock_client):
        df = stock_client.get_stock_data(
            "AAPL", "2022-01-01", "2022-01-31", timeframe="1d"
        )
        expected_columns = [
            "symbol",
            "close",
            "high",
            "low",
            "trade_count",
            "open",
            "date",
            "volume",
            "vwap",
        ]
        assert list(df.columns) == expected_columns


class TestGetStockDataTimeframes:
    """Test different timeframe data retrieval"""

    def _assert_stock_data_structure(self, stock_data, symbol="AAPL"):
        """Helper method to validate stock data structure"""
        assert not stock_data.empty
        assert stock_data["symbol"][0] == symbol
        assert isinstance(stock_data["close"][0], float)
        assert isinstance(stock_data["open"][0], float)
        assert isinstance(stock_data["low"][0], float)
        assert isinstance(stock_data["high"][0], float)
        assert isinstance(stock_data["vwap"][0], float)
        assert isinstance(stock_data["trade_count"][0], np.int64)
        assert isinstance(stock_data["volume"][0], np.int64)
        assert isinstance(stock_data["date"][0], datetime)
        assert isinstance(stock_data["symbol"][0], str)

    def test_get_stock_data_1d(self, alpaca):
        stock_data = alpaca.stock.history.get_stock_data(
            symbol="AAPL", start=month_ago, end=previous_day, timeframe="1d"
        )
        self._assert_stock_data_structure(stock_data)

    def test_get_stock_data_1w(self, alpaca):
        stock_data = alpaca.stock.history.get_stock_data(
            symbol="AAPL", start=month_ago, end=previous_day, timeframe="1w"
        )
        self._assert_stock_data_structure(stock_data)

    def test_get_stock_data_1m(self, alpaca):
        stock_data = alpaca.stock.history.get_stock_data(
            symbol="AAPL", start=month_ago, end=previous_day, timeframe="1m"
        )
        self._assert_stock_data_structure(stock_data)

    def test_get_stock_data_5m(self, alpaca):
        stock_data = alpaca.stock.history.get_stock_data(
            symbol="AAPL", start=month_ago, end=previous_day, timeframe="5m"
        )
        self._assert_stock_data_structure(stock_data)

    def test_get_stock_data_15m(self, alpaca):
        stock_data = alpaca.stock.history.get_stock_data(
            symbol="AAPL", start=month_ago, end=previous_day, timeframe="15m"
        )
        self._assert_stock_data_structure(stock_data)

    def test_get_stock_data_30m(self, alpaca):
        stock_data = alpaca.stock.history.get_stock_data(
            symbol="AAPL", start=month_ago, end=previous_day, timeframe="30m"
        )
        self._assert_stock_data_structure(stock_data)

    def test_get_stock_data_1h(self, alpaca):
        stock_data = alpaca.stock.history.get_stock_data(
            symbol="AAPL", start=month_ago, end=previous_day, timeframe="1h"
        )
        self._assert_stock_data_structure(stock_data)

    def test_get_stock_data_4h(self, alpaca):
        stock_data = alpaca.stock.history.get_stock_data(
            symbol="AAPL", start=month_ago, end=previous_day, timeframe="4h"
        )
        self._assert_stock_data_structure(stock_data)
