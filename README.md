# Trading Arena - Autonomous Options Trader

A comprehensive suite of Alpaca trading tools designed for autonomous options trading with Ollama models.

**Powered by UV - The extremely fast Python package manager**

## Features

### Portfolio Analysis
- Account information and buying power
- Position tracking and P&L analysis
- Portfolio concentration metrics
- Risk assessment

### Options Screening
- Options chain fetching
- Volume and open interest filtering
- DTE (Days to Expiration) filtering
- Strike price range screening

### Options Trading
- Buy/sell options contracts
- Market and limit orders
- Position closing

### Multi-Leg Strategies
- Vertical spreads (credit/debit)
- Iron condors
- Straddles
- Strangles

### Risk Management
- Position sizing validation
- Portfolio concentration limits
- Buying power checks
- Pre-trade risk validation

## Installation

### Prerequisites
Install UV (the fast Python package manager):
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Quick Start
1. Set up the project:
```bash
python uv_run.py setup
# or manually:
uv venv && uv sync --group dev --group test
```

2. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your Alpaca API keys
```

3. Test the installation:
```bash
python uv_run.py test
# or run the import test directly:
uv run python test_imports.py
```

## Configuration

Get your API keys from [Alpaca](https://alpaca.markets/):
- Paper Trading: Free for testing
- Live Trading: Requires funded account

## Usage Example

```python
from src.tools import (
    get_account_info,
    analyze_portfolio,
    screen_options,
    buy_option,
    validate_trade_risk
)

# Check account status
account = get_account_info()
print(f"Portfolio Value: ${account['portfolio_value']:.2f}")

# Analyze current portfolio
portfolio = analyze_portfolio()

# Screen SPY options
contracts = screen_options("SPY", min_dte=7, max_dte=30)

# Validate trade risk
risk_check = validate_trade_risk("SPY241220C00450000", 1)
if risk_check["approved"]:
    result = buy_option("SPY241220C00450000", 1)
```

## Development

### Running Tests
```bash
# Run all tests
python uv_run.py test

# Run unit tests only
python uv_run.py test --unit-only

# Run integration tests only
python uv_run.py test --integration-only

# Run with coverage
python uv_run.py test --coverage

# Run specific test file
python uv_run.py test --file tests/test_portfolio_analysis.py

# Or use UV directly
uv run pytest tests/ -v
uv run pytest tests/ --cov=src --cov-report=html
```

### Code Quality
```bash
# Format code
python uv_run.py format

# Run linting checks
python uv_run.py lint

# Or use individual tools
uv run black src/ tests/
uv run isort src/ tests/
uv run ruff check src/ tests/
uv run mypy src/
```

### Adding Dependencies
```bash
# Add main dependency
python uv_run.py add requests

# Add dev dependency
python uv_run.py add pytest --dev

# Add test dependency
python uv_run.py add pytest-cov --test

# Or use UV directly
uv add requests
uv add --dev pytest
uv add --group test pytest-cov
```

### Running the Application
```bash
python uv_run.py run
# or
uv run python -m src.main
```

## Project Structure

```
trading-agent/
├── src/
│   ├── __init__.py
│   ├── tools.py              # Main trading tools library
│   └── main.py               # Application entry point
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Test fixtures
│   ├── test_*.py             # Test files
│   └── README.md             # Test documentation
├── .python-version           # Python version for UV
├── .env.example              # Environment variables template
├── pyproject.toml            # UV project configuration
├── uv_run.py                 # UV development script
├── run_tests.py              # Test runner (UV edition)
├── test_imports.py           # Installation verification
└── README.md                 # This file
```

## Risk Management

The tools include built-in risk management:
- Maximum position concentration (default: 10%)
- Maximum portfolio exposure (default: 25%)
- Buying power validation
- Position sizing controls

## Paper Trading

By default, the tools use Alpaca's paper trading environment for safe testing.

## UV Benefits

Using UV provides several advantages:
- **Lightning Fast** - 10-100x faster than pip
- **Reliable** - Deterministic dependency resolution
- **Modern** - Supports pyproject.toml and dependency groups
- **Cross-platform** - Works on macOS, Linux, and Windows
- **Zero-config** - No virtualenv management needed

## Note

This is designed for use with autonomous agents and LLMs. All functions return structured data that's easy for AI models to process and act upon.

**Always test thoroughly with paper trading before using real funds.**