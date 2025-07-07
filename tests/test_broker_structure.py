#!/usr/bin/env python3
"""
Test script to verify the broker reorganization
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    from brokers.alpaca.api import PyAlpacaAPI  # noqa: F401

    print("✓ Successfully imported PyAlpacaAPI from new location")

    from brokers.alpaca.adapter import AlpacaBrokerAdapter  # noqa: F401

    print("✓ Successfully imported AlpacaBrokerAdapter")

    from brokers.alpaca import AlpacaBrokerAdapter as AlpacaBrokerAdapter2  # noqa: F401

    print("✓ Successfully imported AlpacaBrokerAdapter from broker package")

    print("\n✓ All imports successful - broker reorganization complete!")

except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)
