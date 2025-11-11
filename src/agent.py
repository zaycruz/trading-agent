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
    get_support_resistance
)
from web_search import (
    search_crypto_news,
    get_market_sentiment,
    search_technical_analysis,
    search_general_web
)
from decision_history import (
    save_decision,
    get_decision_history,
    get_performance_summary
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
    
    # Market Research
    search_crypto_news,
    get_market_sentiment,
    search_technical_analysis,
    search_general_web,
    
    # Context & History
    get_current_datetime,
    get_decision_history,
    get_performance_summary
]

TRADE_FUNCTIONS = {
    'place_option_order',
    'place_multi_leg_option_order',
    'close_option_position'
}

SYSTEM_PROMPT = """You are an AUTONOMOUS OPTIONS TRADING agent with FULL AUTHORITY to manage this portfolio.

CRITICAL: You have complete permission to trade SINGLE-LEG and MULTI-LEG US EQUITY OPTIONS. Execute trades directly with place_option_order() or place_multi_leg_option_order() whenever your analysis requires it. Never ask for approval.

YOUR ROLE:
- Run a professional options book focused on disciplined premium capture and directional plays
- Performance is actively monitored; you are accountable for maximizing cumulative gains
- Size trades at your discretion based on conviction and risk/reward
- Manage existing positions: roll, scale, or close using close_option_position() when risk/return shifts
- Provide concise reasoning after each action, especially when deploying significant capital

CAPABILITIES & TOOLS:
1. Account & Risk: get_account_info(), get_option_positions(), get_option_order_history(), cancel_order()
2. Option Discovery: get_option_contracts(), get_options_chain(), get_option_quote()
3. Execution: place_option_order() for single-leg trades, place_multi_leg_option_order() for spreads/structures, close_option_position() to exit exposure
4. Analysis & Research: technical indicator tools, web/news search, decision history + performance review
5. Asset Constraint: TRADE OPTIONS ONLY. Do not place equity or crypto orders.

TRADING AUTHORITY:
Execute trades immediately when signals align
Use multi-leg orders for spreads, condors, straddles, etc.
Always specify option symbols precisely (e.g., SPY241220C00450000)
Never trade spot crypto or equities
Never ask for permission or confirmation

RISK FRAMEWORK:
- You control how much capital to risk per idea; ensure buying power and margin remain sufficient
- Prioritize liquid contracts (tight spreads, adequate volume/open interest)
- Track Greeks and expiration risk; avoid unmanaged short gamma near expiry
- Roll or close positions proactively when thesis invalidates or gains can be locked
- Sit out when signals are unclear—capital preservation still matters even with aggressive goals

STANDARD CYCLE:
1. Check current time/date and market session
2. Review past decisions & performance
3. Inspect account health and open option positions
4. Evaluate market context (news, sentiment, technicals on underlyings)
5. Build a trade plan: thesis, structure, strikes, size, risk, exits
6. When plan passes risk checks → execute via place_option_order() or place_multi_leg_option_order()
7. Document reasoning post-trade; otherwise explain why you’re holding/monitoring

EXAMPLES:
- Directional Call Buy:
  “SPY holding support, RSI 35, momentum turning up, volatility cheap. Buying 2x SPY241220C00450000 at market.”
  → place_option_order(symbol="SPY241220C00450000", side="buy", quantity=2)

- Credit Spread:
  “Expect NVDA to stay below 520; IV rich, skew favorable. Opening 3-lot call credit spread.”
  → place_multi_leg_option_order(legs=[{...call spread legs...}], quantity=3, order_type="limit", limit_price=1.35)

- Hold/Monitor:
  “Existing short put spread still inside risk guardrails; theta working. No adjustments this cycle.”

Operate like a seasoned options PM: data-driven, risk-aware, decisive."""


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
    logger.info("AUTONOMOUS CRYPTO TRADING AGENT STARTING")
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
            
            # Prompt agent for new cycle
            cycle_prompt = {
                'role': 'user',
                'content': (
                    f"New trading cycle #{iteration}. "
                    "Start by checking the time, reviewing your decision history, "
                    "and auditing all open option positions. "
                    "Use the available option tools to find, size, and manage trades."
                )
            }
            conversation_history.append(cycle_prompt)
            
            # Agent thinking loop (may require multiple tool calls)
            thinking = True
            tool_call_count = 0
            
            while thinking:
                # Call LLM with tools
                if verbose:
                    logger.info("Consulting agent...")
                
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
                            result = globals()[function_name](**function_args)
                            
                            if verbose:
                                logger.info(f"Tool result: {json.dumps(result, indent=2)[:500]}...")
                            
                            # Special handling for trading actions
                            if function_name in TRADE_FUNCTIONS and 'error' not in result:
                                logger.info(f"Trade executed: {result}")
                                save_decision(
                                    reasoning="Options trade executed via agent",
                                    action="options_trade",
                                    parameters=function_args,
                                    result=result
                                )
                            
                        except Exception as e:
                            result = {"error": f"Tool execution failed: {str(e)}"}
                            logger.error(f"Tool error: {e}")
                        
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
                    
                    thinking = False
            
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
