"""
Pytest configuration and fixtures for trading tools tests
"""

import os
import pytest
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass

from alpaca_tools import AlpacaTradingTools, TradingConfig, Position, OptionContract


@pytest.fixture
def mock_trading_config():
    """Mock trading configuration for testing"""
    return TradingConfig(
        api_key="test_api_key",
        secret_key="test_secret_key",
        base_url="https://paper-api.alpaca.markets",
        data_url="https://data.alpaca.markets",
        paper_trading=True
    )


@pytest.fixture
def mock_alpaca_clients():
    """Mock alpaca clients for testing"""
    mock_trading_client = Mock()
    mock_stock_data_client = Mock()
    mock_option_data_client = Mock()

    return {
        'trading_client': mock_trading_client,
        'stock_data_client': mock_stock_data_client,
        'option_data_client': mock_option_data_client
    }


@pytest.fixture
def mock_account_info():
    """Mock account information"""
    account = Mock()
    account.id = "test_account_id"
    account.buying_power = "100000.0"
    account.cash = "50000.0"
    account.portfolio_value = "100000.0"
    account.equity = "100000.0"
    account.long_market_value = "75000.0"
    account.short_market_value = "25000.0"
    account.initial_margin = "30000.0"
    account.maintenance_margin = "20000.0"
    account.daytrading_buying_power = "200000.0"
    account.regt_buying_power = "100000.0"
    account.status = "ACTIVE"
    account.trading_blocked = False
    account.transfers_blocked = False
    account.account_blocked = False
    return account


@pytest.fixture
def mock_position():
    """Mock position data"""
    position = Mock()
    position.symbol = "SPY"
    position.qty = "100"
    position.side = "long"
    position.market_value = "45000.0"
    position.cost_basis = "40000.0"
    position.unrealized_pl = "5000.0"
    position.unrealized_plpc = "0.125"
    return position


@pytest.fixture
def mock_positions_list(mock_position):
    """Mock list of positions"""
    position2 = Mock()
    position2.symbol = "AAPL"
    position2.qty = "50"
    position2.side = "long"
    position2.market_value = "10000.0"
    position2.cost_basis = "9000.0"
    position2.unrealized_pl = "1000.0"
    position2.unrealized_plpc = "0.111"

    position3 = Mock()
    position3.symbol = "TSLA"
    position3.qty = "20"
    position3.side = "long"
    position3.market_value = "5000.0"
    position3.cost_basis = "6000.0"
    position3.unrealized_pl = "-1000.0"
    position3.unrealized_plpc = "-0.167"

    return [mock_position, position2, position3]


@pytest.fixture
def mock_option_contract():
    """Mock option contract data"""
    return OptionContract(
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


@pytest.fixture
def mock_quote():
    """Mock stock quote data"""
    quote = Mock()
    quote.bid_price = 447.50
    quote.ask_price = 449.50
    return quote


@pytest.fixture
def mock_order():
    """Mock order data"""
    order = Mock()
    order.id = "test_order_id"
    order.symbol = "SPY241220C00450000"
    order.qty = "1"
    order.side = "buy"
    order.type = "market"
    order.status = "accepted"
    return order


@pytest.fixture
def trading_tools_with_mocks(mock_trading_config, mock_alpaca_clients, mock_account_info):
    """Trading tools instance with mocked clients"""
    tools = AlpacaTradingTools(mock_trading_config)

    # Replace the actual clients with mocks
    tools.trading_client = mock_alpaca_clients['trading_client']
    tools.stock_data_client = mock_alpaca_clients['stock_data_client']
    tools.option_data_client = mock_alpaca_clients['option_data_client']

    # Set up default mock responses
    tools.trading_client.get_account.return_value = mock_account_info
    tools.trading_client.get_all_positions.return_value = []

    return tools


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio data for testing calculations"""
    return {
        "positions": [
            {"symbol": "SPY", "value": 50000, "pl": 2000},
            {"symbol": "QQQ", "value": 30000, "pl": -500},
            {"symbol": "AAPL", "value": 20000, "pl": 1000}
        ],
        "total_value": 100000,
        "total_pl": 2500
    }


@pytest.fixture(scope="session")
def test_symbols():
    """Common test symbols"""
    return {
        "equities": ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL"],
        "options": ["SPY241220C00450000", "AAPL241220P00150000"],
        "etfs": ["SPY", "QQQ", "IWM", "DIA"]
    }


# Test environment setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    # Set test environment variables
    os.environ["ALPACA_API_KEY"] = "test_api_key"
    os.environ["ALPACA_SECRET_KEY"] = "test_secret_key"

    yield

    # Cleanup
    os.environ.pop("ALPACA_API_KEY", None)
    os.environ.pop("ALPACA_SECRET_KEY", None)