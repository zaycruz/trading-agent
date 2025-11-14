"""
Pure Tool Functions for the Autonomous Options Trading Agent
All functions are designed to be called by LLM via Ollama tool calling.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    ClosePositionRequest,
    GetOptionContractsRequest,
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    OptionLegRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    OrderType,
    TimeInForce,
    AssetClass,
    QueryOrderStatus,
    OrderClass,
    AssetStatus,
    ContractType,
    ExerciseStyle
)
from alpaca.data.historical import (
    StockHistoricalDataClient,
    OptionHistoricalDataClient
)
from alpaca.data.requests import (
    StockLatestQuoteRequest,
    StockBarsRequest,
    OptionLatestQuoteRequest
)
from alpaca.data.timeframe import TimeFrame
import pandas as pd

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Initialize clients globally for tool functions
_trading_client = None
_stock_data_client = None
_option_data_client = None


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _get_trading_client():
    """Lazy initialization of trading client"""
    global _trading_client
    if _trading_client is None:
        api_key = os.getenv("ALPACA_API_KEY", "")
        secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        paper = os.getenv("ALPACA_LIVE_TRADING", "false").lower() != "true"
        _trading_client = TradingClient(api_key=api_key, secret_key=secret_key, paper=paper)
    return _trading_client

def _get_stock_data_client():
    """Lazy initialization of stock data client"""
    global _stock_data_client
    if _stock_data_client is None:
        api_key = os.getenv("ALPACA_API_KEY", "")
        secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        _stock_data_client = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)
    return _stock_data_client

def _get_option_data_client():
    """Lazy initialization of option data client"""
    global _option_data_client
    if _option_data_client is None:
        api_key = os.getenv("ALPACA_API_KEY", "")
        secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        _option_data_client = OptionHistoricalDataClient(api_key=api_key, secret_key=secret_key)
    return _option_data_client

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
            "trading_blocked": bool(account.trading_blocked)
        }
    except Exception as e:
        return {"error": f"Failed to get account info: {str(e)}"}

def get_positions() -> List[Dict]:
    """
    Get all current positions (equities and options).
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


# ============================================================================
# OPTION-SPECIFIC TOOL FUNCTIONS
# ============================================================================

def get_option_positions() -> List[Dict]:
    """
    Get all open option positions only.
    """
    try:
        client = _get_trading_client()
        positions = client.get_all_positions()
        option_positions = []
        for pos in positions:
            asset_class = str(getattr(pos, 'asset_class', '')).lower()
            if 'option' not in asset_class:
                continue
            qty = float(pos.qty) if hasattr(pos, 'qty') else 0.0
            option_positions.append({
                "symbol": str(pos.symbol),
                "quantity": qty,
                "side": str(pos.side),
                "market_value": float(pos.market_value) if hasattr(pos, 'market_value') else 0.0,
                "cost_basis": float(pos.cost_basis) if hasattr(pos, 'cost_basis') else 0.0,
                "current_price": float(pos.current_price) if hasattr(pos, 'current_price') else None,
                "unrealized_pl": float(pos.unrealized_pl) if hasattr(pos, 'unrealized_pl') else None,
                "unrealized_pl_percent": float(pos.unrealized_plpc) * 100 if hasattr(pos, 'unrealized_plpc') else None,
                "expiration_date": str(getattr(pos, 'expiry_date', '')),
                "strike_price": float(getattr(pos, 'strike_price', 0.0)) if hasattr(pos, 'strike_price') else None
            })
        return option_positions
    except Exception as e:
        return [{"error": f"Failed to get option positions: {str(e)}"}]


def _map_contract_type(contract_type: Optional[str]) -> ContractType:
    if contract_type and contract_type.lower() == "put":
        return ContractType.PUT
    return ContractType.CALL


