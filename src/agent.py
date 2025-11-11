"""
Autonomous Crypto Trading Agent
Pure tool-based approach - LLM makes ALL decisions via Ollama tool calling.
"""

import json
import time
import logging
from datetime import datetime
from typing import List, Dict

from ollama import chat

# Import all tool functions
from alpaca_tools import (
    get_account_info,
    get_positions,
    get_crypto_price,
    place_crypto_order,
    get_order_history,
    cancel_order,
    get_crypto_bars,
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


# ============================================================================
# AGENT CONFIGURATION
# ============================================================================

# All available tools for the agent
TOOLS = [
    # Account & Trading
    get_account_info,
    get_positions,
    get_crypto_price,
    place_crypto_order,
    get_order_history,
    cancel_order,
    get_crypto_bars,
    
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

SYSTEM_PROMPT = """You are an AUTONOMOUS crypto trading agent with FULL AUTHORITY to manage this portfolio.

⚡ CRITICAL: You have complete permission to execute trades. DO NOT ask for approval or confirmation.
When your analysis indicates a trade should be made, EXECUTE IT IMMEDIATELY using place_crypto_order().

YOUR ROLE:
- You are the portfolio manager with 100% trading authority
- You make all buy/sell decisions independently
- You execute trades directly without asking permission
- You manage the account to maximize profitable returns
- You are accountable for your trading performance

PERSONALITY & APPROACH:
- Analytical, cautious, and data-driven
- Learn from your past decisions and improve over time
- Explain your reasoning clearly AFTER executing trades
- Manage risk carefully and never over-leverage
- Act decisively when signals align

YOUR CAPABILITIES:
You have access to tools for:
1. Trading: Check account, view positions, get prices, PLACE ORDERS (use this!), review order history
2. Technical Analysis: RSI, MACD, moving averages, Bollinger Bands, momentum, support/resistance
3. Market Research: Search crypto news, analyze sentiment, read technical analysis
4. Self-Awareness: Check time, review your decision history, analyze your performance

TRADING AUTHORITY:
✅ You CAN and SHOULD execute trades when your analysis supports it
✅ You do NOT need to ask "would you like me to..." - just do it
✅ You are managing this account autonomously
✅ Place orders directly: place_crypto_order(symbol, side, quantity)
❌ Never ask for permission or approval to trade
❌ Never say "should I..." or "would you like me to..."

RISK MANAGEMENT RULES:
- Never risk more than 10% of portfolio value on a single trade
- Diversify across multiple assets when possible
- Use technical indicators to time entries/exits
- Always have a clear reason for each trade
- If signals are mixed or weak, it's okay to hold and wait
- Consider position sizing based on conviction level

DECISION PROCESS (each cycle):
1. Check current time/date
2. Review your recent decision history and learn from outcomes
3. Check your current portfolio and positions
4. If you have positions, evaluate if you should hold or take profits/cut losses
5. If considering a NEW trade:
   - Research market news and sentiment
   - Perform technical analysis (RSI, MACD, moving averages, etc.)
   - Check support/resistance levels
   - Analyze momentum and trend
   - Make decision based on confluence of signals
6. When your analysis supports a trade → EXECUTE IT IMMEDIATELY
   - Call place_crypto_order(symbol="BTC/USD", side="buy", quantity=0.1)
   - Explain your reasoning AFTER execution
7. If signals are unclear → hold and continue monitoring

TRADING EXAMPLES:

Example 1 - BUY Signal:
"RSI is 28 (oversold), MACD bullish crossover, positive news sentiment, price at support.
Multiple signals align. Executing BUY order for 0.1 BTC/USD now."
→ place_crypto_order(symbol="BTC/USD", side="buy", quantity=0.1)

Example 2 - SELL Signal:
"RSI is 72 (overbought), MACD bearish divergence, price at resistance, momentum slowing.
Technical indicators suggest taking profits. Executing SELL order for 0.05 BTC/USD now."
→ place_crypto_order(symbol="BTC/USD", side="sell", quantity=0.05)

Example 3 - HOLD:
"RSI at 55 (neutral), MACD showing indecision, mixed news. No clear signal.
I will hold current positions and reassess next cycle."
→ No trade executed

Remember: You are an AUTONOMOUS PORTFOLIO MANAGER. Trade with confidence when your analysis supports it.
"""


# ============================================================================
# AGENT LOOP
# ============================================================================

def run_agent_loop(
    model: str = "qwen2.5:latest",
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
                    "and checking your portfolio. Then decide what to do next."
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
                
                # Add assistant response to history
                conversation_history.append(response['message'])
                
                # Check if agent wants to call tools
                if response['message'].get('tool_calls'):
                    tool_call_count += 1
                    
                    for tool_call in response['message']['tool_calls']:
                        function_name = tool_call['function']['name']
                        function_args = tool_call['function']['arguments']
                        
                        logger.info(f"🔧 Tool Call: {function_name}({json.dumps(function_args)})")
                        
                        # Execute the tool
                        try:
                            result = globals()[function_name](**function_args)
                            
                            if verbose and function_name not in ['get_current_datetime', 'get_decision_history']:
                                logger.info(f"📊 Result: {json.dumps(result, indent=2)[:500]}...")
                            
                            # Special handling for trading actions
                            if function_name == 'place_crypto_order' and 'error' not in result:
                                logger.info(f"💰 TRADE EXECUTED: {result}")
                                # Save decision to history
                                save_decision(
                                    reasoning="Trade executed via agent",
                                    action="trade",
                                    parameters=function_args,
                                    result=result
                                )
                            
                        except Exception as e:
                            result = {"error": f"Tool execution failed: {str(e)}"}
                            logger.error(f"❌ Tool Error: {e}")
                        
                        # Add tool result to conversation
                        conversation_history.append({
                            'role': 'tool',
                            'content': json.dumps(result)
                        })
                    
                    # Continue loop to let agent process tool results
                    continue
                
                # No more tool calls - agent is done thinking
                else:
                    agent_message = response['message'].get('content', '')
                    if agent_message:
                        logger.info(f"\n💭 Agent: {agent_message}\n")
                    
                    thinking = False
            
            logger.info(f"Cycle complete. Made {tool_call_count} tool calls.")
            logger.info(f"Next cycle in {interval_seconds} seconds...\n")
            
            # Limit conversation history size (keep last 50 messages)
            if len(conversation_history) > 50:
                # Keep system prompt + recent messages
                conversation_history = [conversation_history[0]] + conversation_history[-49:]
            
            # Wait before next cycle
            time.sleep(interval_seconds)
            
        except KeyboardInterrupt:
            logger.info("\n⚠️  Agent stopped by user (Ctrl+C)")
            break
        
        except Exception as e:
            logger.error(f"❌ Error in agent loop: {e}", exc_info=True)
            logger.info(f"Recovering... Next cycle in {interval_seconds} seconds")
            time.sleep(interval_seconds)
    
    logger.info("\n" + "=" * 80)
    logger.info("AGENT STOPPED")
    logger.info("=" * 80)