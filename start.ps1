#!/usr/bin/env pwsh
# AutoTrader Pro - Windows PowerShell Runner
# Runs the system using uv for optimal performance

Write-Host ""
Write-Host "🚀 AutoTrader Pro v2.0 - Windows Runner" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check if uv is installed
try {
    $uvVersion = uv --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ uv found: $uvVersion" -ForegroundColor Green
    } else {
        throw "uv not found"
    }
} catch {
    Write-Host "❌ uv is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "📥 Install uv first:" -ForegroundColor Yellow
    Write-Host "powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  No .env file found" -ForegroundColor Yellow
    Write-Host "🎮 Running quick setup for demo mode..." -ForegroundColor Blue
    try {
        uv run python quick_setup.py
        if ($LASTEXITCODE -ne 0) {
            throw "Setup failed"
        }
    } catch {
        Write-Host "❌ Setup failed!" -ForegroundColor Red
        exit 1
    }
}

# Start the system
Write-Host "🚀 Starting AutoTrader Pro..." -ForegroundColor Green
Write-Host "🌐 Dashboard will be available at: http://localhost:8501" -ForegroundColor Blue
Write-Host "📚 API Documentation at: http://localhost:8080/docs" -ForegroundColor Blue
Write-Host ""
Write-Host "Press Ctrl+C to stop the system" -ForegroundColor Yellow
Write-Host ""

try {
    uv run python run.py
} catch {
    Write-Host ""
    Write-Host "❌ Failed to start AutoTrader Pro" -ForegroundColor Red
    Write-Host "Check the logs above for details" -ForegroundColor Yellow
    exit 1
}
