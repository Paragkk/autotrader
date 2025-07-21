#!/usr/bin/env python3
"""
Entry point for AutoTrader Pro API
This module properly sets up the Python path and imports the FastAPI app
"""

import sys
from pathlib import Path

# Get the project root and src directories
project_root = Path(__file__).parent
src_dir = project_root / "src"

# Add src directory to Python path for absolute imports
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Now import the FastAPI app with the correct path setup
from api.main import app  # noqa: E402

# Export the app for uvicorn to find
__all__ = ["app"]
