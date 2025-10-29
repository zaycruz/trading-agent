"""
Alpaca Trading Tools for Autonomous Options Trader
Designed for use with Ollama models and LangChain

Features:
- Portfolio analysis and position tracking
- Options contract screening and fetching
- Options buying and selling
- Multi-leg options strategies
- Account awareness and risk management
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOptionContractsRequest
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce, OrderClass
from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest, OptionLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

# Configuration
class TradingConfig(BaseModel):
    api_key: str
    secret_key: str
    base_url: str = "https://paper-api.alpaca.markets"  # Paper trading by default
    data_url: str = "https://data.alpaca.markets"
    paper_trading: bool = True

# Initialize Alpaca API
config = TradingConfig(
    api_key=os.getenv("ALPACA_API_KEY", ""),
    secret_key=os.getenv("ALPACA_SECRET_KEY", ""),
    paper_trading=True
)

# Use Alpaca's enums
class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"

class OptionStrategy(str, Enum):
    SINGLE = "single"
    VERTICAL_SPREAD = "vertical_spread"
    IRON_CONDOR = "iron_condor"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    BUTTERFLY = "butterfly"
    CALENDAR_SPREAD = "calendar_spread"

@dataclass
class Position:
    symbol: str
    quantity: int
    side: str
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float

@dataclass
class OptionContract:
    symbol: str
    strike: float
    expiration: str
    option_type: OptionType
    underlying_price: float
    bid: float
    ask: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float

class AlpacaTradingTools:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.trading_client = TradingClient(
            api_key=config.api_key,
            secret_key=config.secret_key,
            paper=config.paper_trading
        )
        self.stock_data_client = StockHistoricalDataClient(
            api_key=config.api_key,
            secret_key=config.secret_key
        )
        self.option_data_client = OptionHistoricalDataClient(
            api_key=config.api_key,
            secret_key=config.secret_key
        )

    # PORTFOLIO ANALYSIS TOOLS

    def get_account_info(self) -> Dict[str, Any]:
        """Get comprehensive account information including buying power and equity"""
        try:
            account = self.trading_client.get_account()
            return {
                "account_id": account.id,
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "equity": float(account.equity),
                "long_market_value": float(account.long_market_value),
                "short_market_value": float(account.short_market_value),
                "initial_margin": float(account.initial_margin),
                "maintenance_margin": float(account.maintenance_margin),
                "daytrading_buying_power": float(account.daytrading_buying_power),
                "regt_buying_power": float(account.regt_buying_power),
                "status": account.status,
                "trading_blocked": account.trading_blocked,
                "transfers_blocked": account.transfers_blocked,
                "account_blocked": account.account_blocked
            }
        except Exception as e:
            return {"error": f"Failed to get account info: {str(e)}"}

    def get_positions(self) -> List[Position]:
        """Get all current positions in the portfolio"""
        try:
            positions = self.trading_client.get_all_positions()
            position_list = []

            for pos in positions:
                position = Position(
                    symbol=pos.symbol,
                    quantity=int(pos.qty),
                    side=pos.side,
                    market_value=float(pos.market_value),
                    cost_basis=float(pos.cost_basis),
                    unrealized_pl=float(pos.unrealized_pl),
                    unrealized_plpc=float(pos.unrealized_plpc)
                )
                position_list.append(position)

            return position_list
        except Exception as e:
            print(f"Error getting positions: {e}")
            return []

    def get_portfolio_analysis(self) -> Dict[str, Any]:
        """Comprehensive portfolio analysis including risk metrics"""
        try:
            positions = self.get_positions()
            account = self.get_account_info()

            if not positions:
                return {"message": "No positions found", "account": account}

            total_value = sum([abs(pos.market_value) for pos in positions])
            total_unrealized = sum([pos.unrealized_pl for pos in positions])

            # Concentration analysis
            sector_exposure = {}
            position_analysis = []

            for pos in positions:
                weight_pct = (abs(pos.market_value) / total_value) * 100 if total_value > 0 else 0
                position_analysis.append({
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "market_value": pos.market_value,
                    "weight_pct": round(weight_pct, 2),
                    "unrealized_pl": pos.unrealized_pl,
                    "unrealized_pl_pct": pos.unrealized_plpc,
                    "risk_level": "HIGH" if weight_pct > 20 else "MEDIUM" if weight_pct > 10 else "LOW"
                })

            # Sort by market value
            position_analysis.sort(key=lambda x: x["market_value"], reverse=True)

            return {
                "account_summary": account,
                "total_positions": len(positions),
                "total_portfolio_value": total_value,
                "total_unrealized_pl": total_unrealized,
                "position_analysis": position_analysis,
                "risk_metrics": {
                    "largest_position_pct": position_analysis[0]["weight_pct"] if position_analysis else 0,
                    "position_count": len(positions),
                    "portfolio_concentration": "HIGH" if len(positions) < 5 else "MEDIUM" if len(positions) < 15 else "LOW"
                }
            }
        except Exception as e:
            return {"error": f"Portfolio analysis failed: {str(e)}"}

    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """Get specific position by symbol"""
        try:
            position = self.trading_client.get_open_position(symbol)
            return Position(
                symbol=position.symbol,
                quantity=int(position.qty),
                side=position.side,
                market_value=float(position.market_value),
                cost_basis=float(position.cost_basis),
                unrealized_pl=float(position.unrealized_pl),
                unrealized_plpc=float(position.unrealized_plpc)
            )
        except Exception as e:
            print(f"Position not found for {symbol}: {e}")
            return None

    # OPTIONS CONTRACT SCREENING AND FETCHING

    def get_options_chain(self, underlying_symbol: str, expiration_date: str = None) -> List[OptionContract]:
        """Get complete options chain for an underlying symbol"""
        try:
            # Get available expiration dates if not provided
            if not expiration_date:
                calendar = self.trading_client.get_calendar()
                today = datetime.now().date()
                future_dates = [date for date in calendar if date._date >= today]
                if not future_dates:
                    return []
                expiration_date = future_dates[0]._date.strftime('%Y-%m-%d')

            # Get options chain (this would use the options data endpoint)
            # Note: Actual implementation requires Alpaca's options data API
            # This is a placeholder structure
            option_contracts = []

            # In real implementation, you would call:
            # contracts = self.api.get_options_contracts(underlying_symbol, expiration_date)

            return option_contracts
        except Exception as e:
            print(f"Error getting options chain: {e}")
            return []

    def screen_options_contracts(self,
                                underlying_symbol: str,
                                min_dte: int = 7,
                                max_dte: int = 60,
                                min_volume: int = 10,
                                min_open_interest: int = 50,
                                target_strikes_pct: List[float] = [0.8, 0.9, 1.0, 1.1, 1.2]) -> List[OptionContract]:
        """Screen options contracts based on specified criteria"""
        try:
            # Get current price of underlying
            current_price = self.get_current_price(underlying_symbol)
            if not current_price:
                return []

            # Get expiration dates within range
            expiration_dates = self.get_expiration_dates(min_dte, max_dte)
            if not expiration_dates:
                return []

            screened_contracts = []

            for exp_date in expiration_dates:
                contracts = self.get_options_chain(underlying_symbol, exp_date)

                for contract in contracts:
                    # Filter by volume and open interest
                    if contract.volume < min_volume or contract.open_interest < min_open_interest:
                        continue

                    # Filter by strike range
                    strike_pct = contract.strike / current_price
                    if any(abs(strike_pct - target) < 0.05 for target in target_strikes_pct):
                        screened_contracts.append(contract)

            # Sort by volume and open interest
            screened_contracts.sort(key=lambda x: (x.volume + x.open_interest), reverse=True)

            return screened_contracts[:50]  # Return top 50 contracts
        except Exception as e:
            print(f"Error screening options: {e}")
            return []

    def get_expiration_dates(self, min_dte: int = 7, max_dte: int = 60) -> List[str]:
        """Get available expiration dates within DTE range"""
        try:
            calendar = self.trading_client.get_calendar()
            today = datetime.now().date()

            exp_dates = []
            for date in calendar:
                days_to_exp = (date._date - today).days
                if min_dte <= days_to_exp <= max_dte:
                    exp_dates.append(date._date.strftime('%Y-%m-%d'))

            return exp_dates
        except Exception as e:
            print(f"Error getting expiration dates: {e}")
            return []

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price of a symbol"""
        try:
            quote_params = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self.stock_data_client.get_stock_latest_quote(quote_params)
            if quote:
                quote = quote[symbol]
            return float((quote.bid_price + quote.ask_price) / 2)
        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
            return None

    # OPTIONS BUYING AND SELLING

    def buy_option_contract(self,
                           symbol: str,
                           quantity: int,
                           order_type: str = "market",
                           limit_price: float = None,
                           time_in_force: str = "day") -> Dict[str, Any]:
        """Buy an options contract"""
        try:
            if order_type == "limit":
                order_data = LimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    limit_price=limit_price
                )
            else:
                order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                )

            order = self.trading_client.submit_order(order_data)

            return {
                "success": True,
                "order_id": order.id,
                "symbol": symbol,
                "quantity": quantity,
                "order_type": order_type.value,
                "status": order.status
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sell_option_contract(self,
                            symbol: str,
                            quantity: int,
                            order_type: str = "market",
                            limit_price: float = None,
                            time_in_force: str = "day") -> Dict[str, Any]:
        """Sell an options contract"""
        try:
            if order_type == "limit":
                order_data = LimitOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                    limit_price=limit_price
                )
            else:
                order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=quantity,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )

            order = self.trading_client.submit_order(order_data)

            return {
                "success": True,
                "order_id": order.id,
                "symbol": symbol,
                "quantity": quantity,
                "order_type": order_type.value,
                "status": order.status
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close_option_position(self, symbol: str, quantity: int = None) -> Dict[str, Any]:
        """Close an options position"""
        try:
            position = self.get_position_by_symbol(symbol)
            if not position:
                return {"success": False, "error": f"No position found for {symbol}"}

            close_quantity = abs(quantity) if quantity else abs(position.quantity)
            side = OrderSide.SELL if position.quantity > 0 else OrderSide.BUY

            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=close_quantity,
                side=side,
                time_in_force=TimeInForce.DAY
            )

            order = self.trading_client.submit_order(order_data)

            return {
                "success": True,
                "order_id": order.id,
                "symbol": symbol,
                "quantity_closed": close_quantity,
                "original_position": position.quantity,
                "status": order.status
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # MULTI-LEG OPTIONS STRATEGIES

    def create_vertical_spread(self,
                              underlying_symbol: str,
                              spread_type: str,  # "call_credit", "call_debit", "put_credit", "put_debit"
                              short_strike: float,
                              long_strike: float,
                              expiration_date: str,
                              quantity: int = 1,
                              credit_limit: float = None,
                              debit_limit: float = None) -> Dict[str, Any]:
        """Create a vertical spread strategy"""
        try:
            # Validate spread parameters
            if spread_type not in ["call_credit", "call_debit", "put_credit", "put_debit"]:
                return {"success": False, "error": "Invalid spread type"}

            # Determine option symbols (this would need options data API)
            # For now, return structure
            strategy = {
                "strategy_type": "vertical_spread",
                "spread_type": spread_type,
                "underlying": underlying_symbol,
                "expiration": expiration_date,
                "short_strike": short_strike,
                "long_strike": long_strike,
                "quantity": quantity,
                "credit_limit": credit_limit,
                "debit_limit": debit_limit
            }

            return {"success": True, "strategy": strategy, "message": "Vertical spread structure created"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_iron_condor(self,
                          underlying_symbol: str,
                          short_call_strike: float,
                          long_call_strike: float,
                          short_put_strike: float,
                          long_put_strike: float,
                          expiration_date: str,
                          quantity: int = 1,
                          credit_target: float = None) -> Dict[str, Any]:
        """Create an iron condor strategy"""
        try:
            # Validate strikes
            if not (long_call_strike > short_call_strike > short_put_strike > long_put_strike):
                return {"success": False, "error": "Invalid strike arrangement for iron condor"}

            strategy = {
                "strategy_type": "iron_condor",
                "underlying": underlying_symbol,
                "expiration": expiration_date,
                "strikes": {
                    "long_call": long_call_strike,
                    "short_call": short_call_strike,
                    "short_put": short_put_strike,
                    "long_put": long_put_strike
                },
                "quantity": quantity,
                "credit_target": credit_target,
                "max_loss": (long_call_strike - short_call_strike - short_put_strike + long_put_strike) * 100 * quantity
            }

            return {"success": True, "strategy": strategy, "message": "Iron condor structure created"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_straddle(self,
                       underlying_symbol: str,
                       strike: float,
                       expiration_date: str,
                       quantity: int = 1) -> Dict[str, Any]:
        """Create a straddle strategy (long call and long put at same strike)"""
        try:
            strategy = {
                "strategy_type": "straddle",
                "underlying": underlying_symbol,
                "expiration": expiration_date,
                "strike": strike,
                "quantity": quantity,
                "contracts": [
                    {"type": "call", "strike": strike, "side": "buy"},
                    {"type": "put", "strike": strike, "side": "buy"}
                ]
            }

            return {"success": True, "strategy": strategy, "message": "Straddle structure created"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_strangle(self,
                       underlying_symbol: str,
                       call_strike: float,
                       put_strike: float,
                       expiration_date: str,
                       quantity: int = 1) -> Dict[str, Any]:
        """Create a strangle strategy (out-of-the-money call and put)"""
        try:
            strategy = {
                "strategy_type": "strangle",
                "underlying": underlying_symbol,
                "expiration": expiration_date,
                "strikes": {
                    "call": call_strike,
                    "put": put_strike
                },
                "quantity": quantity,
                "contracts": [
                    {"type": "call", "strike": call_strike, "side": "buy"},
                    {"type": "put", "strike": put_strike, "side": "buy"}
                ]
            }

            return {"success": True, "strategy": strategy, "message": "Strangle structure created"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ACCOUNT AWARENESS AND RISK MANAGEMENT

    def check_buying_power(self, order_cost: float) -> Dict[str, Any]:
        """Check if account has sufficient buying power for a trade"""
        try:
            account = self.get_account_info()
            buying_power = account.get("buying_power", 0)

            return {
                "sufficient_funds": buying_power >= order_cost,
                "required": order_cost,
                "available": buying_power,
                "remaining_after_trade": buying_power - order_cost,
                "utilization_pct": (order_cost / buying_power * 100) if buying_power > 0 else 0
            }
        except Exception as e:
            return {"error": f"Failed to check buying power: {str(e)}"}

    def calculate_position_risk(self, symbol: str, quantity: int) -> Dict[str, Any]:
        """Calculate risk metrics for a potential position"""
        try:
            current_price = self.get_current_price(symbol)
            if not current_price:
                return {"error": "Could not get current price"}

            position_value = current_price * quantity * 100  # Options are 100 shares per contract
            account = self.get_account_info()
            portfolio_value = account.get("portfolio_value", 1)

            return {
                "symbol": symbol,
                "quantity": quantity,
                "current_price": current_price,
                "position_value": position_value,
                "portfolio_concentration_pct": (position_value / portfolio_value * 100) if portfolio_value > 0 else 0,
                "risk_level": "HIGH" if position_value / portfolio_value > 0.1 else "MEDIUM" if position_value / portfolio_value > 0.05 else "LOW"
            }
        except Exception as e:
            return {"error": f"Risk calculation failed: {str(e)}"}

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary of the portfolio"""
        try:
            positions = self.get_positions()
            account = self.get_account_info()

            if not positions:
                return {"message": "No positions to analyze", "account": account}

            total_exposure = sum([abs(pos.market_value) for pos in positions])
            portfolio_value = account.get("portfolio_value", 1)

            # Calculate concentration metrics
            largest_position = max(positions, key=lambda x: abs(x.market_value))
            concentration_ratio = abs(largest_position.market_value) / total_exposure if total_exposure > 0 else 0

            # Unrealized P&L analysis
            total_unrealized = sum([pos.unrealized_pl for pos in positions])
            losing_positions = [pos for pos in positions if pos.unrealized_pl < 0]
            winning_positions = [pos for pos in positions if pos.unrealized_pl > 0]

            return {
                "total_exposure": total_exposure,
                "portfolio_concentration_pct": (total_exposure / portfolio_value * 100) if portfolio_value > 0 else 0,
                "largest_position": {
                    "symbol": largest_position.symbol,
                    "value": largest_position.market_value,
                    "concentration_pct": concentration_ratio * 100
                },
                "position_count": len(positions),
                "diversification_score": "GOOD" if len(positions) > 10 else "FAIR" if len(positions) > 5 else "POOR",
                "total_unrealized_pl": total_unrealized_pl,
                "losing_positions_count": len(losing_positions),
                "winning_positions_count": len(winning_positions),
                "risk_metrics": {
                    "max_drawdown": min([pos.unrealized_pl for pos in positions]) if positions else 0,
                    "risk_level": "HIGH" if concentration_ratio > 0.3 else "MEDIUM" if concentration_ratio > 0.2 else "LOW"
                }
            }
        except Exception as e:
            return {"error": f"Risk summary failed: {str(e)}"}

    def validate_trade_risk(self,
                           symbol: str,
                           quantity: int,
                           max_portfolio_pct: float = 0.25,
                           max_position_pct: float = 0.10) -> Dict[str, Any]:
        """Validate if a trade meets risk management criteria"""
        try:
            # Check position risk
            position_risk = self.calculate_position_risk(symbol, quantity)
            if "error" in position_risk:
                return {"approved": False, "reason": position_risk["error"]}

            # Check portfolio concentration
            current_positions = self.get_positions()
            portfolio_value = self.get_account_info().get("portfolio_value", 1)

            current_exposure = sum([abs(pos.market_value) for pos in current_positions])
            new_exposure = current_exposure + position_risk["position_value"]
            portfolio_concentration = new_exposure / portfolio_value if portfolio_value > 0 else 1

            # Check position concentration
            existing_position = next((pos for pos in current_positions if pos.symbol == symbol), None)
            if existing_position:
                total_position_value = abs(existing_position.market_value) + position_risk["position_value"]
                position_concentration = total_position_value / portfolio_value if portfolio_value > 0 else 1
            else:
                position_concentration = position_risk["portfolio_concentration_pct"] / 100

            approval = {
                "approved": True,
                "position_risk": position_risk,
                "portfolio_concentration_pct": portfolio_concentration * 100,
                "position_concentration_pct": position_concentration * 100,
                "warnings": []
            }

            # Add warnings or reject if limits exceeded
            if portfolio_concentration > max_portfolio_pct:
                approval["approved"] = False
                approval["warnings"].append(f"Portfolio concentration {portfolio_concentration*100:.1f}% exceeds limit {max_portfolio_pct*100:.1f}%")
            elif portfolio_concentration > max_portfolio_pct * 0.8:
                approval["warnings"].append(f"Portfolio concentration {portfolio_concentration*100:.1f}% approaching limit")

            if position_concentration > max_position_pct:
                approval["approved"] = False
                approval["warnings"].append(f"Position concentration {position_concentration*100:.1f}% exceeds limit {max_position_pct*100:.1f}%")
            elif position_concentration > max_position_pct * 0.8:
                approval["warnings"].append(f"Position concentration {position_concentration*100:.1f}% approaching limit")

            return approval
        except Exception as e:
            return {"approved": False, "reason": f"Risk validation failed: {str(e)}"}

# Initialize the trading tools instance
trading_tools = AlpacaTradingTools(config)

# Tool functions for LangChain/Ollama integration
def get_account_info() -> Dict[str, Any]:
    """Get account information including buying power and positions"""
    return trading_tools.get_account_info()

def analyze_portfolio() -> Dict[str, Any]:
    """Comprehensive portfolio analysis with risk metrics"""
    return trading_tools.get_portfolio_analysis()

def get_positions() -> List[Position]:
    """Get all current positions"""
    return trading_tools.get_positions()

def screen_options(underlying_symbol: str, min_dte: int = 7, max_dte: int = 60) -> List[OptionContract]:
    """Screen options contracts based on volume, open interest, and other criteria"""
    return trading_tools.screen_options_contracts(underlying_symbol, min_dte, max_dte)

def buy_option(symbol: str, quantity: int, order_type: str = "market", limit_price: float = None) -> Dict[str, Any]:
    """Buy an options contract"""
    return trading_tools.buy_option_contract(symbol, quantity, OrderType(order_type), limit_price)

def sell_option(symbol: str, quantity: int, order_type: str = "market", limit_price: float = None) -> Dict[str, Any]:
    """Sell an options contract"""
    return trading_tools.sell_option_contract(symbol, quantity, OrderType(order_type), limit_price)

def close_position(symbol: str, quantity: int = None) -> Dict[str, Any]:
    """Close an options position"""
    return trading_tools.close_option_position(symbol, quantity)

def create_vertical_spread(underlying: str, spread_type: str, short_strike: float,
                          long_strike: float, expiration: str, quantity: int = 1) -> Dict[str, Any]:
    """Create a vertical spread strategy"""
    return trading_tools.create_vertical_spread(underlying, spread_type, short_strike,
                                               long_strike, expiration, quantity)

def create_iron_condor(underlying: str, short_call: float, long_call: float,
                      short_put: float, long_put: float, expiration: str,
                      quantity: int = 1) -> Dict[str, Any]:
    """Create an iron condor strategy"""
    return trading_tools.create_iron_condor(underlying, short_call, long_call,
                                           short_put, long_put, expiration, quantity)

def validate_trade_risk(symbol: str, quantity: int) -> Dict[str, Any]:
    """Validate if a trade meets risk management criteria"""
    return trading_tools.validate_trade_risk(symbol, quantity)

def get_risk_summary() -> Dict[str, Any]:
    """Get comprehensive risk summary of the portfolio"""
    return trading_tools.get_risk_summary()