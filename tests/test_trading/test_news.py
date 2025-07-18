import os
import pytest
from src.brokers.alpaca.api import PyAlpacaAPI

api_key = os.environ.get("ALPACA_API_KEY")
api_secret = os.environ.get("ALPACA_SECRET_KEY")


@pytest.fixture
def news():
    return PyAlpacaAPI(api_key=api_key, api_secret=api_secret).trading.news


def test_get_yahoo_news(news):
    yahoo_news = news._get_yahoo_news("AAPL", limit=2)
    assert len(yahoo_news) == 2
    assert isinstance(yahoo_news, list)
    assert isinstance(yahoo_news[0], dict)
    assert "title" in yahoo_news[0]
    assert "content" in yahoo_news[0]
    assert "url" in yahoo_news[0]
    assert "publish_date" in yahoo_news[0]
    assert "source" in yahoo_news[0]
    assert yahoo_news[0]["source"] == "yahoo"


def test_get_benzinga_news(news):
    benzinga_news = news._get_benzinga_news("AAPL", limit=2)
    assert len(benzinga_news) == 2
    assert isinstance(benzinga_news, list)
    assert isinstance(benzinga_news[0], dict)
    assert "title" in benzinga_news[0]
    assert "content" in benzinga_news[0]
    assert "url" in benzinga_news[0]
    assert "publish_date" in benzinga_news[0]
    assert "source" in benzinga_news[0]
    assert benzinga_news[0]["source"] == "benzinga"
