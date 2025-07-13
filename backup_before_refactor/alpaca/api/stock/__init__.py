from typing import Dict
from .latest_quote import LatestQuote
from .predictor import Predictor
from ..trading.market import Market
from .assets import Assets
from .history import History
from .screener import Screener


class Stock:
    def __init__(
        self, api_key: str, api_secret: str, api_paper: bool, market: Market
    ) -> None:
        headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
        }
        base_url = (
            "https://paper-api.alpaca.markets/v2"
            if api_paper
            else "https://api.alpaca.markets/v2"
        )
        data_url = "https://data.alpaca.markets/v2"
        self._initialize_components(
            headers=headers, base_url=base_url, data_url=data_url, market=market
        )

        self._initialize_components(
            headers=headers,
            base_url=base_url,
            data_url=data_url,
            market=market,
        )

    def _initialize_components(
        self,
        headers: Dict[str, str],
        base_url: str,
        data_url: str,
        market: Market,
    ):
        self.assets = Assets(headers=headers, base_url=base_url)
        self.history = History(headers=headers, data_url=data_url, asset=self.assets)
        self.screener = Screener(
            data_url=data_url, headers=headers, market=market, asset=self.assets
        )
        self.predictor = Predictor(history=self.history, screener=self.screener)
        self.latest_quote = LatestQuote(headers=headers)