def get_option_contracts(
    underlying_symbol: str,
    contract_type: str = "call",
    expiration_date_gte: Optional[str] = None,
    expiration_date_lte: Optional[str] = None,
    strike_price_gte: Optional[float] = None,
    strike_price_lte: Optional[float] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Fetch listed option contracts for an underlying symbol with optional filters.
    """
    try:
        client = _get_trading_client()
        request_params = GetOptionContractsRequest(
            underlying_symbols=[underlying_symbol],
            status=AssetStatus.ACTIVE,
            type=_map_contract_type(contract_type),
            style=ExerciseStyle.AMERICAN,
            expiration_date_gte=expiration_date_gte,
            expiration_date_lte=expiration_date_lte,
            strike_price_gte=str(strike_price_gte) if strike_price_gte is not None else None,
            strike_price_lte=str(strike_price_lte) if strike_price_lte is not None else None,
            limit=limit
        )
        response = client.get_option_contracts(request_params)
        contracts = []
        for contract in response.option_contracts:
            contracts.append({
                "symbol": str(contract.symbol),
                "underlying_symbol": str(contract.underlying_symbol),
                "strike_price": float(contract.strike_price),
                "expiration_date": str(contract.expiration_date),
                "type": str(contract.type),
                "style": str(contract.style),
                "open_interest": int(contract.open_interest) if contract.open_interest else 0,
                "close_price": float(contract.close_price) if contract.close_price else None
            })
        return contracts
    except Exception as e:
        return [{"error": f"Failed to get option contracts: {str(e)}"}]


def _get_equity_quote(symbol: str) -> Dict[str, Any]:
    """
    Helper to fetch latest equity quote for underlying reference pricing.
    """
    client = _get_stock_data_client()
    request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
    quotes = client.get_stock_latest_quote(request)
    quote = quotes.get(symbol)
    if not quote:
        return {"error": f"No quote data for {symbol}"}
    bid = float(quote.bid_price) if quote.bid_price else None
    ask = float(quote.ask_price) if quote.ask_price else None
    mid = None
    if bid and ask:
        mid = (bid + ask) / 2
    return {
        "symbol": symbol,
        "bid_price": bid,
        "ask_price": ask,
        "mid_price": mid,
        "timestamp": str(quote.timestamp) if quote.timestamp else None
    }


def get_options_chain(
    underlying_symbol: str,
    expiration_date: Optional[str] = None,
    contract_type: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Retrieve a filtered options chain snapshot around the current underlying price.
    """
    try:
        quote = _get_equity_quote(underlying_symbol)
        if "error" in quote:
            return quote
        reference_price = quote.get("mid_price") or quote.get("bid_price") or quote.get("ask_price")
        if reference_price is None:
            return {"error": f"Missing price data for {underlying_symbol}"}
        
        client = _get_trading_client()
        request_params = GetOptionContractsRequest(
            underlying_symbols=[underlying_symbol],
            status=AssetStatus.ACTIVE,
            expiration_date=expiration_date,
            limit=1000
        )
        contracts_response = client.get_option_contracts(request_params)
        contracts = contracts_response.option_contracts
        
        calls = sorted(
            [
                c for c in contracts
                if c.type == ContractType.CALL and float(c.strike_price) >= reference_price
            ],
            key=lambda c: float(c.strike_price)
        )
        puts = sorted(
            [
                c for c in contracts
                if c.type == ContractType.PUT and float(c.strike_price) <= reference_price
            ],
            key=lambda c: float(c.strike_price),
            reverse=True
        )
        
        if contract_type and contract_type.lower() == "call":
            selected = calls[:limit]
        elif contract_type and contract_type.lower() == "put":
            selected = puts[:limit]
        else:
            half = max(1, limit // 2)
            selected = calls[:half] + puts[:half]
        
        chain = []
        for contract in selected:
            chain.append({
                "symbol": str(contract.symbol),
                "type": str(contract.type),
                "strike_price": float(contract.strike_price),
                "expiration_date": str(contract.expiration_date),
                "open_interest": int(contract.open_interest) if contract.open_interest else 0
            })
        
        return {
            "underlying_symbol": underlying_symbol,
            "reference_price": reference_price,
            "contracts": chain,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": f"Failed to get options chain: {str(e)}"}


def get_option_quote(symbol: str) -> Dict[str, Any]:
    """
    Get the latest quote for a specific option contract.
    """
    try:
        client = _get_option_data_client()
        request = OptionLatestQuoteRequest(symbol_or_symbols=symbol)
        quotes = client.get_option_latest_quote(request)
        quote = quotes.get(symbol)
        if not quote:
            return {"symbol": symbol, "error": "No option quote data available"}
        bid = _safe_float(getattr(quote, "bid_price", None))
        ask = _safe_float(getattr(quote, "ask_price", None))
        mid = (bid + ask) / 2 if bid is not None and ask is not None else None

        greeks_source = getattr(quote, "greeks", None) or quote
        greeks = {
            "delta": _safe_float(getattr(greeks_source, "delta", None)),
            "gamma": _safe_float(getattr(greeks_source, "gamma", None)),
            "theta": _safe_float(getattr(greeks_source, "theta", None)),
            "vega": _safe_float(getattr(greeks_source, "vega", None)),
            "rho": _safe_float(getattr(greeks_source, "rho", None)),
            "implied_volatility": _safe_float(
                getattr(greeks_source, "iv", None) or getattr(greeks_source, "implied_volatility", None)
            )
        }

        return {
            "symbol": symbol,
            "bid_price": bid,
            "ask_price": ask,
            "mid_price": mid,
            "bid_size": int(quote.bid_size) if quote.bid_size else None,
            "ask_size": int(quote.ask_size) if quote.ask_size else None,
            "timestamp": str(quote.timestamp) if getattr(quote, "timestamp", None) else None,
            "delta": greeks["delta"],
            "gamma": greeks["gamma"],
            "theta": greeks["theta"],
            "vega": greeks["vega"],
            "rho": greeks["rho"],
            "implied_volatility": greeks["implied_volatility"]
        }
    except Exception as e:
        return {"error": f"Failed to get option quote for {symbol}: {str(e)}"}


def _map_time_in_force(tif: str) -> TimeInForce:
    mapping = {
        "day": TimeInForce.DAY,
        "gtc": TimeInForce.GTC,
        "opg": TimeInForce.OPG,
        "ioc": TimeInForce.IOC,
        "fok": TimeInForce.FOK
    }
    return mapping.get(tif.lower(), TimeInForce.DAY)


def place_option_order(
    symbol: str,
    side: str,
    quantity: int,
    order_type: str = "market",
    limit_price: Optional[float] = None,
    time_in_force: str = "day"
) -> Dict[str, Any]:
    """
    Submit a single-leg option order.
    """
    try:
        client = _get_trading_client()
        tif_enum = _map_time_in_force(time_in_force)
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        order_type_lower = order_type.lower()
        
        if order_type_lower == "market":
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                time_in_force=tif_enum,
                asset_class=AssetClass.OPTION
            )
        elif order_type_lower == "limit" and limit_price is not None:
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=quantity,
                limit_price=limit_price,
                side=order_side,
                time_in_force=tif_enum,
                asset_class=AssetClass.OPTION
            )
        else:
            return {"error": "Invalid order type or missing limit_price"}
        
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
        return {"error": f"Failed to place option order: {str(e)}"}


def place_multi_leg_option_order(
    legs: List[Dict[str, Any]],
    quantity: int,
    order_type: str = "market",
    limit_price: Optional[float] = None,
    time_in_force: str = "day"
) -> Dict[str, Any]:
    """
    Submit a multi-leg option strategy order.
    """
    try:
        client = _get_trading_client()
        tif_enum = _map_time_in_force(time_in_force)
        option_legs = []
        for leg in legs:
            ratio_qty = leg.get("ratio_qty", 1)
            option_legs.append(
                OptionLegRequest(
                    symbol=leg["symbol"],
                    side=OrderSide.BUY if leg["side"].lower() == "buy" else OrderSide.SELL,
                    ratio_qty=float(ratio_qty)
                )
            )
        
        order_type_lower = order_type.lower()
        if order_type_lower == "market":
            order_data = MarketOrderRequest(
                qty=quantity,
                order_class=OrderClass.MLEG,
                time_in_force=tif_enum,
                legs=option_legs
            )
        elif order_type_lower == "limit" and limit_price is not None:
            order_data = LimitOrderRequest(
                qty=quantity,
                limit_price=limit_price,
                order_class=OrderClass.MLEG,
                time_in_force=tif_enum,
                legs=option_legs
            )
        else:
            return {"error": "Invalid order type or missing limit_price"}
        
        order = client.submit_order(order_data)
        return {
            "order_id": str(order.id),
            "status": str(order.status),
            "quantity": float(order.qty),
            "order_type": str(order.type),
            "submitted_at": str(order.submitted_at),
            "legs": len(legs)
        }
    except Exception as e:
        return {"error": f"Failed to place multi-leg option order: {str(e)}"}


def close_option_position(symbol: str, quantity: Optional[int] = None) -> Dict[str, Any]:
    """
    Close an existing option position using Alpaca's close_position endpoint.
    """
    try:
        client = _get_trading_client()
        close_request = ClosePositionRequest(
            qty=str(quantity) if quantity is not None else None
        )
        # Validate that an open position exists before attempting to close.
        try:
            client.get_open_position(symbol)
        except Exception as lookup_error:
            return {"error": f"No open position found for {symbol}: {lookup_error}"}

        result = client.close_position(symbol_or_asset_id=symbol, close_options=close_request)
        return {
            "order_id": str(getattr(result, "id", "")),
            "symbol": str(getattr(result, "symbol", symbol)),
            "quantity": float(getattr(result, "qty", quantity or 0)),
            "status": str(getattr(result, "status", "submitted"))
        }
    except Exception as e:
        return {"error": f"Failed to close option position: {str(e)}"}


def get_option_order_history(limit: int = 20) -> List[Dict]:
    """
    Retrieve recent option orders only.
    """
    try:
        client = _get_trading_client()
        request_params = GetOrdersRequest(
            status=QueryOrderStatus.ALL,
            limit=limit
        )
        try:
            orders = client.get_orders(filter=request_params)
        except TypeError:
            orders = client.get_orders(status='all', limit=limit)
        option_orders = []
        for order in orders:
            asset_class = str(getattr(order, 'asset_class', '')).lower()
            if 'option' not in asset_class:
                continue
            option_orders.append({
                "order_id": str(order.id),
                "symbol": str(order.symbol),
                "side": str(order.side),
                "quantity": float(order.qty),
                "status": str(order.status),
                "order_type": str(order.type),
                "submitted_at": str(order.submitted_at),
                "filled_at": str(order.filled_at) if order.filled_at else None,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None
            })
        return option_orders
    except Exception as e:
        return [{"error": f"Failed to get option order history: {str(e)}"}]

def get_order_history(limit: int = 10) -> List[Dict]:
    """
    Get recent order history.
    Returns list of recent orders with status and fill information.
    """
    try:
        client = _get_trading_client()
        request_params = GetOrdersRequest(
            status=QueryOrderStatus.ALL,
            limit=limit
        )
        try:
            orders = client.get_orders(filter=request_params)
        except TypeError:
            # Fallback for older alpaca-py versions
            orders = client.get_orders(status='all', limit=limit)
        
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

def get_price_bars(symbol: str, timeframe: str = "1Hour", limit: int = 100) -> Dict:
    """
    Get historical price bars (OHLCV) for an equity or ETF.
    """
    try:
        client = _get_stock_data_client()
        
        timeframe_map = {
            "1Min": TimeFrame.Minute,
            "5Min": TimeFrame(5, "Min"),
            "15Min": TimeFrame(15, "Min"),
            "1Hour": TimeFrame.Hour,
            "1Day": TimeFrame.Day
        }
        tf = timeframe_map.get(timeframe, TimeFrame.Hour)
        
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            limit=limit
        )
        bars = client.get_stock_bars(request_params)
        df = bars.df
        if df.empty:
            return {"error": "No data returned"}
        
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
        return {"error": f"Failed to get price bars: {str(e)}"}

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

