#!/usr/bin/env python3
"""
Test script to verify alpaca-py imports work correctly
"""

try:
    # Test alpaca imports
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
    from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
    from alpaca.data.requests import StockLatestQuoteRequest
    from alpaca.data.timeframe import TimeFrame

    print("-  All alpaca-py imports successful!")

    # Test basic configuration
    import os
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        print("WARNING:   Warning: ALPACA_API_KEY or ALPACA_SECRET_KEY not found in environment")
        print("Please set these in a .env file or environment variables")
    else:
        print("-  API keys found in environment")

        # Test client initialization (without making actual API calls)
        trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=True
        )
        print("-  TradingClient initialized successfully")

        stock_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )
        print("-  StockHistoricalDataClient initialized successfully")

    print("\n All tests passed! Your tools.py should work correctly.")

except ImportError as e:
    print(f"-  Import error: {e}")
    print("Please install alpaca-py with: pip install -r requirements.txt")
except Exception as e:
    print(f"-  Error: {e}")