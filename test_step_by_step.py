#!/usr/bin/env python3
"""Test script to identify which import is causing the hang"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports_step_by_step():
    imports_to_test = [
        "core.stock_screener",
        "core.strategy_engine", 
        "core.signal_aggregator",
        "core.risk_management",
        "core.stock_scorer",
        "core.order_executor",
        "core.position_monitor",
        "infra.logging_config",
        "brokers.alpaca.adapter",
        "main_automated"
    ]
    
    for module_name in imports_to_test:
        try:
            print(f"Testing import: {module_name}")
            __import__(module_name)
            print(f"✅ {module_name} imported successfully")
        except Exception as e:
            print(f"❌ {module_name} import failed: {e}")
            import traceback
            traceback.print_exc()
            break

if __name__ == "__main__":
    test_imports_step_by_step()
