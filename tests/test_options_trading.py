"""
Tests for options trading functionality
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

try:
    from alpaca_tools import AlpacaTradingTools, OptionContract, OptionType, OptionStrategy
except ImportError:
    pytest.skip("Legacy AlpacaTradingTools module not available", allow_module_level=True)


class TestOptionsTrading:
    """Test suite for options trading methods"""

    def test_get_current_price_success(self, trading_tools_with_mocks, mock_quote):
        """Test successful current price retrieval"""
        trading_tools = trading_tools_with_mocks
        trading_tools.stock_data_client.get_stock_latest_quote.return_value = {"SPY": mock_quote}

        price = trading_tools.get_current_price("SPY")

        assert price == 448.5  # (447.50 + 449.50) / 2
        trading_tools.stock_data_client.get_stock_latest_quote.assert_called_once()

    def test_get_current_price_error(self, trading_tools_with_mocks):
        """Test current price retrieval with error"""
        trading_tools = trading_tools_with_mocks
        trading_tools.stock_data_client.get_stock_latest_quote.side_effect = Exception("API Error")

        price = trading_tools.get_current_price("SPY")

        assert price is None

    def test_buy_option_market_order_success(self, trading_tools_with_mocks, mock_order):
        """Test successful market order for buying options"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.submit_order.return_value = mock_order

        result = trading_tools.buy_option_contract("SPY241220C00450000", 1)

        assert result["success"] is True
        assert result["order_id"] == "test_order_id"
        assert result["symbol"] == "SPY241220C00450000"
        assert result["quantity"] == 1
        assert result["order_type"] == "market"

    def test_buy_option_limit_order_success(self, trading_tools_with_mocks, mock_order):
        """Test successful limit order for buying options"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.submit_order.return_value = mock_order

        result = trading_tools.buy_option_contract(
            "SPY241220C00450000",
            1,
            order_type="limit",
            limit_price=2.50
        )

        assert result["success"] is True
        assert result["order_id"] == "test_order_id"
        assert result["quantity"] == 1
        assert result["order_type"] == "limit"

    def test_buy_option_error(self, trading_tools_with_mocks):
        """Test option buying with error"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.submit_order.side_effect = Exception("Insufficient buying power")

        result = trading_tools.buy_option_contract("SPY241220C00450000", 1)

        assert result["success"] is False
        assert "Insufficient buying power" in result["error"]

    def test_sell_option_market_order_success(self, trading_tools_with_mocks, mock_order):
        """Test successful market order for selling options"""
        trading_tools = trading_tools_with_mocks
        mock_order.side = "sell"
        trading_tools.trading_client.submit_order.return_value = mock_order

        result = trading_tools.sell_option_contract("SPY241220C00450000", 1)

        assert result["success"] is True
        assert result["order_id"] == "test_order_id"
        assert result["symbol"] == "SPY241220C00450000"
        assert result["quantity"] == 1

    def test_sell_option_limit_order_success(self, trading_tools_with_mocks, mock_order):
        """Test successful limit order for selling options"""
        trading_tools = trading_tools_with_mocks
        mock_order.side = "sell"
        trading_tools.trading_client.submit_order.return_value = mock_order

        result = trading_tools.sell_option_contract(
            "SPY241220C00450000",
            1,
            order_type="limit",
            limit_price=2.75
        )

        assert result["success"] is True
        assert result["order_type"] == "limit"

    def test_close_position_success(self, trading_tools_with_mocks, mock_position, mock_order):
        """Test successful position closing"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_open_position.return_value = mock_position
        trading_tools.trading_client.submit_order.return_value = mock_order

        result = trading_tools.close_option_position("SPY")

        assert result["success"] is True
        assert result["order_id"] == "test_order_id"
        assert result["symbol"] == "SPY"
        assert result["quantity_closed"] == 100  # Absolute value of position quantity
        assert result["original_position"] == 100

    def test_close_position_with_quantity(self, trading_tools_with_mocks, mock_position, mock_order):
        """Test position closing with specific quantity"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_open_position.return_value = mock_position
        trading_tools.trading_client.submit_order.return_value = mock_order

        result = trading_tools.close_option_position("SPY", quantity=50)

        assert result["success"] is True
        assert result["quantity_closed"] == 50
        assert result["original_position"] == 100

    def test_close_position_not_found(self, trading_tools_with_mocks):
        """Test closing non-existent position"""
        trading_tools = trading_tools_with_mocks
        trading_tools.trading_client.get_open_position.side_effect = Exception("position not found")

        result = trading_tools.close_option_position("NONEXISTENT")

        assert result["success"] is False
        assert "No position found" in result["error"]

    def test_close_position_short(self, trading_tools_with_mocks, mock_order):
        """Test closing a short position"""
        trading_tools = trading_tools_with_mocks

        # Create a short position
        short_position = Mock()
        short_position.symbol = "SPY"
        short_position.qty = "-50"
        short_position.side = "short"
        short_position.market_value = "-5000.0"
        short_position.cost_basis = "0.0"
        short_position.unrealized_pl = "-5000.0"
        short_position.unrealized_plpc = "-1.0"

        trading_tools.trading_client.get_open_position.return_value = short_position
        trading_tools.trading_client.submit_order.return_value = mock_order

        result = trading_tools.close_option_position("SPY")

        assert result["success"] is True
        assert result["quantity_closed"] == 50
        assert result["original_position"] == -50

    def test_screen_options_contracts_basic(self, trading_tools_with_mocks, mock_quote):
        """Test basic options contract screening"""
        trading_tools = trading_tools_with_mocks
        trading_tools.stock_data_client.get_stock_latest_quote.return_value = {"SPY": mock_quote}

        # Mock calendar with future dates
        future_date = Mock()
        future_date._date = datetime.now().date() + timedelta(days=30)
        trading_tools.trading_client.get_calendar.return_value = [future_date]

        # Mock options chain
        mock_contract = OptionContract(
            symbol="SPY241220C00450000",
            strike=450.0,
            expiration="2024-12-20",
            option_type="call",
            underlying_price=448.50,
            bid=2.50,
            ask=2.75,
            volume=150,
            open_interest=2500,
            implied_volatility=0.25,
            delta=0.45,
            gamma=0.02,
            theta=-0.05,
            vega=0.15
        )
        trading_tools.get_options_chain = Mock(return_value=[mock_contract])

        result = trading_tools.screen_options_contracts("SPY", min_dte=7, max_dte=60)

        assert len(result) == 1
        assert result[0].symbol == "SPY241220C00450000"
        assert result[0].volume == 150
        assert result[0].open_interest == 2500

    def test_screen_options_volume_filter(self, trading_tools_with_mocks, mock_quote):
        """Test options screening with volume filter"""
        trading_tools = trading_tools_with_mocks
        trading_tools.stock_data_client.get_stock_latest_quote.return_value = {"SPY": mock_quote}

        # Mock calendar
        future_date = Mock()
        future_date._date = datetime.now().date() + timedelta(days=30)
        trading_tools.trading_client.get_calendar.return_value = [future_date]

        # Create contracts with different volumes
        high_volume_contract = OptionContract(
            symbol="SPY241220C00450000",
            strike=450.0,
            expiration="2024-12-20",
            option_type="call",
            underlying_price=448.50,
            bid=2.50,
            ask=2.75,
            volume=150,  # Above min_volume
            open_interest=2500,
            implied_volatility=0.25,
            delta=0.45,
            gamma=0.02,
            theta=-0.05,
            vega=0.15
        )

        low_volume_contract = OptionContract(
            symbol="SPY241220C00440000",
            strike=440.0,
            expiration="2024-12-20",
            option_type="call",
            underlying_price=448.50,
            bid=4.50,
            ask=4.75,
            volume=5,  # Below min_volume
            open_interest=100,
            implied_volatility=0.30,
            delta=0.65,
            gamma=0.03,
            theta=-0.08,
            vega=0.20
        )

        trading_tools.get_options_chain = Mock(return_value=[high_volume_contract, low_volume_contract])

        result = trading_tools.screen_options_contracts("SPY", min_volume=50)

        assert len(result) == 1
        assert result[0].symbol == "SPY241220C00450000"

    def test_get_expiration_dates(self, trading_tools_with_mocks):
        """Test expiration date retrieval"""
        trading_tools = trading_tools_with_mocks

        # Create calendar dates with different DTE
        today = datetime.now().date()
        dates = []
        for days in [5, 15, 30, 45, 75]:  # Mix of within and outside range
            date = Mock()
            date._date = today + timedelta(days=days)
            dates.append(date)

        trading_tools.trading_client.get_calendar.return_value = dates

        result = trading_tools.get_expiration_dates(min_dte=7, max_dte=60)

        assert len(result) == 3  # Only dates within 7-60 days
        assert all(7 <= (datetime.strptime(d, "%Y-%m-%d").date() - today).days <= 60 for d in result)

    def test_vertical_spread_creation(self, trading_tools_with_mocks):
        """Test vertical spread strategy creation"""
        trading_tools = trading_tools_with_mocks

        result = trading_tools.create_vertical_spread(
            underlying_symbol="SPY",
            spread_type="call_credit",
            short_strike=455.0,
            long_strike=460.0,
            expiration_date="2024-12-20",
            quantity=2,
            credit_limit=1.50
        )

        assert result["success"] is True
        assert result["strategy"]["strategy_type"] == "vertical_spread"
        assert result["strategy"]["spread_type"] == "call_credit"
        assert result["strategy"]["underlying"] == "SPY"
        assert result["strategy"]["short_strike"] == 455.0
        assert result["strategy"]["long_strike"] == 460.0
        assert result["strategy"]["quantity"] == 2
        assert result["strategy"]["credit_limit"] == 1.50

    def test_vertical_spread_invalid_type(self, trading_tools_with_mocks):
        """Test vertical spread with invalid spread type"""
        trading_tools = trading_tools_with_mocks

        result = trading_tools.create_vertical_spread(
            underlying_symbol="SPY",
            spread_type="invalid_spread",
            short_strike=455.0,
            long_strike=460.0,
            expiration_date="2024-12-20"
        )

        assert result["success"] is False
        assert "Invalid spread type" in result["error"]

    def test_iron_condor_creation(self, trading_tools_with_mocks):
        """Test iron condor strategy creation"""
        trading_tools = trading_tools_with_mocks

        result = trading_tools.create_iron_condor(
            underlying_symbol="SPY",
            short_call_strike=455.0,
            long_call_strike=460.0,
            short_put_strike=445.0,
            long_put_strike=440.0,
            expiration_date="2024-12-20",
            quantity=1,
            credit_target=2.00
        )

        assert result["success"] is True
        assert result["strategy"]["strategy_type"] == "iron_condor"
        assert result["strategy"]["underlying"] == "SPY"
        assert result["strategy"]["strikes"]["short_call"] == 455.0
        assert result["strategy"]["strikes"]["long_call"] == 460.0
        assert result["strategy"]["strikes"]["short_put"] == 445.0
        assert result["strategy"]["strikes"]["long_put"] == 440.0
        assert result["strategy"]["credit_target"] == 2.00
        assert result["strategy"]["max_loss"] == 500.0  # (460-455-445+440) * 100

    def test_iron_condor_invalid_strikes(self, trading_tools_with_mocks):
        """Test iron condor with invalid strike arrangement"""
        trading_tools = trading_tools_with_mocks

        result = trading_tools.create_iron_condor(
            underlying_symbol="SPY",
            short_call_strike=455.0,
            long_call_strike=450.0,  # Wrong order
            short_put_strike=445.0,
            long_put_strike=440.0,
            expiration_date="2024-12-20"
        )

        assert result["success"] is False
        assert "Invalid strike arrangement" in result["error"]

    def test_straddle_creation(self, trading_tools_with_mocks):
        """Test straddle strategy creation"""
        trading_tools = trading_tools_with_mocks

        result = trading_tools.create_straddle(
            underlying_symbol="SPY",
            strike=450.0,
            expiration_date="2024-12-20",
            quantity=2
        )

        assert result["success"] is True
        assert result["strategy"]["strategy_type"] == "straddle"
        assert result["strategy"]["strike"] == 450.0
        assert result["strategy"]["quantity"] == 2
        assert len(result["strategy"]["contracts"]) == 2
        assert result["strategy"]["contracts"][0]["type"] == "call"
        assert result["strategy"]["contracts"][1]["type"] == "put"

    def test_strangle_creation(self, trading_tools_with_mocks):
        """Test strangle strategy creation"""
        trading_tools = trading_tools_with_mocks

        result = trading_tools.create_strangle(
            underlying_symbol="SPY",
            call_strike=455.0,
            put_strike=445.0,
            expiration_date="2024-12-20",
            quantity=1
        )

        assert result["success"] is True
        assert result["strategy"]["strategy_type"] == "strangle"
        assert result["strategy"]["strikes"]["call"] == 455.0
        assert result["strategy"]["strikes"]["put"] == 445.0
        assert len(result["strategy"]["contracts"]) == 2
