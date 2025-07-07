#!/usr/bin/env python3
"""Simple test to see if main can be imported and called"""

import sys
from pathlib import Path
import asyncio

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_main():
    try:
        from main_automated import main
        print("✅ Main function imported successfully")
        
        # Try to call it but with a timeout
        print("🔄 Attempting to call main function...")
        await asyncio.wait_for(main(), timeout=5.0)
        print("✅ Main function executed successfully")
        
    except asyncio.TimeoutError:
        print("⚠️  Main function timed out after 5 seconds - this is expected for long-running services")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_main())
