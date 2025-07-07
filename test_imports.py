#!/usr/bin/env python3
"""Test script to verify imports are working correctly"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_stock_screener_import():
    try:
        from core.stock_screener import EnhancedStockScreener, ScreeningCriteria
        print("✅ Stock screener imports successful")
        return True
    except Exception as e:
        print(f"❌ Stock screener import failed: {e}")
        return False

def test_main_automated_import():
    try:
        from main_automated import main
        print("✅ Main automated imports successful")
        return True
    except Exception as e:
        print(f"❌ Main automated import failed: {e}")
        return False

def test_individual_imports():
    imports_to_test = [
        ("core.strategy_engine", "StrategyEngine"),
        ("core.signal_aggregator", "SignalAggregator"),
        ("core.risk_management", "RiskManager"),
        ("core.stock_scorer", "StockScorer"),
        ("core.order_executor", "OrderExecutor"),
        ("core.position_monitor", "PositionMonitor"),
    ]
    
    for module_name, class_name in imports_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {module_name}.{class_name} imported successfully")
        except Exception as e:
            print(f"❌ {module_name}.{class_name} import failed: {e}")

if __name__ == "__main__":
    print("Testing imports...\n")
    
    test_stock_screener_import()
    test_individual_imports()
    
    print("\nTesting main module import...")
    test_main_automated_import()
    
    print("\nImport tests completed.")
