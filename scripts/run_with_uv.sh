#!/bin/bash
# AutoTrader Pro - UV Execution Script for Linux/macOS
# This script provides easy commands to run various components using uv

if [ $# -eq 0 ]; then
    cat << EOF

╔═════════════════════════════════════════════════╗
║              AutoTrader Pro - UV Runner        ║
╚═════════════════════════════════════════════════╝

Usage: ./scripts/run_with_uv.sh [command]

Available commands:
  api        - Start FastAPI server only
  dashboard  - Start Streamlit dashboard only  
  complete   - Start complete system (API + Dashboard)
  main       - Start main trading system
  test       - Run test suite
  config     - Test configuration system

EOF
    exit 1
fi

case "$1" in
    "api")
        echo "Starting AutoTrader Pro API with uv..."
        uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --reload
        ;;
    "dashboard")
        echo "Starting AutoTrader Pro Dashboard with uv..."
        uv run streamlit run src/dashboard/main.py --server.port 8501 --server.address 0.0.0.0
        ;;
    "complete")
        echo "Starting AutoTrader Pro Complete System with uv..."
        uv run python run_complete.py
        ;;
    "main")
        echo "Starting AutoTrader Pro Main System with uv..."
        uv run python src/main_automated.py
        ;;
    "test")
        echo "Running AutoTrader Pro Tests with uv..."
        uv run python -m pytest tests/ -v
        ;;
    "config")
        echo "Testing Configuration System with uv..."
        uv run python scripts/test_config_system.py
        ;;
    *)
        echo "Invalid command: $1"
        echo "Run without arguments to see usage."
        exit 1
        ;;
esac
