"""
Comprehensive test suite for data model conversions
Merged from test_order_model.py and test_position_model.py
"""

import pytest
import pendulum
from src.brokers.alpaca.api.models.order_model import order_class_from_dict
from src.brokers.alpaca.api.models.position_model import position_class_from_dict


class TestOrderModel:
    """Test order model conversion functionality"""

    def test_order_class_from_dict_with_empty_dict(self):
        data_dict = {}
        with pytest.raises(KeyError):
            order_class_from_dict(data_dict)

    def test_order_class_from_dict_with_missing_required_keys(self):
        data_dict = {"some_key": "some_value"}
        with pytest.raises(KeyError):
            order_class_from_dict(data_dict)

    def test_order_class_from_dict_with_invalid_leg_data(self):
        data_dict = {
            "id": "order_123",
            "client_order_id": "client_order_123",
            "asset_class": "equity",
            "legs": [{"invalid_key": "invalid_value"}],
        }
        with pytest.raises(KeyError):
            order_class_from_dict(data_dict)

    def test_order_class_from_dict_with_valid_data(self):
        data_dict = {
            "id": "order_123",
            "client_order_id": "client_order_123",
            "created_at": "2023-05-01T12:00:00Z",
            "updated_at": "2023-05-01T12:00:01Z",
            "submitted_at": "2023-05-01T12:00:02Z",
            "filled_at": "2023-05-01T12:00:03Z",
            "expired_at": "2023-05-01T12:00:04Z",
            "canceled_at": "2023-05-01T12:00:05Z",
            "failed_at": "2023-05-01T12:00:06Z",
            "replaced_at": "2023-05-01T12:00:07Z",
            "replaced_by": "order_456",
            "replaces": "order_789",
            "asset_id": "asset_123",
            "symbol": "AAPL",
            "asset_class": "equity",
            "notional": 10000.0,
            "qty": 100.0,
            "filled_qty": 50.0,
            "filled_avg_price": 100.0,
            "order_class": "simple",
            "order_type": "market",
            "type": "market",
            "side": "buy",
            "time_in_force": "day",
            "limit_price": 110.0,
            "stop_price": 90.0,
            "status": "partially_filled",
            "extended_hours": False,
            "legs": [
                {
                    "id": "leg_1",
                    "client_order_id": "client_order_leg_1",
                    "created_at": "2023-05-01T12:00:00Z",
                    "updated_at": "2023-05-01T12:00:01Z",
                    "submitted_at": "2023-05-01T12:00:02Z",
                    "filled_at": "2023-05-01T12:00:03Z",
                    "expired_at": "2023-05-01T12:00:04Z",
                    "canceled_at": "2023-05-01T12:00:05Z",
                    "failed_at": "2023-05-01T12:00:06Z",
                    "replaced_at": "2023-05-01T12:00:07Z",
                    "replaced_by": "leg_2",
                    "replaces": "leg_3",
                    "asset_id": "asset_123",
                    "symbol": "AAPL",
                    "asset_class": "equity",
                    "notional": 5000.0,
                    "qty": 50.0,
                    "filled_qty": 25.0,
                    "filled_avg_price": 100.0,
                    "order_class": "simple",
                    "order_type": "market",
                    "type": "market",
                    "side": "buy",
                    "time_in_force": "day",
                    "limit_price": 110.0,
                    "stop_price": 90.0,
                    "status": "partially_filled",
                    "extended_hours": False,
                    "legs": [],
                    "trail_percent": 0.0,
                    "trail_price": 0.0,
                    "hwm": 0.0,
                    "subtag": "",
                    "source": "web",
                }
            ],
            "trail_percent": 0.0,
            "trail_price": 0.0,
            "hwm": 0.0,
            "subtag": "",
            "source": "web",
        }

        order = order_class_from_dict(data_dict)
        assert order.id == "order_123"
        assert order.client_order_id == "client_order_123"
        assert order.created_at == pendulum.DateTime(
            2023, 5, 1, 12, 0, 0, tzinfo=pendulum.Timezone("UTC")
        ).strftime("%Y-%m-%d %H:%M:%S")
        assert order.updated_at == pendulum.DateTime(
            2023, 5, 1, 12, 0, 1, tzinfo=pendulum.Timezone("UTC")
        ).strftime("%Y-%m-%d %H:%M:%S")
        assert order.submitted_at == pendulum.DateTime(
            2023, 5, 1, 12, 0, 2, tzinfo=pendulum.Timezone("UTC")
        ).strftime("%Y-%m-%d %H:%M:%S")
        assert order.filled_at == pendulum.DateTime(
            2023, 5, 1, 12, 0, 3, tzinfo=pendulum.Timezone("UTC")
        ).strftime("%Y-%m-%d %H:%M:%S")
        assert order.expired_at == pendulum.DateTime(
            2023, 5, 1, 12, 0, 4, tzinfo=pendulum.Timezone("UTC")
        ).strftime("%Y-%m-%d %H:%M:%S")
        assert order.canceled_at == pendulum.DateTime(
            2023, 5, 1, 12, 0, 5, tzinfo=pendulum.Timezone("UTC")
        ).strftime("%Y-%m-%d %H:%M:%S")
        assert order.failed_at == pendulum.DateTime(
            2023, 5, 1, 12, 0, 6, tzinfo=pendulum.Timezone("UTC")
        ).strftime("%Y-%m-%d %H:%M:%S")
        assert order.replaced_at == pendulum.DateTime(
            2023, 5, 1, 12, 0, 7, tzinfo=pendulum.Timezone("UTC")
        ).strftime("%Y-%m-%d %H:%M:%S")
        assert order.replaced_by == "order_456"
        assert order.replaces == "order_789"
        assert order.asset_id == "asset_123"
        assert order.symbol == "AAPL"
        assert order.asset_class == "equity"
        assert order.notional == 10000.0
        assert order.qty == 100.0
        assert order.filled_qty == 50.0
        assert order.filled_avg_price == 100.0
        assert order.order_class == "simple"
        assert order.order_type == "market"
        assert order.type == "market"
        assert order.side == "buy"
        assert order.time_in_force == "day"
        assert order.limit_price == 110.0
        assert order.stop_price == 90.0
        assert order.status == "partially_filled"
        assert order.extended_hours is False
        assert len(order.legs) == 1
        assert order.legs[0].id == "leg_1"
        assert order.legs[0].client_order_id == "client_order_leg_1"


