# Generic Broker System Documentation

## Overview

The automated trading system now supports a generic broker architecture that allows you to easily add new brokers without modifying the core system code. The system automatically discovers and loads broker configurations from their respective directories.

## How It Works

1. **Broker Discovery**: The system scans the `src/brokers/` directory for subdirectories containing both `config.yaml` and `adapter.py` files.

2. **Configuration Loading**: Each broker has its own `config.yaml` file with broker-specific settings that are automatically loaded and merged with global configuration.

3. **Dynamic Loading**: Broker adapters are dynamically imported and instantiated using Python's importlib.

4. **Generic Factory**: The `BrokerFactory` class handles the creation of broker instances without hard-coding specific broker types.

## Directory Structure

```
src/brokers/
├── base/                    # Base classes and factory
│   ├── config.py           # Generic configuration loader
│   ├── factory.py          # Broker factory
│   └── interface.py        # Base broker interface
├── alpaca/                 # Alpaca broker implementation
│   ├── adapter.py          # AlpacaBrokerAdapter class
│   ├── config.yaml         # Alpaca-specific configuration
│   └── __init__.py
├── demo_broker/            # Example broker implementation
│   ├── adapter.py          # Demo_brokerBrokerAdapter class
│   ├── config.yaml         # Demo broker configuration
│   └── __init__.py
└── your_broker/            # Your new broker (follow this pattern)
    ├── adapter.py          # YourBrokerBrokerAdapter class
    ├── config.yaml         # Your broker configuration
    └── __init__.py
```

## Adding a New Broker

To add a new broker, follow these steps:

### 1. Create Broker Directory

Create a new directory under `src/brokers/` with your broker's name (e.g., `interactive_brokers`, `td_ameritrade`, etc.):

```
src/brokers/your_broker_name/
```

### 2. Create Configuration File

Create a `config.yaml` file with your broker-specific settings:

```yaml
# Example: src/brokers/your_broker_name/config.yaml
your_broker_api_key: your_api_key_here
your_broker_secret_key: your_secret_key_here
base_url: https://api.yourbroker.com
use_paper_trading: true
order_timeout: 60
max_order_retries: 3
# Add any other broker-specific settings
```

### 3. Create Adapter Class

Create an `adapter.py` file with your broker adapter implementation:

```python
# Example: src/brokers/your_broker_name/adapter.py
from typing import Dict, Any
from brokers.base import BrokerAdapter
# Import other required classes...

class Your_broker_nameBrokerAdapter(BrokerAdapter):
    def __init__(self, config: Dict[str, Any]):
        # Extract configuration
        self.api_key = config.get("api_key") or config.get("your_broker_api_key")
        self.api_secret = config.get("api_secret") or config.get("your_broker_secret_key")
        
        # Validate required fields
        if not self.api_key:
            raise ValueError("Missing required configuration: api_key")
        # ... validation logic
        
        self.config = config
        self._connected = False

    @property
    def broker_name(self) -> str:
        return "your_broker_name"

    # Implement all required methods from BrokerAdapter
    async def connect(self) -> bool:
        # Your connection logic
        pass

    async def get_account(self) -> AccountInfo:
        # Your account info logic
        pass

    # ... implement other required methods
```

### 4. Create Package Init File

Create an `__init__.py` file:

```python
# src/brokers/your_broker_name/__init__.py
"""
Your Broker Package
"""
```

### 5. Update Main Configuration

In your main `config.yaml`, specify the broker:

```yaml
broker:
  name: your_broker_name
  api_key: ${YOUR_BROKER_API_KEY}  # Override broker-specific config
  secret_key: ${YOUR_BROKER_SECRET_KEY}
  paper_trading: true
```

## Class Naming Convention

**Important**: The adapter class must follow the naming convention:
`{Broker_Name}BrokerAdapter`

Where `{Broker_Name}` is the title-cased version of your broker directory name:
- Directory: `alpaca` → Class: `AlpacaBrokerAdapter`
- Directory: `demo_broker` → Class: `Demo_brokerBrokerAdapter`
- Directory: `interactive_brokers` → Class: `Interactive_brokersBrokerAdapter`

## Configuration Merging

The system merges configurations in this order (later values override earlier ones):

1. Broker-specific `config.yaml` (from broker directory)
2. Global broker configuration (from main `config.yaml`)

This allows you to:
- Set default values in the broker's `config.yaml`
- Override specific values in the main configuration
- Use environment variables for sensitive data

## Example Usage

After adding your broker, the system will automatically discover it:

```python
from brokers.base.factory import get_supported_brokers, get_broker_adapter

# List all available brokers
print(get_supported_brokers())  # ['alpaca', 'demo_broker', 'your_broker_name']

# Create broker adapter
broker_config = {
    "name": "your_broker_name",
    "api_key": "your_key",
    "secret_key": "your_secret"
}
adapter = get_broker_adapter("your_broker_name", broker_config)
```

## Error Handling

The system provides clear error messages for common issues:

- **Unsupported broker**: Lists available brokers
- **Missing configuration**: Specifies which fields are required
- **Import errors**: Shows module import failures
- **Configuration validation**: Reports invalid configuration

## Testing Your Broker

You can test your new broker adapter:

```python
# Test broker discovery
from brokers.base.factory import get_supported_brokers
assert "your_broker_name" in get_supported_brokers()

# Test broker creation
from brokers.base.factory import get_broker_adapter
config = {"name": "your_broker_name", "api_key": "test", "secret_key": "test"}
adapter = get_broker_adapter("your_broker_name", config)
assert adapter.broker_name == "your_broker_name"
```

## Benefits of This Architecture

1. **Modularity**: Each broker is self-contained
2. **Extensibility**: Easy to add new brokers without changing core code
3. **Configuration**: Flexible configuration system with overrides
4. **Discovery**: Automatic broker discovery
5. **Validation**: Built-in configuration validation
6. **Error Handling**: Clear error messages for troubleshooting

This generic system makes it easy to support multiple brokers and allows the trading system to be broker-agnostic.
