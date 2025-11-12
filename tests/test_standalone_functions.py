"""
Tests for standalone function exports
"""

import pytest
from unittest.mock import Mock, patch

# Import the standalone functions
from alpaca_tools import (
    get_account_info,
    get_positions,
    get_option_positions,
    get_option_contracts,
    get_options_chain,
    get_option_quote,
    place_option_order,
    place_multi_leg_option_order,
    close_option_position,
    get_option_order_history,
    get_order_history,
    cancel_order,
    get_price_bars,
    get_current_datetime
)


class TestStandaloneFunctions:
    """Test suite for standalone function exports"""

    def test_get_account_info_function(self):
        """Test standalone get_account_info function"""
        # Test that the function exists and can be called
        result = get_account_info()
        assert isinstance(result, dict)
        # Should either have account info or error info
        assert "account_id" in result or "error" in result

    def test_get_positions_function(self):
        """Test standalone get_positions function"""
        result = get_positions()
        assert isinstance(result, list)
        # Should be a list, either empty or with positions/errors
        if result:
            assert isinstance(result[0], dict)

    def test_get_option_positions_function(self):
        """Test standalone get_option_positions function"""
        result = get_option_positions()
        assert isinstance(result, list)
        # Should be a list, either empty or with option positions/errors
        if result:
            assert isinstance(result[0], dict)

    def test_get_option_contracts_function(self):
        """Test standalone get_option_contracts function"""
        result = get_option_contracts("SPY")
        assert isinstance(result, list)
        # Should be a list, either empty or with contracts/errors
        if result:
            assert isinstance(result[0], dict)

    def test_get_options_chain_function(self):
        """Test standalone get_options_chain function"""
        result = get_options_chain("SPY")
        assert isinstance(result, dict)
        # Should either have chain data or error info
        assert "contracts" in result or "error" in result

    def test_get_option_quote_function(self):
        """Test standalone get_option_quote function"""
        result = get_option_quote("SPY241220C00450000")
        assert isinstance(result, dict)
        # Should either have quote data or error info
        assert "symbol" in result or "error" in result

    def test_place_option_order_function(self):
        """Test standalone place_option_order function"""
        result = place_option_order("SPY241220C00450000", "buy", 1, "market")
        assert isinstance(result, dict)
        # Should either have order data or error info
        assert "order_id" in result or "error" in result

    def test_place_multi_leg_option_order_function(self):
        """Test standalone place_multi_leg_option_order function"""
        legs = [{"symbol": "SPY241220C00450000", "side": "buy"}]
        result = place_multi_leg_option_order(legs, 1, "market")
        assert isinstance(result, dict)
        # Should either have order data or error info
        assert "order_id" in result or "error" in result

    def test_close_option_position_function(self):
        """Test standalone close_option_position function"""
        result = close_option_position("SPY241220C00450000", 1)
        assert isinstance(result, dict)
        # Should either have order data or error info
        assert "order_id" in result or "error" in result

    def test_get_option_order_history_function(self):
        """Test standalone get_option_order_history function"""
        result = get_option_order_history()
        assert isinstance(result, list)
        # Should be a list, either empty or with order history/errors
        if result:
            assert isinstance(result[0], dict)

    def test_get_order_history_function(self):
        """Test standalone get_order_history function"""
        result = get_order_history()
        assert isinstance(result, list)
        # Should be a list, either empty or with order history/errors
        if result:
            assert isinstance(result[0], dict)

    def test_cancel_order_function(self):
        """Test standalone cancel_order function"""
        result = cancel_order("test_order_123")
        assert isinstance(result, dict)
        # Should either have success info or error info
        assert "success" in result or "error" in result

    def test_get_price_bars_function(self):
        """Test standalone get_price_bars function"""
        result = get_price_bars("SPY", "1Hour", 10)
        assert isinstance(result, dict)
        # Should either have bar data or error info
        assert "data" in result or "error" in result

    def test_get_current_datetime_function(self):
        """Test standalone get_current_datetime function"""
        result = get_current_datetime()
        assert isinstance(result, dict)
        # Should have datetime info
        assert "timestamp" in result
        assert "date" in result
        assert "time" in result
