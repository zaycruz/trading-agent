"""
Tests for portfolio analysis functionality
"""

import pytest
from unittest.mock import Mock, patch

from alpaca_tools import AlpacaTradingTools, Position


class TestPortfolioAnalysis:
    """Test suite for portfolio analysis methods"""

    def test_get_account_info_success(self, trading_tools_with_mocks, mock_account_info):
        """Test successful account info retrieval"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_account.return_value = mock_account_info

        result = trading_tools.get_account_info()

        assert result["account_id"] == "test_account_id"
        assert result["buying_power"] == 100000.0
        assert result["portfolio_value"] == 100000.0
        assert result["status"] == "ACTIVE"
        assert result["trading_blocked"] is False
        trading_tools.trading_client.get_account.assert_called_once()

    def test_get_account_info_error(self, trading_tools_with_mocks):
        """Test account info retrieval with error"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_account.side_effect = Exception("API Error")

        result = trading_tools.get_account_info()

        assert "error" in result
        assert "Failed to get account info" in result["error"]

    def test_get_positions_success(self, trading_tools_with_mocks, mock_positions_list):
        """Test successful positions retrieval"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_all_positions.return_value = mock_positions_list

        positions = trading_tools.get_positions()

        assert len(positions) == 3
        assert positions[0].symbol == "SPY"
        assert positions[0].quantity == 100
        assert positions[0].unrealized_pl == 5000.0
        assert isinstance(positions[0], Position)

    def test_get_positions_empty(self, trading_tools_with_mocks):
        """Test positions retrieval with no positions"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_all_positions.return_value = []

        positions = trading_tools.get_positions()

        assert len(positions) == 0

    def test_get_positions_error(self, trading_tools_with_mocks):
        """Test positions retrieval with error"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_all_positions.side_effect = Exception("API Error")

        positions = trading_tools.get_positions()

        assert len(positions) == 0

    def test_get_position_by_symbol_success(self, trading_tools_with_mocks, mock_position):
        """Test successful single position retrieval"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_open_position.return_value = mock_position

        position = trading_tools.get_position_by_symbol("SPY")

        assert position is not None
        assert position.symbol == "SPY"
        assert position.quantity == 100
        assert position.market_value == 45000.0
        trading_tools.trading_client.get_open_position.assert_called_once_with("SPY")

    def test_get_position_by_symbol_not_found(self, trading_tools_with_mocks):
        """Test position retrieval for non-existent symbol"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_open_position.side_effect = Exception("position not found")

        position = trading_tools.get_position_by_symbol("NONEXISTENT")

        assert position is None

    def test_analyze_portfolio_with_positions(self, trading_tools_with_mocks, mock_positions_list, mock_account_info):
        """Test portfolio analysis with multiple positions"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_all_positions.return_value = mock_positions_list

        result = trading_tools.get_portfolio_analysis()

        assert "account_summary" in result
        assert "total_positions" in result
        assert "total_portfolio_value" in result
        assert "total_unrealized_pl" in result
        assert "position_analysis" in result
        assert "risk_metrics" in result

        assert result["total_positions"] == 3
        assert len(result["position_analysis"]) == 3

        # Check position analysis sorting (should be sorted by market value descending)
        positions = result["position_analysis"]
        assert positions[0]["symbol"] == "SPY"
        assert positions[0]["weight_pct"] > positions[1]["weight_pct"]

        # Check risk metrics
        risk_metrics = result["risk_metrics"]
        assert "largest_position_pct" in risk_metrics
        assert "position_count" in risk_metrics
        assert "portfolio_concentration" in risk_metrics

    def test_analyze_portfolio_empty(self, trading_tools_with_mocks, mock_account_info):
        """Test portfolio analysis with no positions"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_all_positions.return_value = []

        result = trading_tools.get_portfolio_analysis()

        assert "message" in result
        assert "No positions found" in result["message"]
        assert "account" in result

    def test_analyze_portfolio_error(self, trading_tools_with_mocks):
        """Test portfolio analysis with error"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_all_positions.side_effect = Exception("API Error")

        result = trading_tools.get_portfolio_analysis()

        assert "error" in result
        assert "Portfolio analysis failed" in result["error"]

    def test_position_analysis_calculations(self, trading_tools_with_mocks, mock_positions_list):
        """Test portfolio analysis calculations are correct"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_all_positions.return_value = mock_positions_list

        result = trading_tools.get_portfolio_analysis()

        total_value = sum([45000.0, 10000.0, 5000.0])  # Sum of market values
        assert result["total_portfolio_value"] == total_value

        total_pl = sum([5000.0, 1000.0, -1000.0])  # Sum of unrealized P&L
        assert result["total_unrealized_pl"] == total_pl

        # Check weight calculations
        positions = result["position_analysis"]
        spy_weight = (45000.0 / total_value) * 100
        assert abs(positions[0]["weight_pct"] - spy_weight) < 0.01

    def test_risk_level_assignment(self, trading_tools_with_mocks):
        """Test risk level assignment based on position weights"""
        trading_tools = trading_tools_with_mocks

        # Create mock positions with different weights
        high_risk_position = Mock()
        high_risk_position.symbol = "HIGH_RISK"
        high_risk_position.qty = "1000"
        high_risk_position.side = "long"
        high_risk_position.market_value = "30000.0"  # 30% of 100k portfolio
        high_risk_position.cost_basis = "25000.0"
        high_risk_position.unrealized_pl = "5000.0"
        high_risk_position.unrealized_plpc = "0.20"

        low_risk_position = Mock()
        low_risk_position.symbol = "LOW_RISK"
        low_risk_position.qty = "100"
        low_risk_position.side = "long"
        low_risk_position.market_value = "5000.0"  # 5% of 100k portfolio
        low_risk_position.cost_basis = "4000.0"
        low_risk_position.unrealized_pl = "1000.0"
        low_risk_position.unrealized_plpc = "0.25"

        trading_tools.trading_client.get_all_positions.return_value = [high_risk_position, low_risk_position]

        result = trading_tools.get_portfolio_analysis()
        positions = result["position_analysis"]

        # Find the high risk position
        high_risk_pos = next(pos for pos in positions if pos["symbol"] == "HIGH_RISK")
        low_risk_pos = next(pos for pos in positions if pos["symbol"] == "LOW_RISK")

        assert high_risk_pos["risk_level"] == "HIGH"
        assert low_risk_pos["risk_level"] == "LOW"

    def test_portfolio_concentration_metrics(self, trading_tools_with_mocks, mock_positions_list):
        """Test portfolio concentration risk metrics"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_all_positions.return_value = mock_positions_list

        result = trading_tools.get_portfolio_analysis()
        risk_metrics = result["risk_metrics"]

        # With 3 positions, diversification should be FAIR
        assert risk_metrics["position_count"] == 3
        assert risk_metrics["portfolio_concentration"] in ["FAIR", "POOR"]

        # Largest position should be SPY (45000 value out of 60000 total)
        assert risk_metrics["largest_position_pct"] > 70  # Should be around 75%