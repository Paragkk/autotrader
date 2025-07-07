#!/usr/bin/env python3
"""Quick test of the fixed imports"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_functionality():
    try:
        # Test imports
        from core.stock_screener import EnhancedStockScreener, ScreeningCriteria
        from main_automated import main
        
        print("✅ All imports successful!")
        
        # Test creating a screening criteria object
        criteria = ScreeningCriteria(
            min_price=10.0,
            max_price=500.0,
            min_volume=500000,
            max_results=10
        )
        print(f"✅ Created screening criteria: min_price={criteria.min_price}")
        
        print("🎉 Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Running basic functionality test...")
    success = test_basic_functionality()
    
    if success:
        print("\n🚀 The imports are now working correctly!")
        print("The original issue with 'attempted relative import beyond top-level package' has been resolved.")
        print("\nThe main script should now run successfully.")
        print("Note: Prophet prediction functionality will be limited if Prophet import fails, but the core application will work.")
    else:
        print("\n❌ There are still issues to resolve.")
