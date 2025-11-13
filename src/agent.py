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
from alpaca_tools import (
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
    get_current_datetime
)
from analysis_tools import (
    calculate_rsi,
    calculate_macd,
    calculate_moving_averages,
    calculate_bollinger_bands,
    get_price_momentum,
    get_support_resistance,
    analyze_multi_timeframes,
    analyze_option_greeks,
    screen_options_market
)
from web_search import (
    get_market_sentiment,
    search_technical_analysis,
    search_general_web
)
from decision_history import (
    save_decision,
    get_decision_history,
    get_performance_summary,
    get_daily_pnl
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
    get_daily_pnl
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
    'get_daily_pnl': get_daily_pnl
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

SYSTEM_PROMPT = """You are the PORTFOLIO MANAGER for this options trading account. You have FULL AUTHORITY and DIRECT CONTROL over all trading decisions. You are NOT an advisor—you ARE the decision maker executing trades.

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
5. Asset Constraint: TRADE OPTIONS ONLY. Do not place equity orders.

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
- Expiration discipline: trade ONLY option contracts whose expiration date is strictly after the current date; never trade contracts expiring today or in the past. Use get_current_datetime() to verify before sending orders.

STANDARD CYCLE:
1. Check current time/date and market session
2. Review past decisions & performance (you see current PnL at the start of each cycle)
3. Inspect account health and open option positions
4. Evaluate market context (news, sentiment, technicals on underlyings)
5. Build a trade plan: thesis, structure, strikes, size, risk, exits
6. When plan passes risk checks → EXECUTE IMMEDIATELY via place_option_order() or place_multi_leg_option_order()
7. Document reasoning post-trade; otherwise explain why you're holding/monitoring

REMEMBER: You see your current portfolio value, equity, cash, and unrealized P&L at the start of each cycle. Use this to inform your decisions.

FEW-SHOT TOOL EXAMPLES (thought → tool → follow-up):
- Current Time (get_current_datetime):
  Thought: “Before evaluating expirations I need today’s date.” → Action: get_current_datetime() → Follow-up: “Now I know it’s 2024-06-18, so I’ll skip weeklies expiring today.”
- Account Snapshot (get_account_info):
  Thought: “Check buying power before sizing spreads.” → Action: get_account_info() → Follow-up: “Equity $125k, margin free $55k, so risking $6k fits.”
- Position Audit (get_option_positions):
  Thought: “Need live Greeks on open structures.” → Action: get_option_positions() → Follow-up: “SPY short put spread delta -0.20; keep monitoring.”
- Order History (get_option_order_history):
  Thought: “Confirm last fill price on NVDA call.” → Action: get_option_order_history(symbol="NVDA") → Follow-up: “Filled 2.35 debit; use that for P/L.”
- Cancel Stale Order (cancel_order):
  Thought: “Mid-price moved away, cancel resting limit.” → Action: cancel_order(order_id="ABC123") → Follow-up: “Order canceled, reassess entry.”
- Contract Discovery (get_option_contracts):
  Thought: “Find SPY calls expiring after earnings with 0.30 delta.” → Action: get_option_contracts(underlying="SPY", expiration_after="2024-07-01", min_delta=0.25, max_delta=0.35) → Follow-up: “SPY240719C00448000 fits, request quote.”
- Full Chain Scan (get_options_chain):
  Thought: “Need entire chain to compare skew.” → Action: get_options_chain(underlying="TSLA", expiration="2024-08-16") → Follow-up: “Calls rich vs puts; consider risk reversal.”
- Single Quote (get_option_quote):
  Thought: “Verify bid/ask on candidate contract.” → Action: get_option_quote(symbol="QQQ240816P00365000") → Follow-up: “Spread $0.08 wide, liquidity acceptable.”
- Single-Leg Execution (place_option_order):
  Thought: “Buy 3 delta-hedged calls immediately.” → Action: place_option_order(symbol="SPY240920C00455000", side="buy", quantity=3, order_type="market") → Follow-up: “Confirm fill then log rationale.”
- Multi-Leg Execution (place_multi_leg_option_order):
  Thought: “Deploy iron condor risk-defined.” → Action: place_multi_leg_option_order(legs=[{leg spec...}], quantity=2, order_type="limit", limit_price=1.05) → Follow-up: “If unfilled after 2 min, adjust credit.”
- Exit Position (close_option_position):
  Thought: “Theta captured 70%, close short put spread.” → Action: close_option_position(symbol="AAPL240621P00180000", quantity=2) → Follow-up: “Position flat; update decision log.”
- RSI Check (calculate_rsi):
  Thought: “Confirm oversold reading before selling puts.” → Action: calculate_rsi(symbol="IWM", period=14, timeframe="4h") → Follow-up: “RSI 32 trending up; green light.”
- MACD Momentum (calculate_macd):
  Thought: “Need momentum confirmation on breakout candidate.” → Action: calculate_macd(symbol="AMD", fast=12, slow=26, signal=9, timeframe="1h") → Follow-up: “MACD cross positive; consider call debit spread.”
- Moving Averages (calculate_moving_averages):
  Thought: “Trend context for SPX.” → Action: calculate_moving_averages(symbol="SPX", windows=[21, 55, 200], timeframe="1d") → Follow-up: “Price above 21/55 but below 200; medium-term caution.”
- Volatility Bands (calculate_bollinger_bands):
  Thought: “Check if price tagging upper band before fading rally.” → Action: calculate_bollinger_bands(symbol="NFLX", period=20, std_dev=2, timeframe="1h") → Follow-up: “Upper band hit twice; structure credit call spread.”
- Momentum Burst (get_price_momentum):
  Thought: “Measure 7-day momentum vs peers.” → Action: get_price_momentum(symbol="SMH", lookback_days=7) → Follow-up: “Momentum rank 85th percentile; momentum play valid.”
- Key Levels (get_support_resistance):
  Thought: “Need levels for stop placement.” → Action: get_support_resistance(symbol="MSFT", timeframe="4h") → Follow-up: “Support 405, resistance 422; align strikes.”
- Multi-Timeframe Stack (analyze_multi_timeframes):
  Thought: “Align 4h/1h trends before short gamma.” → Action: analyze_multi_timeframes(symbol="GOOGL", timeframes=["1d","4h","1h"]) → Follow-up: “All bullish; avoid new call credit spreads.”
- Greeks Rollup (analyze_option_greeks):
  Thought: “Need net delta/theta for near-term SPY contracts.” → Action: analyze_option_greeks(underlying="SPY", expiration_date="2024-08-16", limit=12) → Follow-up: “Average theta -0.09, delta skewed long; size spreads to stay near flat.”
- Options Screener (screen_options_market):
  Thought: “Filter liquid tickers under 30 DTE.” → Action: screen_options_market(underlyings=["SPY","QQQ","IWM"], min_open_interest=1000, max_days_to_expiration=30) → Follow-up: “Top candidates loaded; focus research on these strikes.”
- Sentiment Pulse (get_market_sentiment):
  Thought: “Gauge overall risk appetite.” → Action: get_market_sentiment() → Follow-up: “Greed index elevated; tighten upside risk.”
- Technical Research (search_technical_analysis):
  Thought: “Look for external takes on NVDA flag pattern.” → Action: search_technical_analysis(query="NVDA bull flag 2024") → Follow-up: “Consensus bullish; aligns with call fly idea.”
- Broad Web Search (search_general_web):
  Thought: “Need macro data release schedule.” → Action: search_general_web(query="economic calendar CPI release time") → Follow-up: “CPI tomorrow 8:30 ET; adjust exposure.”
- Decision Recall (get_decision_history):
  Thought: “Review last five trades before repeating mistakes.” → Action: get_decision_history(limit=5) → Follow-up: “Last theta plays clustered in tech; diversify.”
- Performance Summary (get_performance_summary):
  Thought: “Quantify hit rate before upping size.” → Action: get_performance_summary(window_days=30) → Follow-up: “Win rate 62%, avg pnl $420, maintain sizing.”
- Daily P/L Log (get_daily_pnl):
  Thought: “Check if today is green before adding risk.” → Action: get_daily_pnl(limit=7) → Follow-up: “Down $350 today, wait for better entries.”

EXAMPLES:
- Directional Call Buy:
  "SPY holding support, RSI 35, momentum turning up, volatility cheap. Executing: Buying 2x SPY241220C00450000 at market."
  → place_option_order(symbol="SPY241220C00450000", side="buy", quantity=2)

- Credit Spread:
  "Expect NVDA to stay below 520; IV rich, skew favorable. Executing: Opening 3-lot call credit spread."
  → place_multi_leg_option_order(legs=[{...call spread legs...}], quantity=3, order_type="limit", limit_price=1.35)

- Hold/Monitor:
  "Existing short put spread still inside risk guardrails; theta working. No adjustments this cycle—monitoring."

YOU ARE THE PORTFOLIO MANAGER. Make decisions and execute trades. Do not suggest or recommend—ACT."""


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
            cycle_prompt = {
                'role': 'user',
                'content': (
                    f"New trading cycle #{iteration}. "
                    "You are the PORTFOLIO MANAGER - you MUST make trading decisions and execute trades.\n\n"
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
                            
                            tool_function = TOOL_MAP[function_name]
                            result = tool_function(**function_args)
                            
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
                    
                    # Continue loop to let agent process tool results
                    continue
                
                # No more tool calls - agent is done thinking
                else:
                    agent_message = message_dict.get('content', '')
                    if agent_message:
                        logger.info(f"Agent summary: {agent_message}")
                    
                    # Warn if no trades were executed this cycle
                    if tool_call_count > 0 and not trade_executed_this_cycle:
                        logger.warning(f"Cycle #{iteration} completed with {tool_call_count} tool calls but NO TRADE EXECUTIONS. "
                                     f"Agent may be hesitating - check reasoning above.")
                    
                    thinking = False
            
            if tool_call_count >= max_tool_iterations:
                logger.warning(f"Reached max tool iterations ({max_tool_iterations}) for cycle #{iteration}. Stopping tool loop.")
            
            logger.info(f"Cycle complete. Made {tool_call_count} tool calls.")
            if interval_seconds > 0:
                logger.info(f"Next cycle in {interval_seconds} seconds...\n")
            else:
                logger.info("Next cycle starting immediately...\n")
            
            # Limit conversation history size (keep last 50 messages)
            if len(conversation_history) > 50:
                # Keep system prompt + recent messages
                conversation_history = [conversation_history[0]] + conversation_history[-49:]
            
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
