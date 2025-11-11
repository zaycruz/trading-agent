"""
Integration tests for the complete trading tools workflow
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from alpaca_tools import AlpacaTradingTools, get_account_info, analyze_portfolio, screen_options, buy_option, validate_trade_risk


class TestIntegrationWorkflow:
    """Test suite for complete trading workflows"""

    def test_complete_portfolio_analysis_workflow(self, trading_tools_with_mocks, mock_account_info, mock_positions_list):
        """Test complete portfolio analysis workflow"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_account.return_value = mock_account_info
        trading_tools.trading_client.get_all_positions.return_value = mock_positions_list

        # Step 1: Get account info
        account_info = trading_tools.get_account_info()
        assert account_info["portfolio_value"] == 100000.0

        # Step 2: Get detailed portfolio analysis
        portfolio_analysis = trading_tools.get_portfolio_analysis()
        assert portfolio_analysis["total_positions"] == 3
        assert len(portfolio_analysis["position_analysis"]) == 3

        # Step 3: Get risk summary
        risk_summary = trading_tools.get_risk_summary()
        assert risk_summary["position_count"] == 3
        assert risk_summary["diversification_score"] == "POOR"

        # Verify data consistency across calls
        assert account_info["portfolio_value"] == portfolio_analysis["account_summary"]["portfolio_value"]
        assert portfolio_analysis["total_positions"] == risk_summary["position_count"]

    def test_options_trading_workflow(self, trading_tools_with_mocks, mock_quote, mock_order):
        """Test complete options trading workflow"""
        trading_tools = trading_tools_with_mocks
        trading_tools.stock_data_client.get_stock_latest_quote.return_value = {"SPY": mock_quote}
        trading_tools.trading_client.get_account.return_value = Mock(portfolio_value="100000.0")
        trading_tools.trading_client.submit_order.return_value = mock_order

        # Step 1: Get current price
        current_price = trading_tools.get_current_price("SPY")
        assert current_price == 448.5

        # Step 2: Validate trade risk
        risk_check = trading_tools.validate_trade_risk("SPY241220C00450000", 1)
        assert risk_check["approved"] is True

        # Step 3: Execute trade
        trade_result = trading_tools.buy_option_contract("SPY241220C00450000", 1)
        assert trade_result["success"] is True
        assert trade_result["order_id"] == "test_order_id"

        # Step 4: Close position (simulate having a position)
        mock_position = Mock()
        mock_position.symbol = "SPY241220C00450000"
        mock_position.qty = "1"
        mock_position.side = "long"
        mock_position.market_value = "250.0"
        mock_position.cost_basis = "275.0"
        mock_position.unrealized_pl = "-25.0"
        mock_position.unrealized_plpc = "-0.091"

        trading_tools.trading_client.get_open_position.return_value = mock_position

        close_result = trading_tools.close_option_position("SPY241220C00450000")
        assert close_result["success"] is True

    def test_multi_leg_strategy_workflow(self, trading_tools_with_mocks, mock_quote):
        """Test multi-leg options strategy workflow"""
        trading_tools = trading_tools_with_mocks
        trading_tools.stock_data_client.get_stock_latest_quote.return_value = {"SPY": mock_quote}
        trading_tools.trading_client.get_account.return_value = Mock(portfolio_value="100000.0")

        # Step 1: Create vertical spread
        spread_result = trading_tools.create_vertical_spread(
            underlying_symbol="SPY",
            spread_type="call_credit",
            short_strike=455.0,
            long_strike=460.0,
            expiration_date="2024-12-20",
            quantity=2,
            credit_limit=1.50
        )
        assert spread_result["success"] is True

        # Step 2: Create iron condor
        condor_result = trading_tools.create_iron_condor(
            underlying_symbol="SPY",
            short_call_strike=455.0,
            long_call_strike=460.0,
            short_put_strike=445.0,
            long_put_strike=440.0,
            expiration_date="2024-12-20",
            quantity=1,
            credit_target=2.00
        )
        assert condor_result["success"] is True

        # Step 3: Create straddle
        straddle_result = trading_tools.create_straddle(
            underlying_symbol="SPY",
            strike=450.0,
            expiration_date="2024-12-20",
            quantity=1
        )
        assert straddle_result["success"] is True

        # Step 4: Create strangle
        strangle_result = trading_tools.create_strangle(
            underlying_symbol="SPY",
            call_strike=455.0,
            put_strike=445.0,
            expiration_date="2024-12-20",
            quantity=1
        )
        assert strangle_result["success"] is True

    def test_options_screening_workflow(self, trading_tools_with_mocks, mock_quote):
        """Test complete options screening workflow"""
        trading_tools = trading_tools_with_mocks
        trading_tools.stock_data_client.get_stock_latest_quote.return_value = {"SPY": mock_quote}
        trading_tools.trading_client.get_account.return_value = Mock(portfolio_value="100000.0")

        # Set up calendar mock
        future_date = Mock()
        future_date._date = datetime.now().date() + timedelta(days=30)
        trading_tools.trading_client.get_calendar.return_value = [future_date]

        # Step 1: Get expiration dates
        exp_dates = trading_tools.get_expiration_dates(min_dte=7, max_dte=60)
        assert len(exp_dates) >= 1

        # Step 2: Screen options (mock implementation)
        trading_tools.get_options_chain = Mock(return_value=[])
        screened_options = trading_tools.screen_options_contracts("SPY", min_dte=7, max_dte=30)
        assert isinstance(screened_options, list)

    def test_risk_management_integration(self, trading_tools_with_mocks, mock_account_info, mock_positions_list, mock_quote):
        """Test integrated risk management across different scenarios"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_account.return_value = mock_account_info
        trading_tools.trading_client.get_all_positions.return_value = mock_positions_list
        trading_tools.stock_data_client.get_stock_latest_quote.return_value = {"SPY": mock_quote}

        # Step 1: Check overall portfolio risk
        risk_summary = trading_tools.get_risk_summary()
        assert risk_summary["total_exposure"] > 0

        # Step 2: Validate different trade sizes
        small_trade = trading_tools.validate_trade_risk("SPY241220C00450000", 1, max_position_pct=0.05)
        assert small_trade["approved"] is True

        large_trade = trading_tools.validate_trade_risk("SPY241220C00450000", 10, max_position_pct=0.05)
        assert large_trade["approved"] is False

        # Step 3: Check buying power for trades
        small_cost = trading_tools.check_buying_power(5000.0)
        assert small_cost["sufficient_funds"] is True

        large_cost = trading_tools.check_buying_power(200000.0)
        assert large_cost["sufficient_funds"] is False

    def test_error_handling_workflow(self, trading_tools_with_mocks):
        """Test error handling throughout the workflow"""
        trading_tools = trading_tools_with_mocks

        # Mock various API failures
        trading_tools.trading_client.get_account.side_effect = Exception("Account API Error")
        trading_tools.trading_client.get_all_positions.side_effect = Exception("Positions API Error")
        trading_tools.stock_data_client.get_stock_latest_quote.side_effect = Exception("Data API Error")

        # Test graceful error handling
        account_result = trading_tools.get_account_info()
        assert "error" in account_result

        portfolio_result = trading_tools.get_portfolio_analysis()
        assert "error" in portfolio_result

        risk_result = trading_tools.get_risk_summary()
        assert "error" in risk_result

        price_result = trading_tools.get_current_price("SPY")
        assert price_result is None

        # Test trade validation with no price data
        trade_validation = trading_tools.validate_trade_risk("SPY241220C00450000", 1)
        assert "error" in trade_validation

    def test_standalone_function_integration(self, trading_tools_with_mocks, mock_account_info, mock_positions_list):
        """Test integration using standalone functions"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_account.return_value = mock_account_info
        trading_tools.trading_client.get_all_positions.return_value = mock_positions_list

        # Patch the global trading_tools instance
        with patch('src.tools.trading_tools', trading_tools):
            # Test standalone functions
            account = get_account_info()
            assert account["account_id"] == "test_account_id"

            portfolio = analyze_portfolio()
            assert portfolio["total_positions"] == 3

            # Test options screening
            with patch.object(trading_tools.stock_data_client, 'get_stock_latest_quote') as mock_quote:
                mock_quote.return_value = {"SPY": Mock(bid_price=447.5, ask_price=449.5)}
                with patch.object(trading_tools, 'get_options_chain', return_value=[]):
                    options = screen_options("SPY")
                    assert isinstance(options, list)

            # Test trade validation
            with patch.object(trading_tools.stock_data_client, 'get_stock_latest_quote') as mock_quote:
                mock_quote.return_value = {"SPY": Mock(bid_price=447.5, ask_price=449.5)}
                validation = validate_trade_risk("SPY241220C00450000", 1)
                assert validation["approved"] is True

    def test_data_consistency_across_modules(self, trading_tools_with_mocks, mock_account_info, mock_positions_list):
        """Test data consistency across different module functions"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_account.return_value = mock_account_info
        trading_tools.trading_client.get_all_positions.return_value = mock_positions_list

        # Get data from different sources
        account_direct = trading_tools.get_account_info()
        portfolio_analysis = trading_tools.get_portfolio_analysis()

        # Verify consistency
        assert account_direct["portfolio_value"] == portfolio_analysis["account_summary"]["portfolio_value"]
        assert account_direct["buying_power"] == portfolio_analysis["account_summary"]["buying_power"]

        # Test position data consistency
        positions_direct = trading_tools.get_positions()
        positions_from_analysis = portfolio_analysis["position_analysis"]

        assert len(positions_direct) == len(positions_from_analysis)
        for i, pos in enumerate(positions_direct):
            assert pos.symbol == positions_from_analysis[i]["symbol"]
            assert pos.market_value == positions_from_analysis[i]["market_value"]

    def test_performance_metrics_tracking(self, trading_tools_with_mocks, mock_positions_list):
        """Test performance metrics are correctly calculated and tracked"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_all_positions.return_value = mock_positions_list
        trading_tools.trading_client.get_account.return_value = Mock(portfolio_value="100000.0")

        # Get portfolio analysis
        portfolio = trading_tools.get_portfolio_analysis()

        # Verify P&L calculations
        total_unrealized = portfolio["total_unrealized_pl"]
        expected_total = sum([pos.unrealized_pl for pos in trading_tools.get_positions()])
        assert total_unrealized == expected_total

        # Get risk summary
        risk_summary = trading_tools.get_risk_summary()

        # Verify winning/losing position counts
        winning_count = risk_summary["winning_positions_count"]
        losing_count = risk_summary["losing_positions_count"]
        assert winning_count == 2  # SPY and AAPL
        assert losing_count == 1  # TSLA

        # Verify max drawdown
        max_drawdown = risk_summary["risk_metrics"]["max_drawdown"]
        assert max_drawdown == -1000.0  # TSLA position

    @pytest.mark.parametrize("trade_size,expected_approval", [
        (1, True),   # Small trade should be approved
        (5, True),   # Medium trade should be approved
        (20, False), # Large trade should be rejected
    ])
    def test_parameterized_trade_validation(self, trading_tools_with_mocks, mock_quote, trade_size, expected_approval):
        """Test trade validation with different trade sizes"""
        trading_tools = trading_tools_with_mocks
        trading_tools.stock_data_client.get_stock_latest_quote.return_value = {"SPY": mock_quote}
        trading_tools.trading_client.get_all_positions.return_value = []
        trading_tools.trading_client.get_account.return_value = Mock(portfolio_value="100000.0")

        result = trading_tools.validate_trade_risk("SPY241220C00450000", trade_size, max_position_pct=0.10)

        if expected_approval:
            assert result["approved"] is True
        else:
            assert result["approved"] is False
            assert len(result["warnings"]) > 0