#!/usr/bin/env python3
"""
Test script to verify the broker reorganization (minimal)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

print("Testing broker reorganization (minimal)...")

try:
    print("1. Testing base broker imports...")
    from brokers.base import BrokerAdapter, OrderRequest, OrderResponse  # noqa: F401

    print("   ✓ Base broker imports successful")

    print("2. Testing direct adapter import...")
    from brokers.alpaca.adapter import AlpacaBrokerAdapter  # noqa: F401

    print("   ✓ AlpacaBrokerAdapter import successful")

    print("3. Testing adapter instantiation...")
    adapter = AlpacaBrokerAdapter("test_key", "test_secret", paper_trading=True)
    print(f"   ✓ AlpacaBrokerAdapter created: {adapter.broker_name}")

    print("\n✅ Broker reorganization verification complete!")
    print("📁 New structure:")
    print("   src/brokers/alpaca/")
    print("   ├── __init__.py")
    print("   ├── adapter.py")
    print("   └── api/")
    print("       ├── __init__.py")
    print("       ├── trading/")
    print("       ├── stock/")
    print("       ├── models/")
    print("       └── http/")

except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Unexpected error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