class TestPositionModel:
    """Test position model conversion functionality"""

    def test_handles_missing_optional_fields_with_default_value(self):
        data_dict = {
            "asset_id": "123",
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "class": "equity",
            "avg_entry_price": 150.0,
            "qty": 10.0,
            "qty_available": 10.0,
            "side": "long",
            "market_value": 1500.0,
            "cost_basis": 1500.0,
            "profit_dol": 100.0,
            "profit_pct": 0.0667,
            "intraday_profit_dol": 10.0,
            "intraday_profit_pct": 0.0067,
            "portfolio_pct": 0.1,
            "current_price": 155.0,
            "lastday_price": 150.0,
            "change_today": 0.0333,
            "asset_marginable": False,
        }
        position = position_class_from_dict(data_dict)
        assert position.asset_id == "123"
        assert position.symbol == "AAPL"
        assert position.exchange == "NASDAQ"
        assert position.asset_class == "equity"
        assert position.avg_entry_price == 150.0
        assert position.qty == 10.0
        assert position.qty_available == 10.0
        assert position.side == "long"
        assert position.market_value == 1500.0
        assert position.cost_basis == 1500.0
        assert position.profit_dol == 100.0
        assert position.profit_pct == 0.0667
        assert position.intraday_profit_dol == 10.0
        assert position.intraday_profit_pct == 0.0067
        assert position.portfolio_pct == 0.1
        assert position.current_price == 155.0
        assert position.lastday_price == 150.0
        assert position.change_today == 0.0333
        assert position.asset_marginable is False

    def test_converts_valid_dict_to_position_model(self):
        data_dict = {
            "asset_id": "123",
            "symbol": "AAPL",
            "exchange": "NASDAQ",
            "class": "equity",
            "avg_entry_price": 150.0,
            "qty": 10.0,
            "qty_available": 10.0,
            "side": "long",
            "market_value": 1500.0,
            "cost_basis": 1500.0,
            "profit_dol": 100.0,
            "profit_pct": 0.0667,
            "intraday_profit_dol": 10.0,
            "intraday_profit_pct": 0.0067,
            "portfolio_pct": 0.1,
            "current_price": 155.0,
            "lastday_price": 150.0,
            "change_today": 0.0333,
            "asset_marginable": True,
        }
        position = position_class_from_dict(data_dict)
        assert position.asset_id == "123"
        assert position.symbol == "AAPL"
        assert position.exchange == "NASDAQ"
        assert position.asset_class == "equity"
        assert position.avg_entry_price == 150.0
        assert position.qty == 10.0
        assert position.qty_available == 10.0
        assert position.side == "long"
        assert position.market_value == 1500.0
        assert position.cost_basis == 1500.0
        assert position.profit_dol == 100.0
        assert position.profit_pct == 0.0667
        assert position.intraday_profit_dol == 10.0
        assert position.intraday_profit_pct == 0.0067
        assert position.portfolio_pct == 0.1
        assert position.current_price == 155.0
        assert position.lastday_price == 150.0
        assert position.change_today == 0.0333
        assert position.asset_marginable is True
