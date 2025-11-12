# Autonomous Options Trading Agent - Usage Guide

## Overview

This is a **pure tool-based autonomous options trading agent** powered by Qwen 3 (or any Ollama model) that makes ALL trading decisions via tool calling. The agent has:

- **No hardcoded trading logic** - All decisions come from the LLM
- **Full context awareness** - Remembers past decisions and learns from them
- **Temporal awareness** - Knows the current time/date for market timing
- **Self-reflective** - Reviews its own performance and improves
- **Tool-driven** - Trading, analysis, and research via tool calls

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RECURSIVE AGENT LOOP                     │
│                                                             │
│  1. Check time & review decision history                   │
│  2. Check portfolio & account status                       │
│  3. Research market (Tavily web search)                    │
│  4. Perform technical analysis (RSI, MACD, etc.)           │
│  5. Make trading decision                                   │
│  6. Execute via tools                                       │
│  7. Record decision with timestamp                         │
│  8. Sleep → Repeat                                          │
└─────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Prerequisites

- **Python 3.9+**
- **UV package manager** (https://docs.astral.sh/uv/)
- **Ollama** with Qwen 3 model installed (https://ollama.com/)
- **Alpaca account** (paper or live trading)
- **Tavily API key** (for web search)

### 2. Install Ollama & Qwen 3

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Qwen 3 model (or qwen2.5)
ollama pull qwen2.5:latest

# Verify it's working
ollama run qwen2.5:latest "Hello"
```

### 3. Install Dependencies

```bash
# Install UV if you haven't
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync
```

### 4. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required variables:
```env
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
TAVILY_API_KEY=your_tavily_api_key

# Optional - defaults to paper trading
# ALPACA_LIVE_TRADING=false  

# Optional - defaults to localhost
# OLLAMA_HOST=http://localhost:11434
```

## Running the Agent

### Basic Usage

```bash
# Run with defaults (5-minute cycles, infinite loop)
uv run python main.py

# Or shorter version
python3 main.py
```

### Advanced Options

```bash
# Custom model
uv run python main.py --model qwen3:latest

# Faster cycles (1 minute)
uv run python main.py --interval 60

# Test mode (run 3 cycles only)
uv run python main.py --max-iterations 3

# Quiet mode (less logging)
uv run python main.py --quiet

# Combine options
uv run python main.py --model qwen2.5:latest --interval 180 --max-iterations 10
```

### Stop the Agent

Press `Ctrl+C` to gracefully stop the agent at any time.

## Available Tools (20 total)

The agent can call these tools autonomously:

### Trading Tools
- `get_account_info()` - Check balance, buying power
- `get_positions()` - View current holdings
- `get_option_positions()` - View existing option exposures
- `get_option_contracts(underlying)` - Discover contracts
- `get_options_chain(underlying)` - Inspect chain snapshot
- `get_option_quote(symbol)` - Fetch bid/ask for a contract
- `place_option_order(symbol, side, quantity, order_type)` - Execute single-leg trades
- `place_multi_leg_option_order(legs, quantity, order_type)` - Execute spreads/condors
- `close_option_position(symbol, quantity)` - Flatten open option position
- `get_order_history(limit)` - Review past orders
- `cancel_order(order_id)` - Cancel pending orders
- `get_price_bars(symbol, timeframe)` - Underlying OHLCV data

### Technical Analysis Tools
- `calculate_rsi(symbol, period)` - RSI indicator
- `calculate_macd(symbol)` - MACD crossover signals
- `calculate_moving_averages(symbol, periods)` - SMA analysis
- `calculate_bollinger_bands(symbol)` - Volatility bands
- `get_price_momentum(symbol, periods)` - Price momentum
- `get_support_resistance(symbol)` - Key price levels

### Market Research Tools (Tavily)
- `get_market_sentiment(symbol)` - Sentiment analysis
- `search_technical_analysis(symbol)` - TA discussions
- `search_general_web(query)` - General web search

### Context Tools
- `get_current_datetime()` - Time/date awareness
- `get_decision_history(limit)` - Review past decisions
- `get_performance_summary()` - Performance metrics

## Example Agent Behavior

**Cycle 1:**
```
Tool Call: get_current_datetime()
Tool Call: get_decision_history(limit=10)
Tool Call: get_account_info()
Tool Call: get_positions()
Tool Call: get_price_bars(symbol="SPY", timeframe="1Hour")
Tool Call: calculate_rsi(symbol="SPY", period=14)
Tool Call: calculate_macd(symbol="SPY")
Tool Call: get_option_quote(symbol="SPY241220C00450000")

Agent: Based on my analysis:
- RSI is at 32 (oversold) on SPY
- MACD shows bullish crossover on the 1h chart
- Liquidity is strong with tight 2.44 x 2.46 markets
- My portfolio has capacity for a new position

I will buy 2x SPY Dec 20 450 calls at market.

Tool Call: place_option_order(symbol="SPY241220C00450000", side="buy", quantity=2, order_type="market")
TRADE EXECUTED: {"order_id": "...", "status": "filled"}
```

## Decision History

All decisions are saved to `data/decision_history.json` with:
- Timestamp
- Reasoning
- Action taken
- Parameters used
- Results
- Portfolio value

The agent reviews this history each cycle to learn from past trades.

## Safety Features

1. **Paper Trading by Default** - No risk until you enable live trading
2. **Risk Management in Prompt** - Agent instructed to use 10% max per trade
3. **Graceful Shutdown** - Ctrl+C stops agent safely
4. **Error Recovery** - Agent continues after errors
5. **Tool Validation** - All tool calls logged and validated

## Customization

### Change Agent Personality

Edit `SYSTEM_PROMPT` in `src/agent.py` to modify:
- Risk tolerance
- Trading strategy
- Decision-making style
- Personality traits

### Add New Tools

1. Create tool function in appropriate file
2. Add to `TOOLS` list in `src/agent.py`
3. Agent will automatically have access

### Adjust Cycle Timing

Different intervals for different strategies:
- **Scalping:** `--interval 60` (1 minute)
- **Intraday:** `--interval 300` (5 minutes)
- **Swing:** `--interval 3600` (1 hour)
- **Position:** `--interval 86400` (1 day)

## Monitoring

### View Real-Time Logs

The agent logs all actions:
```
2025-11-10 14:30:00 - INFO - TRADING CYCLE #5
2025-11-10 14:30:01 - INFO - Tool Call: get_current_datetime({})
2025-11-10 14:30:02 - INFO - Tool Call: calculate_rsi({"symbol": "BTC/USD"})
2025-11-10 14:30:03 - INFO - Agent: RSI indicates oversold conditions...
```

### Check Performance

Use the performance tool:
```python
from src.decision_history import get_performance_summary

summary = get_performance_summary()
print(summary)
```

## Troubleshooting

### "Ollama connection refused"
```bash
# Start Ollama
ollama serve
```

### "Tavily API error"
- Check your `TAVILY_API_KEY` in `.env`
- Verify at https://tavily.com/

### "Alpaca authentication failed"
- Verify `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- Check if using paper vs live endpoints

### Agent not making trades
- Check account balance
- Review decision history for reasoning
- Increase verbosity (remove `--quiet`)

## Advanced: Test Mode

Run a single cycle for testing:
```bash
uv run python main.py --max-iterations 1 --interval 0
```

## Architecture Details

### Pure Tool-Based Design

Unlike traditional trading bots with hardcoded if/else logic:
```python
# Traditional Bot (hardcoded)
if rsi < 30:
    buy()

# This Agent (LLM decides)
# Agent calls calculate_rsi(), analyzes result, decides to buy or not
```

### Context Awareness

The agent maintains conversation history:
- Last 50 messages kept in memory
- Past decisions loaded from JSON file
- Learns from mistakes and successes

### Temporal Awareness

Agent knows:
- Current date/time
- Day of week (for market patterns)
- Time since last trade
- Historical performance over time

## Safety Warning

**IMPORTANT:**
- Start with paper trading
- Test thoroughly before live trading
- Monitor the agent actively
- Set Alpaca account limits
- Never risk more than you can afford to lose

This agent makes autonomous decisions. While it has risk management guidelines in its prompt, it's still an AI system that can make mistakes.

## Support

- Check logs for detailed error messages
- Review `data/decision_history.json` for agent reasoning
- Adjust `SYSTEM_PROMPT` for different behavior
- Use `--max-iterations` for controlled testing

## Next Steps

1. Run in test mode: `uv run python main.py --max-iterations 3`
2. Review decision history: `cat data/decision_history.json`
3. Adjust system prompt for your strategy
4. Monitor paper trading performance
5. Only enable live trading after thorough testing
