"""
Technical Analysis Tools for Options Underlyings
All functions designed to be called by LLM via Ollama tool calling.
Uses pandas and numpy for calculations.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Import from alpaca_tools to get price data
from alpaca_tools import (
    get_price_bars,
    get_options_chain,
    get_option_quote,
    get_option_contracts
)

DEFAULT_RISK_FREE_RATE = 0.03


def _parse_expiration(expiration_str: str) -> Optional[datetime]:
    if not expiration_str:
        return None
    try:
        dt = datetime.fromisoformat(expiration_str)
    except ValueError:
        try:
            dt = datetime.fromisoformat(expiration_str.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _norm_pdf(x: float) -> float:
    return (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _black_scholes_price(is_call: bool, s: float, k: float, t: float, r: float, sigma: float) -> float:
    if s <= 0 or k <= 0 or t <= 0 or sigma <= 0:
        return 0.0
    d1 = (math.log(s / k) + (r + 0.5 * sigma ** 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    if is_call:
        return s * _norm_cdf(d1) - k * math.exp(-r * t) * _norm_cdf(d2)
    return k * math.exp(-r * t) * _norm_cdf(-d2) - s * _norm_cdf(-d1)


def _implied_volatility(target_price: float, is_call: bool, s: float, k: float, t: float, r: float) -> Optional[float]:
    if target_price is None or target_price <= 0 or s <= 0 or k <= 0 or t <= 0:
        return None

    intrinsic = max(0.0, s - k) if is_call else max(0.0, k - s)
    if target_price <= intrinsic + 1e-4:
        return 1e-4

    low, high = 1e-4, 5.0
    for _ in range(80):
        mid = (low + high) / 2
        price = _black_scholes_price(is_call, s, k, t, r, mid)
        if abs(price - target_price) < 1e-4:
            return mid
        if price > target_price:
            high = mid
        else:
            low = mid
    return mid


def _compute_black_scholes_greeks(is_call: bool, s: float, k: float, t: float, r: float, sigma: float) -> Dict[str, float]:
    if s <= 0 or k <= 0 or t <= 0 or sigma is None or sigma <= 0:
        return {}
    d1 = (math.log(s / k) + (r + 0.5 * sigma ** 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    delta = _norm_cdf(d1) if is_call else _norm_cdf(d1) - 1
    gamma = _norm_pdf(d1) / (s * sigma * math.sqrt(t))
    vega = s * _norm_pdf(d1) * math.sqrt(t) / 100  # per 1% change
    theta = (
        (-s * _norm_pdf(d1) * sigma) / (2 * math.sqrt(t))
        - r * k * math.exp(-r * t) * _norm_cdf(d2 if is_call else -d2)
    ) / 365
    rho = (k * t * math.exp(-r * t) * _norm_cdf(d2)) / 100 if is_call else (-k * t * math.exp(-r * t) * _norm_cdf(-d2)) / 100
    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 4),
        "vega": round(vega, 4),
        "rho": round(rho, 4),
        "implied_volatility": round(sigma, 4)
    }


def _approximate_greeks_from_price(
    option_type: str,
    underlying_price: Optional[float],
    strike_price: Optional[float],
    expiration_date: Optional[str],
    option_mid_price: Optional[float],
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE
) -> Dict[str, Optional[float]]:
    if (
        underlying_price is None
        or strike_price is None
        or option_mid_price is None
        or expiration_date is None
    ):
        return {}
    expiration_dt = _parse_expiration(expiration_date)
    if not expiration_dt:
        return {}
    now = datetime.now(timezone.utc)
    t = (expiration_dt - now).total_seconds() / (365 * 24 * 3600)
    if t <= 0:
        return {}
    option_type = (option_type or "").lower()
    is_call = "call" in option_type or option_type.endswith("c")
    sigma = _implied_volatility(option_mid_price, is_call, underlying_price, strike_price, t, risk_free_rate)
    if sigma is None or sigma <= 0:
        return {}
    return _compute_black_scholes_greeks(is_call, underlying_price, strike_price, t, risk_free_rate, sigma)


# ============================================================================
# TOOL FUNCTIONS - Called by LLM via Ollama
# ============================================================================

def calculate_rsi(symbol: str, period: int = 14, timeframe: str = "1Hour") -> Dict:
    """
    Calculate RSI (Relative Strength Index) indicator.
    RSI values: >70 = overbought, <30 = oversold
    
    Args:
        symbol: Underlying symbol (e.g., "SPY")
        period: RSI period (default: 14)
        timeframe: Data timeframe (default: "1Hour")
    
    Returns RSI value, signal (overbought/oversold/neutral), and historical data.
    """
    try:
        # Get price data
        bars_data = get_price_bars(symbol, timeframe=timeframe, limit=period * 3)
        
        if "error" in bars_data:
            return bars_data
        
        # Extract close prices
        closes = bars_data['data']['close']
        df = pd.DataFrame({'close': closes})
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = float(rsi.iloc[-1])
        
        # Determine signal
        if current_rsi > 70:
            signal = "overbought"
        elif current_rsi < 30:
            signal = "oversold"
        else:
            signal = "neutral"
        
        return {
            "symbol": symbol,
            "indicator": "RSI",
            "period": period,
            "timeframe": timeframe,
            "current_value": round(current_rsi, 2),
            "signal": signal,
            "interpretation": f"RSI is {signal}. {'Consider selling' if signal == 'overbought' else 'Consider buying' if signal == 'oversold' else 'No strong signal'}"
        }
    except Exception as e:
        return {"error": f"Failed to calculate RSI: {str(e)}"}


def calculate_macd(symbol: str, timeframe: str = "1Hour") -> Dict:
    """
    Calculate MACD (Moving Average Convergence Divergence) indicator.
    MACD line crossing signal line indicates buy/sell signals.
    
    Args:
        symbol: Underlying symbol (e.g., "SPY")
        timeframe: Data timeframe (default: "1Hour")
    
    Returns MACD line, signal line, histogram, and crossover signal.
    """
    try:
        # Get price data
        bars_data = get_price_bars(symbol, timeframe=timeframe, limit=100)
        
        if "error" in bars_data:
            return bars_data
        
        # Extract close prices
        closes = bars_data['data']['close']
        df = pd.DataFrame({'close': closes})
        
        # Calculate MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        
        current_macd = float(macd_line.iloc[-1])
        current_signal = float(signal_line.iloc[-1])
        current_histogram = float(histogram.iloc[-1])
        prev_histogram = float(histogram.iloc[-2])
        
        # Determine crossover signal
        if current_histogram > 0 and prev_histogram <= 0:
            signal = "bullish_crossover"
        elif current_histogram < 0 and prev_histogram >= 0:
            signal = "bearish_crossover"
        elif current_histogram > 0:
            signal = "bullish"
        else:
            signal = "bearish"
        
        return {
            "symbol": symbol,
            "indicator": "MACD",
            "timeframe": timeframe,
            "macd_line": round(current_macd, 2),
            "signal_line": round(current_signal, 2),
            "histogram": round(current_histogram, 2),
            "signal": signal,
            "interpretation": f"MACD is {signal}. {'Consider buying' if 'bullish' in signal else 'Consider selling'}"
        }
    except Exception as e:
        return {"error": f"Failed to calculate MACD: {str(e)}"}


def calculate_moving_averages(symbol: str, periods: List[int] = [20, 50, 200], timeframe: str = "1Hour") -> Dict:
    """
    Calculate Simple Moving Averages (SMA) for multiple periods.
    Price above MA = bullish, below = bearish. Golden cross = bullish, death cross = bearish.
    
    Args:
        symbol: Underlying symbol (e.g., "SPY")
        periods: List of MA periods (default: [20, 50, 200])
        timeframe: Data timeframe (default: "1Hour")
    
    Returns MAs for each period, current price, and trend analysis.
    """
    try:
        # Get price data (use max period * 1.5 for stability)
        max_period = max(periods)
        bars_data = get_price_bars(symbol, timeframe=timeframe, limit=int(max_period * 1.5))
        
        if "error" in bars_data:
            return bars_data
        
        # Extract close prices
        closes = bars_data['data']['close']
        df = pd.DataFrame({'close': closes})
        current_price = closes[-1]
        
        # Calculate MAs
        moving_averages = {}
        for period in periods:
            ma = df['close'].rolling(window=period).mean()
            moving_averages[f"MA_{period}"] = round(float(ma.iloc[-1]), 2)
        
        # Determine trend
        price_above_all = all(current_price > ma for ma in moving_averages.values())
        price_below_all = all(current_price < ma for ma in moving_averages.values())
        
        if price_above_all:
            trend = "strong_bullish"
        elif price_below_all:
            trend = "strong_bearish"
        else:
            trend = "mixed"
        
        return {
            "symbol": symbol,
            "indicator": "Moving_Averages",
            "timeframe": timeframe,
            "current_price": round(current_price, 2),
            "moving_averages": moving_averages,
            "trend": trend,
            "interpretation": f"Price is {trend} relative to moving averages"
        }
    except Exception as e:
        return {"error": f"Failed to calculate MAs: {str(e)}"}


def calculate_bollinger_bands(symbol: str, period: int = 20, std_dev: int = 2, timeframe: str = "1Hour") -> Dict:
    """
    Calculate Bollinger Bands for volatility analysis.
    Price at upper band = overbought, at lower band = oversold.
    
    Args:
        symbol: Underlying symbol (e.g., "SPY")
        period: BB period (default: 20)
        std_dev: Standard deviations (default: 2)
        timeframe: Data timeframe (default: "1Hour")
    
    Returns upper/middle/lower bands, current price position, and volatility signal.
    """
    try:
        # Get price data
        bars_data = get_price_bars(symbol, timeframe=timeframe, limit=period * 2)
        
        if "error" in bars_data:
            return bars_data
        
        # Extract close prices
        closes = bars_data['data']['close']
        df = pd.DataFrame({'close': closes})
        current_price = closes[-1]
        
        # Calculate Bollinger Bands
        middle_band = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        current_upper = float(upper_band.iloc[-1])
        current_middle = float(middle_band.iloc[-1])
        current_lower = float(lower_band.iloc[-1])
        
        # Calculate bandwidth (volatility measure)
        bandwidth = ((current_upper - current_lower) / current_middle) * 100
        
        # Determine position
        if current_price >= current_upper:
            signal = "at_upper_band"
            interpretation = "Price at upper band - overbought, consider selling"
        elif current_price <= current_lower:
            signal = "at_lower_band"
            interpretation = "Price at lower band - oversold, consider buying"
        elif current_price > current_middle:
            signal = "above_middle"
            interpretation = "Price above middle band - bullish"
        else:
            signal = "below_middle"
            interpretation = "Price below middle band - bearish"
        
        return {
            "symbol": symbol,
            "indicator": "Bollinger_Bands",
            "timeframe": timeframe,
            "current_price": round(current_price, 2),
            "upper_band": round(current_upper, 2),
            "middle_band": round(current_middle, 2),
            "lower_band": round(current_lower, 2),
            "bandwidth_percent": round(bandwidth, 2),
            "signal": signal,
            "interpretation": interpretation
        }
    except Exception as e:
        return {"error": f"Failed to calculate Bollinger Bands: {str(e)}"}


def get_price_momentum(symbol: str, timeframe: str = "1Hour", periods: int = 20) -> Dict:
    """
    Calculate price momentum and rate of change.
    Positive momentum = bullish, negative = bearish.
    
    Args:
        symbol: Underlying symbol (e.g., "SPY")
        timeframe: Data timeframe (default: "1Hour")
        periods: Lookback period (default: 20)
    
    Returns momentum percentage, trend strength, and direction.
    """
    try:
        # Get price data
        bars_data = get_price_bars(symbol, timeframe=timeframe, limit=periods + 10)
        
        if "error" in bars_data:
            return bars_data
        
        # Extract close prices
        closes = bars_data['data']['close']
        
        current_price = closes[-1]
        past_price = closes[-periods]
        
        # Calculate momentum
        momentum_pct = ((current_price - past_price) / past_price) * 100
        
        # Determine strength
        if abs(momentum_pct) > 10:
            strength = "strong"
        elif abs(momentum_pct) > 5:
            strength = "moderate"
        else:
            strength = "weak"
        
        direction = "bullish" if momentum_pct > 0 else "bearish"
        
        return {
            "symbol": symbol,
            "indicator": "Price_Momentum",
            "timeframe": timeframe,
            "periods": periods,
            "current_price": round(current_price, 2),
            "past_price": round(past_price, 2),
            "momentum_percent": round(momentum_pct, 2),
            "direction": direction,
            "strength": strength,
            "interpretation": f"{strength} {direction} momentum over {periods} periods"
        }
    except Exception as e:
        return {"error": f"Failed to calculate momentum: {str(e)}"}


def get_support_resistance(symbol: str, timeframe: str = "1Day", lookback: int = 50) -> Dict:
    """
    Identify support and resistance levels using recent highs and lows.
    
    Args:
        symbol: Underlying symbol (e.g., "SPY")
        timeframe: Data timeframe (default: "1Day")
        lookback: Number of periods to analyze (default: 50)
    
    Returns support/resistance levels and current price position.
    """
    try:
        # Get price data
        bars_data = get_price_bars(symbol, timeframe=timeframe, limit=lookback)
        
        if "error" in bars_data:
            return bars_data
        
        # Extract price data
        highs = bars_data['data']['high']
        lows = bars_data['data']['low']
        closes = bars_data['data']['close']
        current_price = closes[-1]
        
        # Find recent high/low (resistance/support)
        resistance = max(highs)
        support = min(lows)
        
        # Calculate distance to levels
        distance_to_resistance = ((resistance - current_price) / current_price) * 100
        distance_to_support = ((current_price - support) / current_price) * 100
        
        return {
            "symbol": symbol,
            "indicator": "Support_Resistance",
            "timeframe": timeframe,
            "current_price": round(current_price, 2),
            "resistance_level": round(resistance, 2),
            "support_level": round(support, 2),
            "distance_to_resistance_pct": round(distance_to_resistance, 2),
            "distance_to_support_pct": round(distance_to_support, 2),
            "interpretation": f"Price {round(distance_to_support_pct, 1)}% above support, {round(distance_to_resistance_pct, 1)}% below resistance"
        }
    except Exception as e:
        return {"error": f"Failed to calculate support/resistance: {str(e)}"}


def analyze_multi_timeframes(
    symbol: str,
    timeframes: Optional[List[str]] = None,
    lookback: int = 60
) -> Dict:
    """
    Evaluate trend and momentum across multiple timeframes in a single call.

    Returns per-timeframe stats (price change, moving averages, volatility proxy)
    plus an aggregated sentiment summary.
    """
    try:
        timeframes = timeframes or ["15Min", "1Hour", "4Hour", "1Day"]
        if not timeframes:
            return {"error": "No timeframes provided"}

        analysis: List[Dict] = []
        trend_counts = {"bullish": 0, "bearish": 0, "neutral": 0}

        for timeframe in timeframes:
            bars_data = get_price_bars(symbol, timeframe=timeframe, limit=lookback)
            if "error" in bars_data:
                analysis.append({
                    "timeframe": timeframe,
                    "error": bars_data["error"]
                })
                continue

            closes = bars_data["data"].get("close", [])
            if len(closes) < 5:
                analysis.append({
                    "timeframe": timeframe,
                    "error": "Insufficient data"
                })
                continue

            current_price = closes[-1]
            start_price = closes[0]
            change_pct = ((current_price - start_price) / start_price) * 100 if start_price else 0.0

            short_window = min(10, len(closes))
            long_window = min(max(20, short_window), len(closes))
            short_ma = sum(closes[-short_window:]) / short_window
            long_ma = sum(closes[-long_window:]) / long_window

            if short_ma > long_ma * 1.001:
                trend = "bullish"
            elif short_ma < long_ma * 0.999:
                trend = "bearish"
            else:
                trend = "neutral"
            trend_counts[trend] += 1

            recent_slice = closes[-short_window:]
            volatility = ((max(recent_slice) - min(recent_slice)) / current_price) * 100 if current_price else 0.0

            analysis.append({
                "timeframe": timeframe,
                "current_price": round(current_price, 2),
                "change_percent": round(change_pct, 2),
                "short_ma": round(short_ma, 2),
                "long_ma": round(long_ma, 2),
                "trend": trend,
                "volatility_percent": round(volatility, 2)
            })

        total = sum(trend_counts.values()) or 1
        dominant_trend = max(trend_counts, key=trend_counts.get)

        summary = {
            "trend_counts": trend_counts,
            "dominant_trend": dominant_trend,
            "bullish_ratio": round(trend_counts["bullish"] / total, 2),
            "bearish_ratio": round(trend_counts["bearish"] / total, 2)
        }

        return {
            "symbol": symbol,
            "timeframes": timeframes,
            "analysis": analysis,
            "summary": summary
        }
    except Exception as e:
        return {"error": f"Failed multi-timeframe analysis: {str(e)}"}


def analyze_option_greeks(
    underlying: str,
    expiration_date: Optional[str] = None,
    contract_type: Optional[str] = None,
    limit: int = 10
) -> Dict:
    """
    Aggregate option greeks from an options chain snapshot.
    """
    try:
        chain = get_options_chain(
            underlying_symbol=underlying,
            expiration_date=expiration_date,
            contract_type=contract_type,
            limit=limit
        )
        if "error" in chain:
            return chain

        contracts = chain.get("contracts", [])
        reference_price = chain.get("reference_price")
        greek_fields = ["delta", "gamma", "theta", "vega", "rho", "implied_volatility"]
        totals = {field: 0.0 for field in greek_fields}
        counts = {field: 0 for field in greek_fields}
        coverage_denominator = max(len(contracts), 1)
        analyzed_contracts: List[Dict] = []
        approximation_used = False
        avg_open_interest = []
        avg_mid_prices = []
        avg_spreads = []

        for contract in contracts:
            quote = get_option_quote(contract["symbol"])
            row = {
                "symbol": contract["symbol"],
                "type": contract.get("type"),
                "strike_price": contract.get("strike_price"),
                "expiration_date": contract.get("expiration_date"),
                "open_interest": contract.get("open_interest"),
                "greeks_source": "feed"
            }
            if "error" in quote:
                row["error"] = quote["error"]
            else:
                for field in ["mid_price", "bid_price", "ask_price"]:
                    row[field] = quote.get(field)
                bid = row.get("bid_price")
                ask = row.get("ask_price")
                if bid is not None and ask is not None:
                    spread = round(ask - bid, 4)
                    row["bid_ask_spread"] = spread
                    avg_spreads.append(spread)
                mid = row.get("mid_price")
                if mid is not None:
                    avg_mid_prices.append(mid)
                oi = row.get("open_interest")
                if oi is not None:
                    avg_open_interest.append(oi)

                for field in greek_fields:
                    value = quote.get(field)
                    if value is not None:
                        row[field] = value
                        totals[field] += value
                        counts[field] += 1

                missing_greeks = all(row.get(field) is None for field in greek_fields)
                if missing_greeks:
                    approx = _approximate_greeks_from_price(
                        option_type=row.get("type"),
                        underlying_price=reference_price,
                        strike_price=row.get("strike_price"),
                        expiration_date=row.get("expiration_date"),
                        option_mid_price=row.get("mid_price"),
                        risk_free_rate=DEFAULT_RISK_FREE_RATE
                    )
                    if approx:
                        approximation_used = True
                        row["greeks_source"] = "approximation"
                        for field in greek_fields:
                            value = approx.get(field)
                            if value is not None:
                                row[field] = value
                                totals[field] += value
                                counts[field] += 1
                    else:
                        row["greeks_source"] = "unavailable"

            analyzed_contracts.append(row)

        summary = {
            f"avg_{field}": (totals[field] / counts[field]) if counts[field] else None
            for field in greek_fields
        }
        coverage = {
            field: round(counts[field] / coverage_denominator, 2)
            for field in greek_fields
        }
        summary["coverage"] = coverage
        if approximation_used:
            summary["notes"] = "Approximate greeks computed via Black-Scholes for contracts lacking feed data."
        elif all(counts[field] == 0 for field in greek_fields):
            summary["notes"] = "Data provider returned no greek fields for the requested slice."

        return {
            "underlying": underlying,
            "reference_price": chain.get("reference_price"),
            "contracts_analyzed": len(analyzed_contracts),
            "summary": summary,
            "liquidity": {
                "avg_open_interest": round(sum(avg_open_interest) / len(avg_open_interest), 2) if avg_open_interest else None,
                "avg_mid_price": round(sum(avg_mid_prices) / len(avg_mid_prices), 4) if avg_mid_prices else None,
                "avg_bid_ask_spread": round(sum(avg_spreads) / len(avg_spreads), 4) if avg_spreads else None
            },
            "contracts": analyzed_contracts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"error": f"Failed to analyze option greeks: {str(e)}"}


def screen_options_market(
    underlyings: List[str],
    min_open_interest: int = 500,
    max_days_to_expiration: int = 45,
    moneyness_tolerance: float = 0.1,
    contract_type: Optional[str] = None,
    max_contracts_per_symbol: int = 5
) -> Dict:
    """
    Lightweight options screener to narrow trading focus.
    Filters by open interest, days to expiration, and moneyness.
    """
    try:
        today = datetime.now(timezone.utc).date()
        screened: List[Dict] = []

        for symbol in underlyings:
            price_data = get_price_bars(symbol, timeframe="1Day", limit=1)
            reference_price = None
            if "error" not in price_data:
                closes = price_data.get("data", {}).get("close", [])
                if closes:
                    reference_price = closes[-1]

            contracts = get_option_contracts(
                underlying_symbol=symbol,
                contract_type=contract_type,
                limit=200
            )
            if isinstance(contracts, list) and contracts and "error" in contracts[0]:
                continue

            filtered: List[Dict] = []
            for contract in contracts:
                expiration_raw = contract.get("expiration_date")
                if not expiration_raw:
                    continue
                try:
                    exp_date = datetime.fromisoformat(expiration_raw.replace("Z", "+00:00")).date()
                except ValueError:
                    continue
                dte = (exp_date - today).days
                if dte < 0 or dte > max_days_to_expiration:
                    continue
                if contract.get("open_interest", 0) < min_open_interest:
                    continue

                if reference_price:
                    moneyness = abs(contract.get("strike_price") - reference_price) / reference_price
                    if moneyness > moneyness_tolerance:
                        continue
                else:
                    moneyness = None

                filtered.append({
                    "underlying": symbol,
                    "symbol": contract.get("symbol"),
                    "type": contract.get("type"),
                    "strike_price": contract.get("strike_price"),
                    "expiration_date": expiration_raw,
                    "days_to_expiration": dte,
                    "open_interest": contract.get("open_interest"),
                    "close_price": contract.get("close_price"),
                    "moneyness": moneyness
                })

            filtered.sort(key=lambda c: c.get("open_interest", 0), reverse=True)
            screened.extend(filtered[:max_contracts_per_symbol])

        screened.sort(key=lambda c: c.get("open_interest", 0), reverse=True)

        return {
            "results": screened,
            "summary": {
                "total_underlyings": len(underlyings),
                "candidates": len(screened),
                "criteria": {
                    "min_open_interest": min_open_interest,
                    "max_days_to_expiration": max_days_to_expiration,
                    "moneyness_tolerance": moneyness_tolerance,
                    "contract_type": contract_type,
                    "max_contracts_per_symbol": max_contracts_per_symbol
                }
            }
        }
    except Exception as e:
        return {"error": f"Failed to screen options: {str(e)}"}
