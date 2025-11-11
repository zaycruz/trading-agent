"""
Web Search Tools using Tavily for Market Research
All functions designed to be called by LLM via Ollama tool calling.
"""

import os
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    print("Warning: tavily-python not installed. Run: uv add tavily-python")


# Initialize Tavily client globally
_tavily_client = None

def _get_tavily_client():
    """Lazy initialization of Tavily client"""
    global _tavily_client
    if not TAVILY_AVAILABLE:
        return None
    if _tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY", "")
        if not api_key:
            print("Warning: TAVILY_API_KEY not set in environment")
            return None
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


# ============================================================================
# TOOL FUNCTIONS - Called by LLM via Ollama
# ============================================================================

def search_crypto_news(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search for crypto market news and analysis using Tavily.
    Returns recent news articles, analysis, and market commentary.
    
    Args:
        query: Search query (e.g., "Bitcoin market news today", "Ethereum price analysis")
        max_results: Number of results to return (default: 5)
    
    Returns list of news articles with title, content, URL, and published date.
    """
    try:
        client = _get_tavily_client()
        if client is None:
            return [{"error": "Tavily client not available. Check API key or installation."}]
        
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_domains=["coindesk.com", "cointelegraph.com", "decrypt.co", "theblockcrypto.com"]
        )
        
        results = []
        for item in response.get('results', []):
            results.append({
                "title": item.get('title', ''),
                "content": item.get('content', ''),
                "url": item.get('url', ''),
                "score": item.get('score', 0),
                "published_date": item.get('published_date', 'unknown')
            })
        
        return results
    except Exception as e:
        return [{"error": f"Failed to search news: {str(e)}"}]


def get_market_sentiment(symbol: str) -> Dict:
    """
    Get current market sentiment for a crypto asset.
    Searches for recent sentiment analysis and market opinion.
    
    Args:
        symbol: Crypto symbol (e.g., "BTC", "ETH", "Bitcoin", "Ethereum")
    
    Returns sentiment summary with bullish/bearish indicators from recent analysis.
    """
    try:
        client = _get_tavily_client()
        if client is None:
            return {"error": "Tavily client not available. Check API key or installation."}
        
        query = f"{symbol} crypto market sentiment analysis latest"
        response = client.search(
            query=query,
            max_results=3,
            search_depth="advanced"
        )
        
        results = []
        for item in response.get('results', []):
            results.append({
                "source": item.get('title', ''),
                "content": item.get('content', ''),
                "url": item.get('url', '')
            })
        
        return {
            "symbol": symbol,
            "query": query,
            "sentiment_sources": results,
            "note": "Analyze the content to determine bullish/bearish sentiment"
        }
    except Exception as e:
        return {"error": f"Failed to get sentiment: {str(e)}"}


def search_technical_analysis(symbol: str) -> List[Dict]:
    """
    Search for technical analysis and trading signals for a crypto asset.
    Returns recent TA discussions, chart patterns, and trading ideas.
    
    Args:
        symbol: Crypto symbol (e.g., "BTC", "ETH", "Bitcoin")
    
    Returns list of technical analysis articles and discussions.
    """
    try:
        client = _get_tavily_client()
        if client is None:
            return [{"error": "Tavily client not available. Check API key or installation."}]
        
        query = f"{symbol} technical analysis trading signals chart patterns"
        response = client.search(
            query=query,
            max_results=5,
            search_depth="advanced"
        )
        
        results = []
        for item in response.get('results', []):
            results.append({
                "title": item.get('title', ''),
                "content": item.get('content', ''),
                "url": item.get('url', ''),
                "relevance_score": item.get('score', 0)
            })
        
        return results
    except Exception as e:
        return [{"error": f"Failed to search technical analysis: {str(e)}"}]


def search_general_web(query: str, max_results: int = 5) -> List[Dict]:
    """
    General web search for any trading-related query.
    Use this for specific questions or research topics.
    
    Args:
        query: Any search query
        max_results: Number of results (default: 5)
    
    Returns list of search results with content and URLs.
    """
    try:
        client = _get_tavily_client()
        if client is None:
            return [{"error": "Tavily client not available. Check API key or installation."}]
        
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic"
        )
        
        results = []
        for item in response.get('results', []):
            results.append({
                "title": item.get('title', ''),
                "content": item.get('content', ''),
                "url": item.get('url', '')
            })
        
        return results
    except Exception as e:
        return [{"error": f"Failed to search: {str(e)}"}]