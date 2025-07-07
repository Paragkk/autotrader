# AutoTrader Pro - Professional Automated Trading System

<p align="center">
    <em>Production-ready automated trading system with advanced risk management and ML-driven strategies</em>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python Version">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
    <img src="https://img.shields.io/badge/Version-1.0.0-orange.svg" alt="Version">
    <img src="https://img.shields.io/badge/Docker-Ready-brightgreen.svg" alt="Docker">
</p>

## 🚀 Overview

AutoTrader Pro is a comprehensive, production-ready automated trading system designed for professional deployment. It features a complete 10-step automated trading workflow with advanced risk management, multi-strategy execution, and real-time monitoring capabilities.

**Key Highlights:**
- **Fully Automated**: End-to-end trading automation from screening to execution
- **Risk Management**: Advanced position sizing, stop-loss, and portfolio risk controls
- **Multi-Strategy**: Pluggable strategy architecture supporting multiple trading approaches
- **Production Ready**: Docker containerized with comprehensive logging and monitoring
- **ML-Driven**: Machine learning for stock scoring and signal generation

---

## 🎯 Features

### Automated Trading Workflow
- **Scheduled Stock Screening**: Hourly screening with configurable criteria
- **Multi-Factor Scoring**: Advanced scoring system using momentum, volume, volatility, and technical indicators
- **Strategy Engine**: Multiple parallel trading strategies with weighted signal aggregation
- **Risk Management**: Portfolio limits, position sizing, and stop-loss controls
- **Order Execution**: Reliable order execution with retry logic and timeout handling
- **Position Monitoring**: Real-time monitoring with automated exit conditions
- **Audit Trail**: Complete logging and persistence of all trading activities

### Technical Features
- **Docker Containerized**: Production-ready deployment with Docker Compose
- **Database Persistence**: SQLite with comprehensive audit logging
- **Web Dashboard**: Real-time monitoring and control interface
- **RESTful API**: Complete API for external integrations
- **Configuration Management**: YAML-based configuration with environment variables
- **Structured Logging**: Comprehensive logging with rotation and filtering
- **Health Monitoring**: System health checks and performance metrics

### Risk Management
- **Position Limits**: Maximum number of concurrent positions
- **Daily Loss Limits**: Automatic trading suspension on loss thresholds
- **Portfolio Diversification**: Automatic position sizing based on portfolio percentage
- **Stop-Loss Protection**: Configurable stop-loss percentages
- **Take-Profit Targets**: Automated profit-taking at target levels

---

## 🏗️ Architecture

AutoTrader Pro follows a modular, production-ready architecture:

```
src/
├── main_automated.py          # Main trading orchestrator
├── core/                      # Core trading components
│   ├── stock_screener.py      # Automated stock screening
│   ├── stock_scorer.py        # Multi-factor scoring system
│   ├── strategy_engine.py     # Trading strategy engine
│   ├── signal_aggregator.py   # Signal aggregation logic
│   ├── risk_manager.py        # Risk management system
│   ├── order_executor.py      # Order execution engine
│   └── position_monitor.py    # Position monitoring
├── brokers/                   # Broker integrations
│   └── alpaca/               # Alpaca broker adapter
├── db/                       # Database layer
│   ├── models.py             # Data models
│   └── repository.py         # Data access layer
├── api/                      # REST API
│   └── main.py              # FastAPI application
└── infra/                    # Infrastructure
    ├── config.py             # Configuration management
    ├── logging_config.py     # Logging setup
    └── path_utils.py         # Path utilities
```

### Key Components

- **Trading Orchestrator**: Coordinates the entire trading workflow
- **Strategy Engine**: Pluggable architecture for multiple trading strategies
- **Risk Manager**: Advanced risk controls and position sizing
- **Signal Aggregator**: Combines signals from multiple strategies with confidence weighting
- **Order Executor**: Handles order placement with retry logic and error handling
- **Position Monitor**: Tracks open positions and manages exit conditions

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (recommended)
- **Alpaca trading account** (paper or live)

### 1. Environment Setup

Create a `.env` file in the project root:

```bash
# Required: Alpaca API Credentials
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here

# Optional: Override default settings
DATABASE_URL=sqlite:///data/trading.db
LOG_LEVEL=INFO
```

### 2. Docker Deployment (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd autotrader

# Build and start all services
docker-compose up -d

# View real-time logs
docker-compose logs -f autotrader

# Stop services
docker-compose down
```

This starts:
- **AutoTrader Pro** (main trading system)
- **Dashboard** (automatically started at http://localhost:8501)
- **Redis** (for caching)

### 3. Local Development

```bash
# Install dependencies with uv
uv pip install -e .

# For dashboard (optional - installs Streamlit)
uv pip install -e .[dashboard]

# For full development setup
uv pip install -e .[dev]

# Run the system (dashboard starts automatically)
python run.py
```

### 4. Configuration

Edit `config.yaml` to customize trading parameters:

```yaml
trading:
  max_positions: 15              # Maximum concurrent positions
  max_daily_loss: 2000.0        # Daily loss limit ($)
  position_size_percent: 0.03   # Position size (3% of portfolio)
  stop_loss_percent: 0.03       # Stop loss (3%)
  take_profit_percent: 0.08     # Take profit (8%)

screening:
  enabled: true
  schedule: "0 */1 * * *"        # Every hour
  max_symbols: 50
  criteria:
    min_price: 5.0
    max_price: 500.0
    min_volume: 250000
