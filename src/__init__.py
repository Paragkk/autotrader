"""
AutoTrader Pro - Main Package
Professional Automated Trading System
"""

import sys
from pathlib import Path

# Ensure src directory is in the Python path for absolute imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

__version__ = "2.0.0"
__author__ = "AutoTrader Pro Team"
