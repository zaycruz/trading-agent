"""
Pure Tool Functions for Autonomous Crypto Trading Agent
All functions are designed to be called by LLM via Ollama tool calling.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce, AssetClass
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, CryptoLatestQuoteRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
import pandas as pd

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Initialize clients globally for tool functions
_trading_client = None
_crypto_data_client = None

def _get_trading_client():
    """Lazy initialization of trading client"""
    global _trading_client
    if _trading_client is None:
        api_key = os.getenv("ALPACA_API_KEY", "")
        secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        paper = os.getenv("ALPACA_LIVE_TRADING", "false").lower() != "true"
        _trading_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=paper)
    return _trading_client

def _get_crypto_data_client():
    """Lazy initialization of crypto data client"""
    global _crypto_data_client
    if _crypto_data_client is None:
        api_key = os.getenv("ALPACA_API_KEY", "")
        secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        _crypto_data_client = CryptoHistoricalDataClient(api_key=api_key, secret_key=secret_key)
    return _crypto_data_client

# ============================================================================
# TOOL FUNCTIONS - Called by LLM via Ollama
# ============================================================================

def get_account_info() -> Dict:
    """
    Get comprehensive account information including balance and buying power.
    Returns account status, cash, portfolio value, and trading permissions.
    """
    try:
        client = _get_trading_client()
        account = client.get_account()
        return {
            "account_id": str(account.id),
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "equity": float(account.equity),
            "long_market_value": float(account.long_market_value),
            "status": str(account.status),
            "trading_blocked": bool(account.trading_blocked),
            "crypto_status": account.crypto_status if hasattr(account, 'crypto_status') else "unknown"
        }
    except Exception as e:
        return {"error": f"Failed to get account info: {str(e)}"}

def get_positions() -> List[Dict]:
    """
    Get all current positions (stocks and crypto).
    Returns list of positions with symbol, quantity, market value, and P&L.
    """
    try:
        client = _get_trading_client()
        positions = client.get_all_positions()
        position_list = []
        for pos in positions:
            position_list.append({
                "symbol": str(pos.symbol),
                "quantity": float(pos.qty),
                "side": str(pos.side),
                "market_value": float(pos.market_value),
                "cost_basis": float(pos.cost_basis),
                "unrealized_pl": float(pos.unrealized_pl),
                "unrealized_pl_percent": float(pos.unrealized_plpc) * 100,
                "current_price": float(pos.current_price),
                "asset_class": str(pos.asset_class) if hasattr(pos, 'asset_class') else "unknown"
            })
        return position_list
    except Exception as e:
        return [{"error": f"Failed to get positions: {str(e)}"}]

def get_crypto_price(symbol: str) -> Dict:
    """
    Get current price for a crypto symbol (e.g., BTC/USD, ETH/USD).
    Returns bid, ask, mid price, and timestamp.
    """
    try:
        client = _get_crypto_data_client()
        request_params = CryptoLatestQuoteRequest(symbol_or_symbols=symbol)
        quotes = client.get_crypto_latest_quote(request_params)
        quote = quotes[symbol]
        
        return {
            "symbol": symbol,
            "bid_price": float(quote.bid_price),
            "ask_price": float(quote.ask_price),
            "mid_price": float((quote.bid_price + quote.ask_price) / 2),
            "timestamp": str(quote.timestamp)
        }
    except Exception as e:
        return {"error": f"Failed to get crypto price for {symbol}: {str(e)}"}

def place_crypto_order(symbol: str, side: str, quantity: float, order_type: str = "market") -> Dict:
    """
    Place a crypto order (buy or sell).
    
    Args:
        symbol: Crypto symbol (e.g., "BTC/USD", "ETH/USD")
        side: "buy" or "sell"
        quantity: Amount to trade (e.g., 0.1 for 0.1 BTC)
        order_type: "market" or "limit" (default: "market")
    
    Returns order confirmation with order_id, status, and fill price.
    """
    try:
        client = _get_trading_client()
        
        # Convert side to OrderSide enum
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        
        # Create market order request
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=order_side,
            time_in_force=TimeInForce.GTC
        )
        
        order = client.submit_order(order_data)
        
        return {
            "order_id": str(order.id),
            "symbol": str(order.symbol),
            "side": str(order.side),
            "quantity": float(order.qty),
            "order_type": str(order.type),
            "status": str(order.status),
            "submitted_at": str(order.submitted_at),
            "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None
        }
    except Exception as e:
        return {"error": f"Failed to place order: {str(e)}"}

def get_order_history(limit: int = 10) -> List[Dict]:
    """
    Get recent order history.
    Returns list of recent orders with status and fill information.
    """
    try:
        client = _get_trading_client()
        orders = client.get_orders(limit=limit, status='all')
        
        order_list = []
        for order in orders:
            order_list.append({
                "order_id": str(order.id),
                "symbol": str(order.symbol),
                "side": str(order.side),
                "quantity": float(order.qty),
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "status": str(order.status),
                "order_type": str(order.type),
                "submitted_at": str(order.submitted_at),
                "filled_at": str(order.filled_at) if order.filled_at else None,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None
            })
        
        return order_list
    except Exception as e:
        return [{"error": f"Failed to get order history: {str(e)}"}]

def cancel_order(order_id: str) -> Dict:
    """
    Cancel a pending order by order_id.
    Returns cancellation confirmation.
    """
    try:
        client = _get_trading_client()
        client.cancel_order_by_id(order_id)
        return {
            "success": True,
            "order_id": order_id,
            "message": "Order cancelled successfully"
        }
    except Exception as e:
        return {"error": f"Failed to cancel order: {str(e)}"}

def get_crypto_bars(symbol: str, timeframe: str = "1Hour", limit: int = 100) -> Dict:
    """
    Get historical price bars for crypto (OHLCV data).
    
    Args:
        symbol: Crypto symbol (e.g., "BTC/USD")
        timeframe: "1Min", "5Min", "15Min", "1Hour", "1Day" (default: "1Hour")
        limit: Number of bars to return (default: 100)
    
    Returns OHLCV data as lists for easy analysis.
    """
    try:
        client = _get_crypto_data_client()
        
        # Map timeframe string to TimeFrame enum
        timeframe_map = {
            "1Min": TimeFrame.Minute,
            "5Min": TimeFrame(5, "Min"),
            "15Min": TimeFrame(15, "Min"),
            "1Hour": TimeFrame.Hour,
            "1Day": TimeFrame.Day
        }
        
        tf = timeframe_map.get(timeframe, TimeFrame.Hour)
        
        request_params = CryptoBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            limit=limit
        )
        
        bars = client.get_crypto_bars(request_params)
        df = bars.df
        
        if df.empty:
            return {"error": "No data returned"}
        
        # Convert to simple dict format
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "data": {
                "timestamps": [str(ts) for ts in df.index.get_level_values('timestamp')],
                "open": df['open'].tolist(),
                "high": df['high'].tolist(),
                "low": df['low'].tolist(),
                "close": df['close'].tolist(),
                "volume": df['volume'].tolist()
            }
        }
    except Exception as e:
        return {"error": f"Failed to get crypto bars: {str(e)}"}

def get_current_datetime() -> Dict:
    """
    Get current date and time for temporal awareness.
    Returns current timestamp, date, time, and day of week.
    """
    now = datetime.now()
    return {
        "timestamp": str(now),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "unix_timestamp": int(now.timestamp())
    }