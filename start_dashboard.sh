#!/bin/bash

echo
echo "========================================"
echo "   Starting AutoTrader Pro Dashboard"
echo "========================================"
echo
echo "Dashboard will be available at: http://localhost:8501"
echo "Press Ctrl+C to stop the dashboard"
echo

export AUTOTRADER_API_BASE_URL="http://localhost:8080"
uv run streamlit run src/dashboard/main.py --server.port 8501 --theme.base dark
