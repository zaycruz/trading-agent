"""
Tests for standalone function exports
"""

import pytest
from unittest.mock import Mock, patch

# Import the standalone functions
from src.tools import (
    get_account_info,
    analyze_portfolio,
    get_positions,
    screen_options,
    buy_option,
    sell_option,
    close_position,
    create_vertical_spread,
    create_iron_condor,
    create_straddle,
    create_strangle,
    validate_trade_risk,
    get_risk_summary
)


class TestStandaloneFunctions:
    """Test suite for standalone function exports"""

    @patch('src.tools.trading_tools')
    def test_get_account_info_function(self, mock_trading_tools):
        """Test standalone get_account_info function"""
        mock_trading_tools.get_account_info.return_value = {"account_id": "test123"}

        result = get_account_info()

        assert result["account_id"] == "test123"
        mock_trading_tools.get_account_info.assert_called_once()

    @patch('src.tools.trading_tools')
    def test_analyze_portfolio_function(self, mock_trading_tools):
        """Test standalone analyze_portfolio function"""
        mock_trading_tools.get_portfolio_analysis.return_value = {"total_positions": 5}

        result = analyze_portfolio()

        assert result["total_positions"] == 5
        mock_trading_tools.get_portfolio_analysis.assert_called_once()

    @patch('src.tools.trading_tools')
    def test_get_positions_function(self, mock_trading_tools):
        """Test standalone get_positions function"""
        from src.tools import Position
        mock_positions = [Position("SPY", 100, "long", 45000.0, 40000.0, 5000.0, 0.125)]
        mock_trading_tools.get_positions.return_value = mock_positions

        result = get_positions()

        assert len(result) == 1
        assert result[0].symbol == "SPY"
        mock_trading_tools.get_positions.assert_called_once()

    @patch('src.tools.trading_tools')
    def test_screen_options_function(self, mock_trading_tools):
        """Test standalone screen_options function"""
        mock_trading_tools.screen_options_contracts.return_value = []

        result = screen_options("SPY", min_dte=7, max_dte=30)

        assert isinstance(result, list)
        mock_trading_tools.screen_options_contracts.assert_called_once_with("SPY", 7, 30)

    @patch('src.tools.trading_tools')
    def test_buy_option_function(self, mock_trading_tools):
        """Test standalone buy_option function"""
        mock_trading_tools.buy_option_contract.return_value = {"success": True, "order_id": "123"}

        result = buy_option("SPY241220C00450000", 1, "market", 2.50)

        assert result["success"] is True
        assert result["order_id"] == "123"
        mock_trading_tools.buy_option_contract.assert_called_once()

    @patch('src.tools.trading_tools')
    def test_sell_option_function(self, mock_trading_tools):
        """Test standalone sell_option function"""
        mock_trading_tools.sell_option_contract.return_value = {"success": True, "order_id": "456"}

        result = sell_option("SPY241220C00450000", 1, "limit", 2.75)

        assert result["success"] is True
        assert result["order_id"] == "456"
        mock_trading_tools.sell_option_contract.assert_called_once()

    @patch('src.tools.trading_tools')
    def test_close_position_function(self, mock_trading_tools):
        """Test standalone close_position function"""
        mock_trading_tools.close_option_position.return_value = {"success": True, "quantity_closed": 5}

        result = close_position("SPY241220C00450000", 5)

        assert result["success"] is True
        assert result["quantity_closed"] == 5
        mock_trading_tools.close_option_position.assert_called_once()

    @patch('src.tools.trading_tools')
    def test_create_vertical_spread_function(self, mock_trading_tools):
        """Test standalone create_vertical_spread function"""
        mock_trading_tools.create_vertical_spread.return_value = {"success": True, "strategy": "vertical_spread"}

        result = create_vertical_spread("SPY", "call_credit", 455.0, 460.0, "2024-12-20", 2)

        assert result["success"] is True
        assert result["strategy"] == "vertical_spread"
        mock_trading_tools.create_vertical_spread.assert_called_once()

    @patch('src.tools.trading_tools')
    def test_create_iron_condor_function(self, mock_trading_tools):
        """Test standalone create_iron_condor function"""
        mock_trading_tools.create_iron_condor.return_value = {"success": True, "strategy": "iron_condor"}

        result = create_iron_condor("SPY", 455.0, 460.0, 445.0, 440.0, "2024-12-20", 1)

        assert result["success"] is True
        assert result["strategy"] == "iron_condor"
        mock_trading_tools.create_iron_condor.assert_called_once()

    @patch('src.tools.trading_tools')
    def test_create_straddle_function(self, mock_trading_tools):
        """Test standalone create_straddle function"""
        mock_trading_tools.create_straddle.return_value = {"success": True, "strategy": "straddle"}

        result = create_straddle("SPY", 450.0, "2024-12-20", 1)

        assert result["success"] is True
        assert result["strategy"] == "straddle"
        mock_trading_tools.create_straddle.assert_called_once()

    @patch('src.tools.trading_tools')
    def test_create_strangle_function(self, mock_trading_tools):
        """Test standalone create_strangle function"""
        mock_trading_tools.create_strangle.return_value = {"success": True, "strategy": "strangle"}

        result = create_strangle("SPY", 455.0, 445.0, "2024-12-20", 1)

        assert result["success"] is True
        assert result["strategy"] == "strangle"
        mock_trading_tools.create_strangle.assert_called_once()

    @patch('src.tools.trading_tools')
    def test_validate_trade_risk_function(self, mock_trading_tools):
        """Test standalone validate_trade_risk function"""
        mock_trading_tools.validate_trade_risk.return_value = {"approved": True, "warnings": []}

        result = validate_trade_risk("SPY241220C00450000", 1)

        assert result["approved"] is True
        assert len(result["warnings"]) == 0
        mock_trading_tools.validate_trade_risk.assert_called_once()

    @patch('src.tools.trading_tools')
    def test_get_risk_summary_function(self, mock_trading_tools):
        """Test standalone get_risk_summary function"""
        mock_trading_tools.get_risk_summary.return_value = {"total_exposure": 50000, "risk_level": "MEDIUM"}

        result = get_risk_summary()

        assert result["total_exposure"] == 50000
        assert result["risk_level"] == "MEDIUM"
        mock_trading_tools.get_risk_summary.assert_called_once()