```

### 5. Broker Configuration

AutoTrader Pro supports modular broker configuration. The system uses a layered configuration approach:

1. **Base Configuration**: Common settings in `src/brokers/base/config/base_config.yaml`
2. **Broker-Specific Configuration**: Alpaca settings in `src/brokers/alpaca/config/alpaca_config.yaml`
3. **Main Configuration**: Override settings in `config.yaml`

To add a new broker, create the directory structure:
```
src/brokers/new_broker/
├── config/new_broker_config.yaml
├── __init__.py
└── adapter.py
```

---

## 📊 Monitoring & Control

### Real-time Dashboard

AutoTrader Pro includes a comprehensive **Streamlit dashboard** that automatically launches with the system:

**Access:** http://localhost:8501

**Features:**
- **🏠 Overview**: System status, tracked symbols, portfolio metrics
- **📊 Strategies**: Strategy performance, win rates, signal distribution
- **🎯 Signals**: Live trading signals with confidence scores
- **💼 Positions**: Active positions with real-time P&L
- **📈 Performance**: Portfolio charts and risk analytics

**Emergency Controls:**
- **🛑 Emergency Stop**: Immediately halt all trading
- **🔄 Close Positions**: Close individual or all positions
- **⚡ Strategy Toggle**: Enable/disable specific strategies
- **📊 Real-time Monitoring**: Live updates every 10 seconds
- Configuration management interface

### API Endpoints

The system provides a comprehensive REST API:

- `GET /health` - System health check
- `GET /portfolio` - Portfolio overview
- `GET /positions` - Current positions
- `GET /signals` - Recent trading signals
- `POST /orders` - Manual order placement
- `POST /controls/stop` - Emergency stop

### Logging

Comprehensive logging with multiple levels:
- **INFO**: General system operation
- **WARNING**: Non-critical issues
- **ERROR**: Critical errors requiring attention
- **DEBUG**: Detailed debugging information

Logs are automatically rotated and stored in `logs/` directory.

---

## 🔧 Technical Details

### Database Schema

AutoTrader Pro uses SQLite with the following main tables:

- **trades**: Complete trading history
- **positions**: Current and historical positions
- **signals**: Generated trading signals
- **portfolio_snapshots**: Portfolio state over time
- **system_logs**: System events and errors

### Strategy Framework

The system supports multiple trading strategies:

1. **Mean Reversion Strategy**: Identifies oversold/overbought conditions
2. **Momentum Strategy**: Follows price trends and breakouts
3. **Volatility Strategy**: Trades based on volatility patterns
4. **Multi-Factor Strategy**: Combines multiple indicators

### Risk Management

**Portfolio Level:**
- Maximum number of positions
- Daily loss limits
- Sector concentration limits
- Correlation limits

**Position Level:**
- Position sizing based on volatility
- Stop-loss orders
- Take-profit targets
- Maximum holding periods

### Security Features

- Environment variable configuration
- API key encryption
- Request rate limiting
- Input validation and sanitization
- Secure logging (no sensitive data)

---

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/test_trading/
python -m pytest tests/test_models/
python -m pytest tests/test_integration/

# Run with coverage
python -m pytest --cov=src/
```

**Test Coverage:**
- Unit tests for all core components
- Integration tests for broker interactions
- End-to-end workflow testing
- Performance and stress testing

---

## 🛡️ Production Considerations

### Deployment Checklist

- [ ] Environment variables configured
- [ ] Database backup strategy in place
- [ ] Monitoring and alerting configured
- [ ] Log rotation and retention policy
- [ ] Security review completed
- [ ] Disaster recovery plan documented

### Performance Optimization

- Enable Redis caching for market data
- Configure appropriate database connection pooling
- Implement request rate limiting
- Monitor memory usage and optimize accordingly

### Security Best Practices

- Use environment variables for sensitive configuration
- Implement IP whitelisting for API access
- Regular security audits and updates
- Secure backup and disaster recovery procedures

---

## 📈 Performance Metrics

AutoTrader Pro tracks comprehensive performance metrics:

- **Trading Performance**: Win rate, profit/loss, Sharpe ratio
- **System Performance**: Execution latency, uptime, error rates
- **Risk Metrics**: Maximum drawdown, portfolio volatility
- **Operational Metrics**: Order fill rates, signal accuracy

All metrics are available through the dashboard and API endpoints.

---

## 🤝 Contributing

We welcome contributions to improve AutoTrader Pro! Here's how you can help:

### Ways to Contribute

- **Bug Reports**: Submit detailed bug reports with reproduction steps
- **Feature Requests**: Suggest new features or improvements
- **Code Contributions**: Submit pull requests with bug fixes or new features
- **Documentation**: Help improve documentation and examples
- **Testing**: Add test coverage or report testing results

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes and add tests
4. Ensure all tests pass: `python -m pytest`
5. Submit a pull request with a detailed description

### Code Standards

- Follow PEP 8 style guidelines
- Add comprehensive docstrings
- Include unit tests for new functionality
- Update documentation as needed

---

## 🛡️ Security

### Security Best Practices

- **API Keys**: Never commit API keys to version control
- **Environment Variables**: Use `.env` files for sensitive configuration
- **Network Security**: Implement proper firewall rules in production
- **Data Encryption**: Ensure data at rest and in transit is encrypted

### Reporting Security Issues

If you discover a security vulnerability, please email the maintainers directly rather than opening a public issue.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Alpaca Markets**: For providing the excellent trading API
- **Open Source Community**: For the amazing libraries and tools
- **Contributors**: Thanks to all who have contributed to this project

---

## 📞 Support

- **Documentation**: Complete documentation is available in this README
- **Issues**: Report bugs and feature requests on GitHub
- **Community**: Join discussions and share experiences

---

<p align="center">
    <strong>AutoTrader Pro v1.0.0</strong><br>
    <em>Professional Automated Trading System</em>
</p>
