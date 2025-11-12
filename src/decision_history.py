"""
Decision History Management
Tracks agent decisions, trades, and performance over time.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

# History file location
HISTORY_FILE = Path(__file__).parent.parent / "data" / "decision_history.json"


def _ensure_data_dir():
    """Ensure data directory exists"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_history() -> List[Dict]:
    """Load decision history from file"""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading history: {e}")
        return []


def _save_history(history: List[Dict]):
    """Save decision history to file"""
    _ensure_data_dir()
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")


# ============================================================================
# TOOL FUNCTIONS - Called by LLM and Agent
# ============================================================================

def save_decision(
    reasoning: str,
    action: str,
    parameters: Optional[Dict] = None,
    result: Optional[Dict] = None,
    portfolio_value: Optional[float] = None
) -> Dict:
    """
    Save a decision to history (called by agent loop, not directly by LLM).
    
    Args:
        reasoning: LLM's reasoning for the decision
        action: Action taken (buy, sell, hold, research, analyze)
        parameters: Parameters used (e.g., symbol, quantity)
        result: Result of the action
        portfolio_value: Portfolio value at time of decision
    
    Returns confirmation with decision_id and timestamp.
    """
    try:
        history = _load_history()
        
        decision = {
            "decision_id": len(history) + 1,
            "timestamp": datetime.now().isoformat(),
            "reasoning": reasoning,
            "action": action,
            "parameters": parameters or {},
            "result": result or {},
            "portfolio_value": portfolio_value
        }
        
        history.append(decision)
        _save_history(history)
        
        return {
            "success": True,
            "decision_id": decision["decision_id"],
            "timestamp": decision["timestamp"],
            "message": "Decision saved successfully"
        }
    except Exception as e:
        return {"error": f"Failed to save decision: {str(e)}"}


def get_decision_history(limit: int = 20) -> List[Dict]:
    """
    Get recent decision history for context awareness.
    LLM calls this to review past decisions and learn from them.
    
    Args:
        limit: Number of recent decisions to return (default: 20)
    
    Returns list of recent decisions with timestamps and outcomes.
    """
    try:
        history = _load_history()
        # Return most recent decisions
        return history[-limit:] if len(history) > limit else history
    except Exception as e:
        return [{"error": f"Failed to get history: {str(e)}"}]


def get_performance_summary() -> Dict:
    """
    Get summary of agent performance over time.
    Analyzes decision history to show win rate, total trades, etc.
    
    Returns performance metrics and statistics.
    """
    try:
        history = _load_history()
        
        if not history:
            return {
                "total_decisions": 0,
                "message": "No decision history yet"
            }
        
        # Count actions
        actions = {}
        trades = []
        
        for decision in history:
            action = decision.get('action', 'unknown')
            actions[action] = actions.get(action, 0) + 1
            
            if action in ['buy', 'sell']:
                trades.append(decision)
        
        # Get portfolio value progression
        portfolio_values = [
            d.get('portfolio_value') 
            for d in history 
            if d.get('portfolio_value') is not None
        ]
        
        performance = {
            "total_decisions": len(history),
            "total_trades": len(trades),
            "actions_breakdown": actions,
            "first_decision": history[0].get('timestamp'),
            "last_decision": history[-1].get('timestamp'),
        }
        
        if portfolio_values:
            performance["initial_portfolio_value"] = portfolio_values[0]
            performance["current_portfolio_value"] = portfolio_values[-1]
            performance["portfolio_change_pct"] = (
                ((portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0]) * 100
            )
        
        return performance
    except Exception as e:
        return {"error": f"Failed to get performance summary: {str(e)}"}


def get_daily_pnl(limit: int = 30) -> Dict:
    """
    Aggregate daily P/L using the portfolio_value captured in decisions.
    
    Args:
        limit: Number of most recent days to include (default: 30)
    
    Returns:
        {
            "days": [
                {
                    "date": "2024-10-01",
                    "start_value": 100000,
                    "end_value": 101200,
                    "pnl": 1200,
                    "pnl_percent": 1.2,
                    "decisions": 5
                },
                ...
            ]
        }
    """
    try:
        history = _load_history()
        if not history:
            return {"days": [], "message": "No history available"}

        daily_entries: Dict[str, Dict] = {}

        for decision in history:
            pv = decision.get("portfolio_value")
            ts = decision.get("timestamp")
            if pv is None or not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts)
            except ValueError:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue
            day = dt.date().isoformat()

            bucket = daily_entries.setdefault(
                day,
                {
                    "date": day,
                    "start_value": pv,
                    "end_value": pv,
                    "first_ts": dt,
                    "last_ts": dt,
                    "decisions": 0
                }
            )

            # Update start/end values based on timestamps
            if dt < bucket["first_ts"]:
                bucket["first_ts"] = dt
                bucket["start_value"] = pv
            if dt > bucket["last_ts"]:
                bucket["last_ts"] = dt
                bucket["end_value"] = pv

            bucket["decisions"] += 1

        if not daily_entries:
            return {"days": [], "message": "No portfolio values recorded"}

        sorted_days = sorted(daily_entries.values(), key=lambda x: x["date"], reverse=True)
        limited = sorted_days[:limit]

        for entry in limited:
            start = entry["start_value"]
            end = entry["end_value"]
            entry["pnl"] = round(end - start, 2)
            if start not in (None, 0):
                entry["pnl_percent"] = round(((end - start) / start) * 100, 2)
            else:
                entry["pnl_percent"] = None
            entry.pop("first_ts", None)
            entry.pop("last_ts", None)

        return {"days": limited}
    except Exception as e:
        return {"error": f"Failed to get daily P/L: {str(e)}"}


def clear_history() -> Dict:
    """
    Clear all decision history (use with caution).
    Returns confirmation.
    """
    try:
        _save_history([])
        return {
            "success": True,
            "message": "Decision history cleared"
        }
    except Exception as e:
        return {"error": f"Failed to clear history: {str(e)}"}
