# Example: Adding a New Broker to the Generic Configuration System

## Step 1: Add broker configuration to config.yaml

```yaml
brokers:
  # Existing brokers...
  
  # New broker example
  td_ameritrade:
    env_vars:
      api_key: "TD_AMERITRADE_API_KEY"
      secret_key: "TD_AMERITRADE_SECRET_KEY"
      refresh_token: "TD_AMERITRADE_REFRESH_TOKEN"
      account_id: "TD_AMERITRADE_ACCOUNT_ID"
    base_url: "https://api.tdameritrade.com/v1"
    paper_trading: false
    order_timeout: 90
    max_order_retries: 2
    
  binance:
    env_vars:
      api_key: "BINANCE_API_KEY"
      secret_key: "BINANCE_SECRET_KEY"
    base_url: "https://api.binance.com"
    paper_trading: false
    testnet_url: "https://testnet.binance.vision"
    
  custom_broker:
    env_vars:
      username: "CUSTOM_BROKER_USERNAME"
      password: "CUSTOM_BROKER_PASSWORD"
      token: "CUSTOM_BROKER_TOKEN"
      client_id: "CUSTOM_BROKER_CLIENT_ID"
    base_url: "https://api.custombroker.com/v2"
    paper_trading: true
```

## Step 2: Set environment variables

```bash
# For TD Ameritrade
export TD_AMERITRADE_API_KEY="your_td_api_key_here"
export TD_AMERITRADE_SECRET_KEY="your_td_secret_key_here"
export TD_AMERITRADE_REFRESH_TOKEN="your_refresh_token_here"
export TD_AMERITRADE_ACCOUNT_ID="your_account_id_here"

# For Binance
export BINANCE_API_KEY="your_binance_api_key_here"
export BINANCE_SECRET_KEY="your_binance_secret_key_here"

# For Custom Broker
export CUSTOM_BROKER_USERNAME="your_username_here"
export CUSTOM_BROKER_PASSWORD="your_password_here"
export CUSTOM_BROKER_TOKEN="your_token_here"
export CUSTOM_BROKER_CLIENT_ID="your_client_id_here"
```

## Step 3: Use in your code

```python
from infra.config import get_broker_config, validate_broker_env_vars

# Get TD Ameritrade configuration
try:
    td_config = get_broker_config("td_ameritrade")
    print(f"TD API Key: {td_config['api_key']}")
    print(f"TD Account ID: {td_config['account_id']}")
    print(f"TD Base URL: {td_config['base_url']}")
except EnvironmentError as e:
    print(f"TD Ameritrade not configured: {e}")

# Get Binance configuration
try:
    binance_config = get_broker_config("binance")
    print(f"Binance API Key: {binance_config['api_key']}")
    print(f"Binance Base URL: {binance_config['base_url']}")
except EnvironmentError as e:
    print(f"Binance not configured: {e}")

# Validate before using
try:
    validate_broker_env_vars("custom_broker")
    custom_config = get_broker_config("custom_broker")
    # Use custom_config...
except EnvironmentError as e:
    print(f"Custom broker not ready: {e}")
```

## Benefits of the Generic System

1. **No Code Changes**: Adding new brokers requires no changes to the configuration loading code
2. **Clear Error Messages**: Missing environment variables are clearly identified
3. **Flexible Naming**: Each broker can use its own environment variable naming convention
4. **Easy Validation**: Built-in validation ensures all required credentials are present
5. **Consistent Interface**: All brokers are accessed using the same pattern

## Migration from Old System

The old hardcoded system:
```python
# Old way - hardcoded for each broker
if broker_name == "alpaca":
    broker_config["api_key"] = os.getenv("ALPACA_API_KEY")
    broker_config["secret_key"] = os.getenv("ALPACA_SECRET_KEY")
elif broker_name == "interactive_brokers":
    broker_config["api_key"] = os.getenv("IB_API_KEY")
    broker_config["secret_key"] = os.getenv("IB_SECRET_KEY")
# Need to add more elif statements for each new broker...
```

The new generic system:
```python
# New way - completely generic
env_vars = broker_config.get("env_vars", {})
for config_key, env_var_name in env_vars.items():
    env_value = os.getenv(env_var_name)
    if env_value is None:
        missing_env_vars.append(env_var_name)
    else:
        broker_config[config_key] = env_value
```

This scales automatically to any number of brokers without code changes!
