@echo off
REM AutoTrader Pro - UV Execution Script for Windows
REM This script provides easy commands to run various components using uv

if "%1"=="" goto :usage

if "%1"=="api" (
    echo Starting AutoTrader Pro API with uv...
    uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --reload
    goto :end
)

if "%1"=="dashboard" (
    echo Starting AutoTrader Pro Dashboard with uv...
    uv run streamlit run src/dashboard/main.py --server.port 8501 --server.address 0.0.0.0
    goto :end
)

if "%1"=="complete" (
    echo Starting AutoTrader Pro Complete System with uv...
    uv run python run_complete.py
    goto :end
)

if "%1"=="main" (
    echo Starting AutoTrader Pro Main System with uv...
    uv run python src/main_automated.py
    goto :end
)

if "%1"=="test" (
    echo Running AutoTrader Pro Tests with uv...
    uv run python -m pytest tests/ -v
    goto :end
)

if "%1"=="config" (
    echo Testing Configuration System with uv...
    uv run python scripts/test_config_system.py
    goto :end
)

:usage
echo.
echo ╔═════════════════════════════════════════════════╗
echo ║              AutoTrader Pro - UV Runner        ║
echo ╚═════════════════════════════════════════════════╝
echo.
echo Usage: run_with_uv.bat [command]
echo.
echo Available commands:
echo   api        - Start FastAPI server only
echo   dashboard  - Start Streamlit dashboard only  
echo   complete   - Start complete system (API + Dashboard)
echo   main       - Start main trading system
echo   test       - Run test suite
echo   config     - Test configuration system
echo.

:end
