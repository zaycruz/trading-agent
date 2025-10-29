# Test Suite for Trading Arena

This directory contains a comprehensive test suite for the autonomous options trader tools.

## 📁 Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest configuration and fixtures
├── test_portfolio_analysis.py  # Portfolio analysis tests
├── test_options_trading.py     # Options trading tests
├── test_risk_management.py     # Risk management tests
├── test_integration.py         # Integration tests
├── test_standalone_functions.py # Standalone function tests
└── README.md                   # This file
```

## 🧪 Test Categories

### Unit Tests
- **Portfolio Analysis** (`test_portfolio_analysis.py`)
  - Account information retrieval
  - Position tracking and P&L calculations
  - Portfolio concentration metrics
  - Risk level assignments

- **Options Trading** (`test_options_trading.py`)
  - Options contract screening
  - Buy/sell order execution
  - Position management
  - Multi-leg strategy creation
  - Price data retrieval

- **Risk Management** (`test_risk_management.py`)
  - Buying power validation
  - Position risk calculations
  - Trade approval logic
  - Portfolio risk metrics
  - Concentration limit enforcement

### Integration Tests
- **Complete Workflows** (`test_integration.py`)
  - End-to-end portfolio analysis
  - Options trading workflows
  - Multi-leg strategy workflows
  - Error handling scenarios
  - Data consistency verification

### Standalone Function Tests
- **Function Exports** (`test_standalone_functions.py`)
  - All public API functions
  - Proper mock delegation
  - Function signature verification

## 🛠️ Running Tests

### Quick Start
```bash
# Run all tests
python run_tests.py

# Or use pytest directly
pytest tests/ -v
```

### Specific Test Categories
```bash
# Run only unit tests
pytest tests/ -v -m "not integration"

# Run only integration tests
pytest tests/test_integration.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_portfolio_analysis.py -v
```

### Test Options
```bash
# Verbose output
pytest tests/ -v

# Show test durations
pytest tests/ --durations=10

# Stop on first failure
pytest tests/ -x

# Run failed tests only
pytest tests/ --lf

# Run with specific markers
pytest tests/ -m "unit"
```

## 📊 Test Coverage

The test suite covers:

- **API Calls**: All Alpaca API interactions are mocked
- **Data Models**: Position, OptionContract, and configuration objects
- **Error Handling**: API failures, invalid inputs, edge cases
- **Business Logic**: Risk calculations, position sizing, strategy validation
- **Integration**: End-to-end workflows and data consistency

## 🎯 Key Test Scenarios

### Portfolio Analysis
- ✅ Account information retrieval
- ✅ Position list processing
- ✅ P&L calculations
- ✅ Concentration analysis
- ✅ Risk level assignments
- ✅ Empty portfolio handling
- ✅ API error handling

### Options Trading
- ✅ Current price fetching
- ✅ Options contract screening
- ✅ Market and limit orders
- ✅ Position closing
- ✅ Multi-leg strategy creation
- ✅ Strategy validation
- ✅ Order error handling

### Risk Management
- ✅ Buying power validation
- ✅ Position risk calculation
- ✅ Trade approval logic
- ✅ Portfolio concentration limits
- ✅ Position concentration limits
- ✅ Risk level assignments
- ✅ Portfolio diversification scoring

### Integration
- ✅ Complete trading workflows
- ✅ Data consistency across modules
- ✅ Error propagation
- ✅ Standalone function integration
- ✅ Performance metrics tracking

## 🔧 Test Configuration

### Fixtures (`conftest.py`)
- **Mock Trading Configuration**: API keys and endpoints
- **Mock Alpaca Clients**: Trading, stock data, and options data clients
- **Mock Data**: Account info, positions, quotes, orders
- **Environment Setup**: Test environment variables

### Pytest Configuration (`pytest.ini`)
- Test discovery patterns
- Output formatting
- Warning suppression
- Custom markers

## 🚨 Test Dependencies

Required packages for testing:
```bash
pytest>=7.0.0
pytest-cov>=4.0.0
alpaca-py>=0.30.0
pandas>=1.5.0
numpy>=1.21.0
pydantic>=2.0.0
python-dotenv>=0.19.0
```

## 📝 Writing New Tests

### Test Naming Convention
```python
def test_function_name_scenario(self):
    """Test description"""
    # Arrange
    # Act
    # Assert
```

### Using Fixtures
```python
def test_with_fixture(self, trading_tools_with_mocks, mock_account_info):
    """Test using fixtures"""
    trading_tools = trading_tools_with_mocks
    trading_tools.trading_client.get_account.return_value = mock_account_info

    result = trading_tools.get_account_info()
    assert result["account_id"] == "test_account_id"
```

### Mocking API Calls
```python
def test_api_call_mocking(self, trading_tools_with_mocks):
    """Test with mocked API calls"""
    trading_tools.trading_client.submit_order.return_value = Mock(id="order_123")

    result = trading_tools.buy_option_contract("SYMBOL", 1)
    assert result["order_id"] == "order_123"
```

## 🐛 Debugging Tests

### Running Tests in Debug Mode
```bash
# Run with pdb debugger
pytest tests/ --pdb

# Run specific test in debug mode
pytest tests/test_portfolio_analysis.py::TestPortfolioAnalysis::test_get_account_info_success --pdb
```

### Print Debug Information
```python
def test_debug_example(self, trading_tools_with_mocks):
    """Test with debug output"""
    result = trading_tools.get_account_info()
    print(f"Debug: {result}")
    assert "account_id" in result
```

### Test Output
- Use `-v` flag for verbose output
- Use `-s` flag to see print statements
- Use `--tb=short` for concise tracebacks

## 📈 Continuous Integration

These tests are designed to run in CI/CD environments:
- ✅ No external API dependencies (all mocked)
- ✅ Deterministic results
- ✅ Fast execution
- ✅ Clear error reporting
- ✅ Coverage reporting support

## 🔍 Test Data

All test data is mocked to ensure:
- **Consistency**: Same data across test runs
- **Speed**: No network latency
- **Reliability**: No external service dependencies
- **Privacy**: No real account data exposure

## 🎉 Best Practices

1. **Mock Everything**: All external API calls should be mocked
2. **Test Edge Cases**: Include error conditions and boundary values
3. **Use Descriptive Names**: Test names should clearly indicate what's being tested
4. **Arrange-Act-Assert**: Structure tests clearly
5. **One Assertion Per Test**: Keep tests focused
6. **Cleanup After Tests**: Use fixtures and teardown methods
7. **Test Documentation**: Include docstrings explaining test purpose

## 📞 Support

If you encounter issues with the tests:
1. Check that all dependencies are installed
2. Verify you're running from the project root
3. Ensure environment variables are set (use .env for testing)
4. Check the pytest configuration in `pytest.ini`
5. Run the test runner script: `python run_tests.py`