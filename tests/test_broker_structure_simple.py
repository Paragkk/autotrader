#!/usr/bin/env python3
"""
Test script to verify the broker reorganization
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

print("Testing broker reorganization...")

try:
    print("1. Testing base broker imports...")
    from brokers.base import BrokerAdapter, OrderRequest, OrderResponse  # noqa: F401

    print("   ✓ Base broker imports successful")

    print("2. Testing Alpaca API import...")
    from brokers.alpaca.api import PyAlpacaAPI  # noqa: F401

    print("   ✓ PyAlpacaAPI import successful")

    print("3. Testing Alpaca adapter import...")
    from brokers.alpaca.adapter import AlpacaBrokerAdapter  # noqa: F401

    print("   ✓ AlpacaBrokerAdapter import successful")

    print("4. Testing Alpaca package import...")
    from brokers.alpaca import AlpacaBrokerAdapter as AlpacaBrokerAdapter2  # noqa: F401

    print("   ✓ Alpaca package import successful")

    print("\n✅ All imports successful - broker reorganization complete!")

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
