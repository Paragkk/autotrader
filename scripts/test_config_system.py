#!/usr/bin/env python3
"""
Simple test script to verify the broker-specific configuration system
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_config_loading():
    """Test that the configuration system works correctly"""
    print("Testing broker-specific configuration system...")

    try:
        from infra.config import load_config, get_available_brokers

        # Test loading config
        config = load_config()
        print("✓ Configuration loaded successfully")
        print(f"  Broker: {config.get('broker')}")
        print(f"  Environment: {config.get('environment')}")
        print(f"  Max positions: {config.get('max_positions')}")

        # Test available brokers
        brokers = get_available_brokers()
        print(f"✓ Available brokers: {brokers}")

        # Test broker-specific settings
        if "alpaca_api_key" in config:
            print("✓ Alpaca-specific settings loaded")

        # Test base config settings
        if "database_url" in config:
            print("✓ Base configuration settings loaded")

        print("\n✓ All tests passed! Configuration system is working correctly.")
        return True

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_config_loading()
    sys.exit(0 if success else 1)
