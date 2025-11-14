"""
Autonomous Options Trading Agent
Pure tool-based approach - LLM makes ALL decisions via Ollama tool calling.
"""

import json
import time
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ollama import chat

# Import all tool functions
from tools.history import save_decision
from tools import (
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
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    calculate_bollinger_bands,
    get_price_momentum,
    get_support_resistance,
    analyze_multi_timeframes,
    analyze_option_greeks,
    screen_options_market,
    get_market_sentiment,
    search_technical_analysis,
    search_general_web,
    get_decision_history,
    get_performance_summary,
    get_daily_pnl,
    log_trading_decision
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _message_to_dict(message: Any) -> Dict[str, Any]:
    """
    Normalize Ollama message objects (dict or Pydantic) into plain dicts.
    """
    if message is None:
        return {"role": "assistant", "content": ""}
    if isinstance(message, dict):
        return message
    if hasattr(message, "model_dump"):
        dumped = message.model_dump()
        if isinstance(dumped, dict):
            return dumped
    normalized = {}
    for attr in ("role", "content", "name", "tool_calls"):
        if hasattr(message, attr):
            normalized[attr] = getattr(message, attr)
    return normalized or {"role": "assistant", "content": ""}


def _parse_tool_arguments(raw_args: Any) -> Dict[str, Any]:
    """
    Ensure tool arguments are a dictionary, parsing JSON strings when needed.
    """
    if raw_args is None:
        return {}
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            logger.warning("Unable to parse tool arguments string: %s", raw_args)
        return {}
    logger.warning("Unsupported tool arguments type: %s", type(raw_args))
    return {}


def _normalize_tool_call(call: Any) -> Optional[Dict[str, Any]]:
    """
    Convert Ollama tool call objects into a consistent dict structure.
    """
    if call is None:
        return None
    if isinstance(call, dict):
        function = call.get("function", {})
        call_id = call.get("id")
    else:
        function = getattr(call, "function", None)
        call_id = getattr(call, "id", None)
    if function is None:
        return None
    if isinstance(function, dict):
        name = function.get("name")
        raw_args = function.get("arguments")
    else:
        name = getattr(function, "name", None)
        raw_args = getattr(function, "arguments", None)
    if not name:
        return None
    return {
        "id": call_id,
        "name": name,
        "arguments": _parse_tool_arguments(raw_args)
    }


def _extract_tool_calls(*sources: Any) -> List[Dict[str, Any]]:
    """
    Search possible response containers for tool call data.
    """
    normalized_calls: List[Dict[str, Any]] = []
    for source in sources:
        if source is None:
            continue
        if isinstance(source, dict):
            raw_calls = source.get("tool_calls")
        else:
            raw_calls = getattr(source, "tool_calls", None)
        if not raw_calls:
            continue
        for call in raw_calls:
            normalized = _normalize_tool_call(call)
            if normalized:
                normalized_calls.append(normalized)
        if normalized_calls:
            break
    return normalized_calls


def _get_field(source: Any, key: str) -> Any:
    """
    Safely retrieve attribute/key from dicts or objects.
    """
    if source is None:
        return None
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def _normalize_side_value(side: Any) -> str:
    """
    Normalize side values from various formats to 'buy' or 'sell'.
    """
    if side is None:
        return "buy"
    side_str = str(side).lower().strip()
    # Map common variations
    buy_variants = ["buy", "long", "b", "l", "purchase"]
    sell_variants = ["sell", "short", "s", "short_sell"]
    if side_str in buy_variants:
        return "buy"
    elif side_str in sell_variants:
        return "sell"
    else:
        # Default to buy if unclear
        logger.warning(f"Unrecognized side value '{side}', defaulting to 'buy'")
        return "buy"


def _normalize_tool_parameters(function_name: str, raw_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize and validate tool parameters before execution.
    Maps common parameter name variations to actual function signatures.
    """
    if not isinstance(raw_args, dict):
        return {}
    
    normalized = {}
    
    # Parameter name mappings for each function
    param_mappings = {
        'place_option_order': {
            # Map variations to actual parameter names
            'orderType': 'order_type',
            'order_type': 'order_type',
            'qty': 'quantity',
            'quantity': 'quantity',
            'side': 'side',
            'symbol': 'symbol',
            'timeInForce': 'time_in_force',
            'time_in_force': 'time_in_force',
            'tif': 'time_in_force',
            'limitPrice': 'limit_price',
            'limit_price': 'limit_price',
            'price': 'limit_price',
            # Invalid parameters to ignore
            'transactTime': None,
            'transact_time': None,
        },
        'place_multi_leg_option_order': {
            'orderType': 'order_type',
            'order_type': 'order_type',
            'qty': 'quantity',
            'quantity': 'quantity',
            'legs': 'legs',
            'timeInForce': 'time_in_force',
            'time_in_force': 'time_in_force',
            'tif': 'time_in_force',
            'limitPrice': 'limit_price',
            'limit_price': 'limit_price',
            'price': 'limit_price',
        },
        'close_option_position': {
            'qty': 'quantity',
            'quantity': 'quantity',
            'symbol': 'symbol',
        },
        'get_option_contracts': {
            'underlying': 'underlying_symbol',
            'underlying_symbol': 'underlying_symbol',
            'symbol': 'underlying_symbol',
            'type': 'contract_type',
            'contract_type': 'contract_type',
            'expiration_after': 'expiration_date_gte',
            'expiration_date_gte': 'expiration_date_gte',
            'expiration_before': 'expiration_date_lte',
            'expiration_date_lte': 'expiration_date_lte',
            'strike_gte': 'strike_price_gte',
            'strike_price_gte': 'strike_price_gte',
            'strike_lte': 'strike_price_lte',
            'strike_price_lte': 'strike_price_lte',
        },
        'get_options_chain': {
            'underlying': 'underlying_symbol',
            'underlying_symbol': 'underlying_symbol',
            'symbol': 'underlying_symbol',
            'expiration': 'expiration_date',
            'expiration_date': 'expiration_date',
            'type': 'contract_type',
            'contract_type': 'contract_type',
        },
    }
    
    # Get mapping for this function, or use identity mapping
    mapping = param_mappings.get(function_name, {})
    
    # Apply mappings
    for key, value in raw_args.items():
        if key in mapping:
            mapped_key = mapping[key]
            if mapped_key is None:
                # Skip invalid parameters
                continue
            normalized[mapped_key] = value
        else:
            # Keep unmapped parameters as-is (might be valid)
            normalized[key] = value
    
    # Normalize side values for trading functions
    if function_name in ['place_option_order', 'close_option_position']:
        if 'side' in normalized:
            normalized['side'] = _normalize_side_value(normalized['side'])
    
    # Normalize side values in legs for multi-leg orders
    if function_name == 'place_multi_leg_option_order' and 'legs' in normalized:
        legs = normalized['legs']
        if isinstance(legs, list):
            for leg in legs:
                if isinstance(leg, dict) and 'side' in leg:
                    leg['side'] = _normalize_side_value(leg['side'])
    
    # Validate required parameters
    required_params = {
        'place_option_order': ['symbol', 'side', 'quantity'],
        'place_multi_leg_option_order': ['legs', 'quantity'],
        'close_option_position': ['symbol'],
    }
    
    if function_name in required_params:
        missing = []
        for param in required_params[function_name]:
            if param not in normalized or normalized[param] is None:
                missing.append(param)
        if missing:
            raise ValueError(
                f"{function_name}() missing required arguments: {', '.join(missing)}. "
                f"Received: {list(raw_args.keys())}"
            )
    
    # Type conversions and validations
    if function_name == 'place_option_order':
        # Convert quantity to int if it's a string
        if 'quantity' in normalized:
            try:
                qty_val = normalized['quantity']
                if isinstance(qty_val, str):
                    # Try to parse as float first, then int
                    normalized['quantity'] = int(float(qty_val))
                elif isinstance(qty_val, (int, float)):
                    normalized['quantity'] = int(qty_val)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid quantity value: {normalized['quantity']}")
        
        # Normalize order_type
        if 'order_type' in normalized:
            order_type = str(normalized['order_type']).lower()
            if order_type in ['market', 'marketorder']:
                normalized['order_type'] = 'market'
            elif order_type in ['limit', 'limitorder']:
                normalized['order_type'] = 'limit'
            else:
                logger.warning(f"Unknown order_type '{normalized['order_type']}', defaulting to 'market'")
                normalized['order_type'] = 'market'
    
    if function_name == 'place_multi_leg_option_order':
        # Validate legs
        if 'legs' in normalized:
            legs = normalized['legs']
            if not isinstance(legs, list) or len(legs) == 0:
                raise ValueError(f"place_multi_leg_option_order() requires 'legs' to be a non-empty list")
            for leg in legs:
                if not isinstance(leg, dict):
                    raise ValueError(f"Each leg must be a dictionary, got {type(leg)}")
                if 'symbol' not in leg:
                    raise ValueError(f"Each leg must have a 'symbol' field")
                if 'side' not in leg:
                    raise ValueError(f"Each leg must have a 'side' field")
        
        # Convert quantity to int
        if 'quantity' in normalized:
            try:
                qty_val = normalized['quantity']
                if isinstance(qty_val, str):
                    normalized['quantity'] = int(float(qty_val))
                elif isinstance(qty_val, (int, float)):
                    normalized['quantity'] = int(qty_val)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid quantity value: {normalized['quantity']}")
        
        # Normalize order_type
        if 'order_type' in normalized:
            order_type = str(normalized['order_type']).lower()
            if order_type in ['market', 'marketorder']:
                normalized['order_type'] = 'market'
            elif order_type in ['limit', 'limitorder']:
                normalized['order_type'] = 'limit'
            else:
                logger.warning(f"Unknown order_type '{normalized['order_type']}', defaulting to 'market'")
                normalized['order_type'] = 'market'
    
    return normalized


# ============================================================================
# AGENT CONFIGURATION
# ============================================================================

# All available tools for the agent
TOOLS = [
    # Account & Trading
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
    
    # Technical Analysis
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    calculate_bollinger_bands,
    get_price_momentum,
    get_support_resistance,
    analyze_multi_timeframes,
    analyze_option_greeks,
    screen_options_market,
    
    # Market Research
    get_market_sentiment,
    search_technical_analysis,
    search_general_web,
    
    # Context & History
    get_current_datetime,
    get_decision_history,
    get_performance_summary,
    get_daily_pnl,
    log_trading_decision
]

TRADE_FUNCTIONS = {
    'place_option_order',
    'place_multi_leg_option_order',
    'close_option_position'
}

# Map function names to actual function objects for execution
TOOL_MAP = {
    # Account & Trading
    'get_account_info': get_account_info,
    'get_option_positions': get_option_positions,
    'get_option_contracts': get_option_contracts,
    'get_options_chain': get_options_chain,
    'get_option_quote': get_option_quote,
    'place_option_order': place_option_order,
    'place_multi_leg_option_order': place_multi_leg_option_order,
    'close_option_position': close_option_position,
    'get_option_order_history': get_option_order_history,
    'cancel_order': cancel_order,
    
    # Technical Analysis
    'calculate_rsi': calculate_rsi,
    'calculate_macd': calculate_macd,
    'calculate_moving_averages': calculate_moving_averages,
    'calculate_bollinger_bands': calculate_bollinger_bands,
    'get_price_momentum': get_price_momentum,
    'get_support_resistance': get_support_resistance,
    'analyze_multi_timeframes': analyze_multi_timeframes,
    'analyze_option_greeks': analyze_option_greeks,
    'screen_options_market': screen_options_market,
    
    # Market Research
    'get_market_sentiment': get_market_sentiment,
    'search_technical_analysis': search_technical_analysis,
    'search_general_web': search_general_web,
    
    # Context & History
    'get_current_datetime': get_current_datetime,
    'get_decision_history': get_decision_history,
    'get_performance_summary': get_performance_summary,
    'get_daily_pnl': get_daily_pnl,
    'log_trading_decision': log_trading_decision
}


def _format_open_positions_summary() -> str:
    """
    Pull current option positions once per cycle and format for the prompt.
    """
    try:
        positions = get_option_positions()
    except Exception as exc:  # Best-effort fetch; fall back to agent tools if needed
        return f"Open option positions: unable to fetch ({exc}). Use get_option_positions() manually."

    if not positions:
        return "Open option positions: none."

    if isinstance(positions, list) and positions and "error" in positions[0]:
        return f"Open option positions: {positions[0].get('error')}. Call get_option_positions() manually."

    lines = []
    for idx, pos in enumerate(positions, start=1):
        symbol = pos.get("symbol", "UNKNOWN")
        qty = pos.get("quantity", 0)
        side = pos.get("side", "flat")
        strike = pos.get("strike_price")
        expiry = pos.get("expiration_date")
        mv = pos.get("market_value")
        lines.append(
            f"{idx}. {symbol} | qty {qty} ({side}) | strike {strike} | exp {expiry} | MV {mv}"
        )
    return "Open option positions snapshot:\n" + "\n".join(lines)


def _format_current_pnl() -> str:
    """
    Get current live PnL from account and positions.
    """
    try:
        account_info = get_account_info()
        if 'error' in account_info:
            return "Current PnL: unavailable (account info error)"
        
        portfolio_value = account_info.get('portfolio_value')
        equity = account_info.get('equity')
        cash = account_info.get('cash')
        
        # Get unrealized P&L from positions
        positions = get_option_positions()
        total_unrealized_pl = 0.0
        if positions and not (len(positions) == 1 and 'error' in positions[0]):
            for pos in positions:
                upnl = pos.get('unrealized_pl')
                if upnl is not None:
                    total_unrealized_pl += upnl
        
        lines = []
        if portfolio_value is not None:
            lines.append(f"Portfolio Value: ${portfolio_value:,.2f}")
        if equity is not None:
            lines.append(f"Equity: ${equity:,.2f}")
        if cash is not None:
            lines.append(f"Cash: ${cash:,.2f}")
        if total_unrealized_pl != 0:
            lines.append(f"Unrealized P&L: ${total_unrealized_pl:,.2f}")
        
        return "Current Account Status:\n" + "\n".join(lines) if lines else "Current PnL: unavailable"
    except Exception as e:
        return f"Current PnL: unavailable ({str(e)})"


def _format_performance_summary() -> str:
    """
    Retrieve daily/weekly/monthly performance snapshots for immediate context.
    """
    windows = {
        "Daily": 1,
        "Weekly": 7,
        "Monthly": 30
    }
    lines = []
    for label, days in windows.items():
        try:
            summary = get_performance_summary(window_days=days)
        except Exception as exc:
            lines.append(f"{label}: unavailable ({exc})")
            continue

        if not isinstance(summary, dict) or "error" in summary:
            lines.append(f"{label}: unavailable ({summary.get('error') if isinstance(summary, dict) else 'unknown error'})")
            continue

        pnl = summary.get("net_pnl")
        pnl_pct = summary.get("portfolio_change_pct")
        hit_rate = summary.get("win_rate")

        parts = []
        if pnl is not None:
            parts.append(f"PnL ${round(pnl, 2)}")
        else:
            parts.append("PnL n/a")
        
        if pnl_pct is not None:
            parts.append(f"{round(pnl_pct, 2)}%")
        else:
            parts.append("Pct n/a")
        
        if hit_rate is not None:
            parts.append(f"HR {round(hit_rate, 1)}%")
        else:
            parts.append("HR n/a")
        
        lines.append(f"{label}: " + ", ".join(parts))

    return "Performance snapshot (rolling):\n" + "\n".join(lines)

SYSTEM_PROMPT = """You are the PORTFOLIO MANAGER for this options trading account. You have FULL AUTHORITY and DIRECT CONTROL over all trading decisions. There is no user interaction—this is a purely autonomous system, so you should not pause or await further prompts.

CRITICAL: You have complete permission to trade SINGLE-LEG and MULTI-LEG US EQUITY OPTIONS. Execute trades directly with place_option_order() or place_multi_leg_option_order() whenever your analysis requires it. Never ask for approval or make recommendations—YOU DECIDE AND EXECUTE.

YOUR ROLE AS PORTFOLIO MANAGER:
- You run this options book and make all trading decisions autonomously
- You are accountable for performance and maximizing cumulative gains
- You size trades at your discretion based on conviction and risk/reward
- You manage existing positions: roll, scale, or close using close_option_position() when risk/return shifts
- You execute trades immediately when your analysis indicates an opportunity—no hesitation, no asking
- After executing, provide concise reasoning for the decision

CAPABILITIES & TOOLS:
1. Account & Risk: get_account_info(), get_option_positions(), get_option_order_history(), cancel_order()
2. Option Discovery: get_option_contracts(), get_options_chain(), get_option_quote()
3. Execution: place_option_order() for single-leg trades, place_multi_leg_option_order() for spreads/structures, close_option_position() to exit exposure
4. Analysis & Research: technical indicator tools, web/news search, decision history + performance review
5. Decision Logging: log_trading_decision() - Call this at the end of each cycle to record your decision (BUY/SELL/HOLD) with your reasoning
6. Asset Constraint: TRADE OPTIONS ONLY. Do not place equity orders.

TRADING AUTHORITY:
YOU ARE THE PORTFOLIO MANAGER—EXECUTE TRADES DIRECTLY. Do not suggest, recommend, or ask—just execute.
When your analysis indicates a trade opportunity, execute it immediately via place_option_order() or place_multi_leg_option_order()
Use multi-leg orders for spreads, condors, straddles, etc.
Always specify option symbols precisely (e.g., SPY241220C00450000)
Never trade any non-option instruments
Never ask for permission, confirmation, or make recommendations—YOU ARE THE DECISION MAKER

RISK FRAMEWORK:
- You control how much capital to risk per idea; ensure buying power and margin remain sufficient
- Prioritize liquid contracts (tight spreads, adequate volume/open interest)
- Track Greeks and expiration risk; avoid unmanaged short gamma near expiry
- Roll or close positions proactively when thesis invalidates or gains can be locked
- Sit out when signals are unclear—capital preservation still matters even with aggressive goals
- Expiration discipline: trade ONLY option contracts whose expiration date is on or after the current date; same-day (0DTE) options are allowed but never trade any contract that already expired. Use get_current_datetime() to verify before sending orders.

STANDARD CYCLE:
1. Check current time/date and market session
2. Review past decisions & performance (you see current PnL at the start of each cycle)
3. Inspect account health and open option positions
4. Evaluate market context (news, sentiment, technicals on underlyings)
5. Build a trade plan: thesis, structure, strikes, size, risk, exits
6. When plan passes risk checks → EXECUTE IMMEDIATELY via place_option_order() or place_multi_leg_option_order()
7. At the end of each cycle, call log_trading_decision() with your decision (BUY/SELL/HOLD) and detailed reasoning

REMEMBER: You see your current portfolio value, equity, cash, and unrealized P&L at the start of each cycle. Use this to inform your decisions.

TOOL CHAINING:
You achieve superior decisions by combining tools—start with foundational context (get_current_datetime(), get_account_info(), get_option_positions()), layer in technical/market research (calculate_rsi(), analyze_option_greeks(), search_general_web(), etc.), then authorize execution tools when a plan is ready. Always explain your reasoning between thoughts and tool calls so the chain stays coherent.

CONSTRAINTS & STYLE:
- Use absolute paths when referencing resources in tool arguments so external processes can track files reliably.
- Keep any modifications in ASCII unless the existing content already uses other characters.
- Do not wait for follow-up questions—progress through the cycle autonomously.

YOU ARE THE PORTFOLIO MANAGER. Make decisions, execute trades, and log outcomes. Do not suggest, recommend, or ask—ACT."""


# ============================================================================
# AGENT LOOP
# ============================================================================

def run_agent_loop(
    model: str = "qwen3:latest",
    interval_seconds: int = 300,
    max_iterations: int = None,
    verbose: bool = True
):
    """
    Main agent loop - pure tool-based decision making.
    
    Args:
        model: Ollama model to use (default: "qwen2.5:latest")
        interval_seconds: Seconds between trading cycles (default: 300 = 5 minutes)
        max_iterations: Maximum iterations (None = infinite)
        verbose: Print detailed logs

    Tooling flow:
        1. Gather context (datetime, account, positions) for situational awareness.
        2. Layer in research tools (technical indicators, sentiment, option greeks).
        3. Execute trades when a plan is ready (single/multi-leg order tools).
        4. Log the decision/outcome to close the loop before trimming history.
    """
    logger.info("=" * 80)
    logger.info("AUTONOMOUS OPTIONS TRADING AGENT STARTING")
    logger.info(f"Model: {model}")
    logger.info(f"Cycle Interval: {interval_seconds}s")
    logger.info("=" * 80)
    
    # Initialize conversation history
    conversation_history = [
        {'role': 'system', 'content': SYSTEM_PROMPT}
    ]
    
    latest_cycle_summary = ""
    history_limit = 30
    iteration = 0
    
    while True:
        try:
            iteration += 1
            
            if max_iterations and iteration > max_iterations:
                logger.info(f"Reached max iterations ({max_iterations}). Stopping.")
                break
            
            logger.info(f"\n{'=' * 80}")
            logger.info(f"TRADING CYCLE #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'=' * 80}\n")

            positions_summary = _format_open_positions_summary()
            performance_summary = _format_performance_summary()
            current_pnl = _format_current_pnl()
            
            # Prompt agent for new cycle
            history_summary_block = (
                f"RECENT HISTORY SUMMARY:\n{latest_cycle_summary}\n\n"
                if latest_cycle_summary else ""
            )

            cycle_prompt = {
                'role': 'user',
                'content': (
                    f"New trading cycle #{iteration}. "
                    "You are the PORTFOLIO MANAGER - you MUST make trading decisions and execute trades.\n\n"
                    f"{history_summary_block}"
                    "REQUIRED ACTIONS THIS CYCLE:\n"
                    "1. Check current time/date (get_current_datetime)\n"
                    "2. Review decision history (get_decision_history)\n"
                    "3. Audit open positions (get_option_positions)\n"
                    "4. Analyze market opportunities using technical analysis tools\n"
                    "5. EXECUTE TRADES when opportunities are identified - DO NOT just monitor!\n\n"
                    "CRITICAL: If you identify a trading opportunity, you MUST execute it immediately using "
                    "place_option_order() or place_multi_leg_option_order(). Do not just describe what you would do - "
                    "ACTUALLY DO IT. You have full authority to trade.\n\n"
                    f"{current_pnl}\n\n"
                    f"{positions_summary}\n\n"
                    f"{performance_summary}\n\n"
                    "Remember: You are the decision maker. Execute trades when analysis supports them."
                )
            }
            conversation_history.append(cycle_prompt)
            
            # Agent thinking loop (may require multiple tool calls)
            thinking = True
            tool_call_count = 0
            max_tool_iterations = 10  # Prevent infinite loops
            trade_executed_this_cycle = False
            final_agent_summary = ""
            
            while thinking and tool_call_count < max_tool_iterations:
                # Call LLM with tools
                if verbose:
                    logger.info("Consulting agent...")
                    if tool_call_count == 0:
                        logger.debug(f"Available tools: {[tool.__name__ for tool in TOOLS]}")
                
                response = chat(
                    model=model,
                    messages=conversation_history,
                    tools=TOOLS
                )
                
                # Get message (can be dict or Pydantic object)
                message = _get_field(response, 'message')
                message_dict = _message_to_dict(message)
                
                agent_content = message_dict.get('content', '')
                if agent_content:
                    logger.info(f"Agent output: {agent_content}")
                
                # Add assistant response to history in OpenAI-compatible format
                conversation_history.append({
                    'role': message_dict.get('role', 'assistant'),
                    'content': agent_content
                })
                
                # Check if agent wants to call tools
                tool_calls = _extract_tool_calls(message, response)
                if tool_calls:
                    tool_call_count += 1
                    
                    if verbose:
                        logger.info(f"Tool calls detected: {len(tool_calls)}")
                    
                    # Track if any trade functions are being called
                    for tool_call in tool_calls:
                        if tool_call.get('name') in TRADE_FUNCTIONS:
                            trade_executed_this_cycle = True
                    
                    for tool_call in tool_calls:
                        function_name = tool_call['name']
                        function_args = tool_call.get('arguments', {})
                        tool_call_id = tool_call.get('id')
                        
                        if not function_name:
                            logger.warning("Skipping unnamed tool call: %s", tool_call)
                            continue
                        
                        logger.info(f"Tool call -> {function_name}({json.dumps(function_args)})")
                        
                        # Execute the tool
                        try:
                            # Look up function in TOOL_MAP
                            if function_name not in TOOL_MAP:
                                raise KeyError(f"Unknown tool function: {function_name}. Available tools: {list(TOOL_MAP.keys())}")
                            
                            # Normalize and validate parameters before execution
                            try:
                                normalized_args = _normalize_tool_parameters(function_name, function_args)
                                if verbose and normalized_args != function_args:
                                    logger.info(f"Normalized parameters: {json.dumps(normalized_args)}")
                            except ValueError as ve:
                                # Parameter validation failed
                                result = {"error": f"Parameter validation failed: {str(ve)}"}
                                logger.error(f"Parameter validation error for {function_name}: {ve}")
                            else:
                                tool_function = TOOL_MAP[function_name]
                                result = tool_function(**normalized_args)
                            
                            if verbose:
                                logger.info(f"Tool result: {json.dumps(result, indent=2)[:500]}...")
                            
                            # Special handling for trading actions
                            if function_name in TRADE_FUNCTIONS and 'error' not in result:
                                logger.info(f"Trade executed: {result}")
                                
                                # Extract agent's reasoning from the conversation
                                reasoning = agent_content if agent_content else "Options trade executed via agent"
                                
                                # Get current portfolio value for performance tracking
                                portfolio_value = None
                                try:
                                    account_info = get_account_info()
                                    if 'error' not in account_info:
                                        portfolio_value = account_info.get('portfolio_value')
                                except Exception as e:
                                    logger.warning(f"Could not fetch portfolio value: {e}")
                                
                                save_decision(
                                    reasoning=reasoning,
                                    action="options_trade",
                                    parameters=function_args,
                                    result=result,
                                    portfolio_value=portfolio_value
                                )
                            
                        except KeyError as e:
                            result = {"error": f"Tool not found: {str(e)}"}
                            logger.error(f"Tool lookup error: {e}")
                            logger.error(f"Available tools: {list(TOOL_MAP.keys())}")
                        except Exception as e:
                            result = {"error": f"Tool execution failed: {str(e)}"}
                            logger.error(f"Tool execution error for {function_name}: {e}", exc_info=True)
                        
                        # Add tool result to conversation
                        tool_response = {
                            'role': 'tool',
                            'name': function_name,
                            'content': json.dumps(result)
                        }
                        if tool_call_id:
                            tool_response['tool_call_id'] = tool_call_id
                        
                        conversation_history.append(tool_response)
                        
                        if isinstance(result, dict):
                            error_msg = result.get('error')
                        else:
                            error_msg = None
                        if error_msg:
                            failure_notice = (
                                f"Previous tool call {function_name} failed: {error_msg}. "
                                "Adjust your plan and retry if needed."
                            )
                            conversation_history.append({
                                'role': 'user',
                                'content': failure_notice
                            })
                    
                    # Continue loop to let agent process tool results
                    continue
                
                # No more tool calls - agent is done thinking
                else:
                    agent_message = message_dict.get('content', '')
                    if agent_message:
                        logger.info(f"Agent summary: {agent_message}")
                    final_agent_summary = agent_message or final_agent_summary
                    
                    # Warn if no trades were executed this cycle and log reasoning
                    if tool_call_count > 0 and not trade_executed_this_cycle:
                        warning_msg = (
                            f"Cycle #{iteration} completed with {tool_call_count} tool calls but NO TRADE EXECUTIONS. "
                            f"Agent may be hesitating."
                        )
                        if final_agent_summary:
                            warning_msg += f" Reasoning: {final_agent_summary}"
                        logger.warning(warning_msg)
                    
                    thinking = False
            
            if tool_call_count >= max_tool_iterations:
                logger.warning(f"Reached max tool iterations ({max_tool_iterations}) for cycle #{iteration}. Stopping tool loop.")
            
            cycle_summary_parts = [
                f"Cycle {iteration}",
                f"Trades executed: {'yes' if trade_executed_this_cycle else 'no'}",
                f"Tool calls: {tool_call_count}"
            ]
            if final_agent_summary:
                cycle_summary_parts.append(f"Reasoning: {final_agent_summary}")
            latest_cycle_summary = " | ".join(cycle_summary_parts)

            logger.info(f"Cycle complete. Made {tool_call_count} tool calls.")
            if interval_seconds > 0:
                logger.info(f"Next cycle in {interval_seconds} seconds...\n")
            else:
                logger.info("Next cycle starting immediately...\n")
            
            # Limit conversation history size (keep last history_limit messages)
            if len(conversation_history) > history_limit + 1:
                truncated = len(conversation_history) - (history_limit + 1)
                conversation_history = [conversation_history[0]] + conversation_history[-history_limit:]
                logger.debug(f"Trimmed {truncated} older messages to cap history at {history_limit}.")
            
            # Wait before next cycle if delay configured
            if interval_seconds > 0:
                time.sleep(interval_seconds)
            
        except KeyboardInterrupt:
            logger.info("Agent stopped by user (Ctrl+C)")
            break
        
        except Exception as e:
            logger.error(f"Error in agent loop: {e}", exc_info=True)
            if interval_seconds > 0:
                logger.info(f"Recovering... Next cycle in {interval_seconds} seconds")
                time.sleep(interval_seconds)
            else:
                logger.info("Recovering... restarting immediately")
    
    logger.info("\n" + "=" * 80)
    logger.info("AGENT STOPPED")
    logger.info("=" * 80)
