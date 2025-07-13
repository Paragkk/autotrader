#!/usr/bin/env python3
"""
Test script to verify the new generic broker configuration system
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def test_generic_broker_config():
    """Test the new generic broker configuration system"""
    print("Testing generic broker configuration system...")

    try:
        from infra.config import (
            load_config,
            get_broker_config,
            get_active_brokers,
            validate_broker_env_vars,
            get_broker_env_vars,
        )

        # Test loading config
        config = load_config()
        print("✓ Configuration loaded successfully")

        # Test getting available brokers
        brokers = get_active_brokers(config)
        print(f"✓ Available brokers: {brokers}")

        # Test environment variable mappings for each broker
        for broker_name in brokers:
            print(f"\n--- Testing broker: {broker_name} ---")

            # Get environment variable mappings
            env_vars = get_broker_env_vars(broker_name, config)
            print(f"✓ Environment variable mappings: {env_vars}")

            # Test validation (this might fail if env vars are not set)
            try:
                validate_broker_env_vars(broker_name, config)
                print(f"✓ All environment variables are set for {broker_name}")

                # Try to get broker config (should work if validation passed)
                broker_config = get_broker_config(broker_name, config)
                print("✓ Broker configuration loaded successfully")
                print(f"  Base URL: {broker_config.get('base_url')}")
                print(f"  Paper trading: {broker_config.get('paper_trading')}")
                print(f"  Has API key: {'api_key' in broker_config}")
                print(f"  Has secret key: {'secret_key' in broker_config}")

            except EnvironmentError as e:
                print(f"⚠ Environment variables not set for {broker_name}: {e}")
                print(f"  Required environment variables: {list(env_vars.values())}")

        print("\n--- Testing error cases ---")

        # Test invalid broker name
        try:
            get_broker_config("invalid_broker", config)
            print("✗ Should have raised ValueError for invalid broker")
        except ValueError as e:
            print(f"✓ Correctly raised ValueError for invalid broker: {e}")

        print("\n✓ Generic configuration system tests completed!")
        return True

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def demonstrate_usage():
    """Demonstrate how to use the new generic configuration system"""
    print("\n" + "=" * 60)
    print("DEMONSTRATION: How to use the new generic config system")
    print("=" * 60)

    print("""
1. In your broker configuration (config.yaml), define environment variables:

brokers:
  my_new_broker:
    env_vars:
      api_key: "MY_BROKER_API_KEY"
      secret_key: "MY_BROKER_SECRET_KEY"
      custom_token: "MY_BROKER_CUSTOM_TOKEN"
    base_url: "https://api.mybroker.com"
    
2. Set the environment variables:
   export MY_BROKER_API_KEY="your_api_key_here"
   export MY_BROKER_SECRET_KEY="your_secret_key_here"
   export MY_BROKER_CUSTOM_TOKEN="your_custom_token_here"
   
3. Use the configuration in your code:
   
   from infra.config import get_broker_config
   
   # This will automatically load all environment variables
   # defined in the env_vars section
   broker_config = get_broker_config("my_new_broker")
   
   # Access the loaded values
   api_key = broker_config["api_key"]           # From MY_BROKER_API_KEY
   secret_key = broker_config["secret_key"]     # From MY_BROKER_SECRET_KEY
   custom_token = broker_config["custom_token"] # From MY_BROKER_CUSTOM_TOKEN
   
4. If any required environment variable is missing, 
   an EnvironmentError will be raised with details.
""")


if __name__ == "__main__":
    success = test_generic_broker_config()
    demonstrate_usage()
    sys.exit(0 if success else 1)
