"""
Trading Arena - Autonomous Crypto Trading Agent
Entry point for starting the agent.
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent import run_agent_loop


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Crypto Trading Agent using Qwen 3 via Ollama"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="qwen2.5:latest",
        help="Ollama model to use (default: qwen2.5:latest)"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Seconds between trading cycles (default: 300)"
    )
    
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum iterations to run (default: infinite)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce logging verbosity"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🤖 AUTONOMOUS CRYPTO TRADING AGENT")
    print("=" * 80)
    print(f"Model: {args.model}")
    print(f"Cycle Interval: {args.interval}s")
    print(f"Max Iterations: {args.max_iterations or 'Infinite'}")
    print("=" * 80)
    print("\n⚠️  WARNING: This agent will make real trades on Alpaca!")
    print("Make sure you're using paper trading for testing.\n")
    print("Press Ctrl+C to stop the agent at any time.\n")
    print("=" * 80)
    
    try:
        run_agent_loop(
            model=args.model,
            interval_seconds=args.interval,
            max_iterations=args.max_iterations,
            verbose=not args.quiet
        )
    except KeyboardInterrupt:
        print("\n\n✅ Agent stopped successfully")
    except Exception as e:
        print(f"\n\n❌ Agent crashed: {e}")
        raise


if __name__ == "__main__":
    main()
