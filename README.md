# Trading Arena - Autonomous Options Trader

A comprehensive suite of Alpaca trading tools designed for autonomous options trading with Ollama models.

## Features

### 📊 Portfolio Analysis
- Account information and buying power
- Position tracking and P&L analysis
- Portfolio concentration metrics
- Risk assessment

### 🔍 Options Screening
- Options chain fetching
- Volume and open interest filtering
- DTE (Days to Expiration) filtering
- Strike price range screening

### 💰 Options Trading
- Buy/sell options contracts
- Market and limit orders
- Position closing

### 🎯 Multi-Leg Strategies
- Vertical spreads (credit/debit)
- Iron condors
- Straddles
- Strangles

### ⚠️ Risk Management
- Position sizing validation
- Portfolio concentration limits
- Buying power checks
- Pre-trade risk validation

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your Alpaca API keys
```

3. Test the installation:
```bash
python test_imports.py
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

## Structure

- `src/tools.py` - Main trading tools library
- `test_imports.py` - Installation verification
- `.env.example` - Environment variables template
- `requirements.txt` - Python dependencies

## Risk Management

The tools include built-in risk management:
- Maximum position concentration (default: 10%)
- Maximum portfolio exposure (default: 25%)
- Buying power validation
- Position sizing controls

## Paper Trading

By default, the tools use Alpaca's paper trading environment for safe testing.

## Note

This is designed for use with autonomous agents and LLMs. All functions return structured data that's easy for AI models to process and act upon.

⚠️ **Always test thoroughly with paper trading before using real funds.**