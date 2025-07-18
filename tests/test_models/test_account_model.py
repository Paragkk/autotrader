from src.brokers.alpaca.api.models.account_model import (
    AccountModel,
    account_class_from_dict,
)
import pendulum


def test_account_class_from_dict():
    data_dict = {
        "id": "12345678",
        "account_number": "ABC123",
        "status": "ACTIVE",
        "crypto_status": "ENABLED",
        "options_approved_level": 2,
        "options_trading_level": 3,
        "currency": "USD",
        "buying_power": 10000.0,
        "regt_buying_power": 5000.0,
        "daytrading_buying_power": 2000.0,
        "effective_buying_power": 8000.0,
        "non_marginable_buying_power": 6000.0,
        "options_buying_power": 4000.0,
        "bod_dtbp": 1000.0,
        "cash": 5000.0,
        "accrued_fees": 100.0,
        "pending_transfer_in": 200.0,
        "portfolio_value": 15000.0,
        "pattern_day_trader": False,
        "trading_blocked": False,
        "transfers_blocked": False,
        "account_blocked": False,
        "created_at": "2022-01-01",
        "trade_suspended_by_user": False,
        "multiplier": 1,
        "shorting_enabled": True,
        "equity": 10000.0,
        "last_equity": 9000.0,
        "long_market_value": 8000.0,
        "short_market_value": 2000.0,
        "position_market_value": 10000.0,
        "initial_margin": 5000.0,
        "maintenance_margin": 4000.0,
        "last_maintenance_margin": 3000.0,
        "sma": 2000.0,
        "daytrade_count": 5,
        "balance_asof": "2022-01-01",
        "crypto_tier": 1,
        "intraday_adjustments": 2,
        "pending_reg_taf_fees": 50.0,
    }

    expected_account = AccountModel(
        id="12345678",
        account_number="ABC123",
        status="ACTIVE",
        crypto_status="ENABLED",
        options_approved_level=2,
        options_trading_level=3,
        currency="USD",
        buying_power=10000.0,
        regt_buying_power=5000.0,
        daytrading_buying_power=2000.0,
        effective_buying_power=8000.0,
        non_marginable_buying_power=6000.0,
        options_buying_power=4000.0,
        bod_dtbp=1000.0,
        cash=5000.0,
        accrued_fees=100.0,
        pending_transfer_in=200.0,
        portfolio_value=15000.0,
        pattern_day_trader=False,
        trading_blocked=False,
        transfers_blocked=False,
        account_blocked=False,
        created_at=pendulum.DateTime(
            2022, 1, 1, tzinfo=pendulum.Timezone("America/New_York")
        ).strftime("%Y-%m-%d %H:%M:%S"),
        trade_suspended_by_user=False,
        multiplier=1,
        shorting_enabled=True,
        equity=10000.0,
        last_equity=9000.0,
        long_market_value=8000.0,
        short_market_value=2000.0,
        position_market_value=10000.0,
        initial_margin=5000.0,
        maintenance_margin=4000.0,
        last_maintenance_margin=3000.0,
        sma=2000.0,
        daytrade_count=5,
        balance_asof="2022-01-01",
        crypto_tier=1,
        intraday_adjustments=2,
        pending_reg_taf_fees=50.0,
    )

    assert account_class_from_dict(data_dict) == expected_account
