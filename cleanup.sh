#!/bin/bash
# AutoTrader Pro - Project Cleanup and Setup Script

echo "🧹 Cleaning up AutoTrader Pro project..."

# Remove unnecessary files
echo "📁 Removing unnecessary files..."

# Remove old demo files
rm -f demo_enhanced_screening.py
rm -f start_enhanced_trading.py

# Remove duplicate config files
rm -f main_config.yaml
rm -f enhanced_config.yaml
rm -f src/brokers/alpaca/config.yaml
rm -f src/brokers/base/config/base_config.yaml

# Remove cache files
rm -rf yfinance.cache
rm -rf src/__pycache__
rm -rf src/*/__pycache__
rm -rf tests/__pycache__

# Remove old docs
rm -rf docs/

# Remove test files that are stubs
rm -f tests/test_unit_stub.py
rm -f tests/test_integration_stub.py

# Remove old requirements
rm -f docs/rtd_requirements.txt

echo "✅ Cleanup completed!"

echo "🔧 Setting up project structure..."

# Create necessary directories
mkdir -p data
mkdir -p logs
mkdir -p scripts

# Make run script executable
chmod +x run.py

echo "📋 Project structure overview:"
echo "
AutoTrader Pro/
├── src/
│   ├── main_automated.py      # ✅ Main trading system
│   ├── db/models.py           # ✅ Database models
│   ├── core/                  # ✅ Core trading components
│   ├── brokers/               # ✅ Broker integrations
│   ├── api/main.py            # ✅ Monitoring dashboard
│   └── infra/                 # ✅ Infrastructure
├── config.yaml                # ✅ Single configuration file
├── docker-compose.yml         # ✅ Docker deployment
├── Dockerfile                 # ✅ Container definition
├── requirements.txt           # ✅ Dependencies
├── run.py                     # ✅ Main entry point
└── data/                      # ✅ Database storage
"

echo "✅ Project cleanup and setup completed!"
echo ""
echo "🚀 Next steps:"
echo "1. Set your environment variables:"
echo "   export ALPACA_API_KEY='your_key'"
echo "   export ALPACA_SECRET_KEY='your_secret'"
echo ""
echo "2. Run the system:"
echo "   python run.py"
echo ""
echo "3. Or use Docker:"
echo "   docker-compose up -d"
echo ""
echo "4. Access dashboard:"
echo "   http://localhost:8080"
