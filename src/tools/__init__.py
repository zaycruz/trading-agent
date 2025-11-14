"""
Unified Tools Module
All agent-callable tools exposed via a single interface.
"""

from __future__ import annotations

# Import all tools from their respective modules
from .alpaca import (
    get_account_info,
    get_option_positions,
    get_option_contracts,
    get_options_chain,
    get_option_quote,
    place_option_order,
    place_multi_leg_option_order,
    close_option_position,
    get_option_order_history,
    cancel_order,
    get_current_datetime,
)

from .analysis import (
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    calculate_bollinger_bands,
    get_price_momentum,
    get_support_resistance,
    analyze_multi_timeframes,
    analyze_option_greeks,
    screen_options_market,
)

from .web_search import (
    get_market_sentiment,
    search_technical_analysis,
    search_general_web,
)

from .history import (
    get_decision_history,
    get_performance_summary,
    get_daily_pnl,
    log_trading_decision,
    save_decision,  # For agent internal use
)

__all__ = [
    # Account & Trading
    "get_account_info",
    "get_option_positions",
    "get_option_contracts",
    "get_options_chain",
    "get_option_quote",
    "place_option_order",
    "place_multi_leg_option_order",
    "close_option_position",
    "get_option_order_history",
    "cancel_order",
    "get_current_datetime",
    # Technical Analysis
    "calculate_rsi",
    "calculate_macd",
    "calculate_moving_averages",
    "calculate_bollinger_bands",
    "get_price_momentum",
    "get_support_resistance",
    "analyze_multi_timeframes",
    "analyze_option_greeks",
    "screen_options_market",
    # Market Research
    "get_market_sentiment",
    "search_technical_analysis",
    "search_general_web",
    # Decision History & Logging
    "get_decision_history",
    "get_performance_summary",
    "get_daily_pnl",
    "log_trading_decision",
    "save_decision",
]

