"""
Tests for tool parameter normalization and validation.
This ensures LLM-generated parameter names are correctly mapped to function signatures.
"""

import sys
from pathlib import Path
import pytest

# Add src to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from agent import _normalize_tool_parameters, _normalize_side_value


class TestSideValueNormalization:
    """Test side value normalization (Long/Short -> buy/sell)"""
    
    def test_buy_variants(self):
        """Test various buy side representations"""
        assert _normalize_side_value("buy") == "buy"
        assert _normalize_side_value("Buy") == "buy"
        assert _normalize_side_value("BUY") == "buy"
        assert _normalize_side_value("long") == "buy"
        assert _normalize_side_value("Long") == "buy"
        assert _normalize_side_value("LONG") == "buy"
        assert _normalize_side_value("b") == "buy"
        assert _normalize_side_value("l") == "buy"
        assert _normalize_side_value("purchase") == "buy"
    
    def test_sell_variants(self):
        """Test various sell side representations"""
        assert _normalize_side_value("sell") == "sell"
        assert _normalize_side_value("Sell") == "sell"
        assert _normalize_side_value("SELL") == "sell"
        assert _normalize_side_value("short") == "sell"
        assert _normalize_side_value("Short") == "sell"
        assert _normalize_side_value("SHORT") == "sell"
        assert _normalize_side_value("s") == "sell"
    
    def test_none_defaults_to_buy(self):
        """Test that None defaults to buy"""
        assert _normalize_side_value(None) == "buy"
    
    def test_unknown_defaults_to_buy(self):
        """Test that unknown values default to buy with warning"""
        assert _normalize_side_value("unknown") == "buy"
        assert _normalize_side_value("") == "buy"


class TestPlaceOptionOrderNormalization:
    """Test parameter normalization for place_option_order"""
    
    def test_camelcase_to_snakecase(self):
        """Test camelCase parameter names are converted to snake_case"""
        raw = {
            "orderType": "MarketOrder",
            "qty": "1.0",
            "side": "Long",
            "symbol": "SPY",
            "timeInForce": "Day",
            "transactTime": "get_current_datetime"
        }
        normalized = _normalize_tool_parameters("place_option_order", raw)
        
        assert "order_type" in normalized
        assert normalized["order_type"] == "MarketOrder"
        assert "quantity" in normalized
        assert normalized["quantity"] == 1  # Should be converted to int
        assert "side" in normalized
        assert normalized["side"] == "buy"  # Long -> buy
        assert "symbol" in normalized
        assert normalized["symbol"] == "SPY"
        assert "time_in_force" in normalized
        assert normalized["time_in_force"] == "Day"
        # Invalid parameter should be removed
        assert "transactTime" not in normalized
        assert "transact_time" not in normalized
    
    def test_snakecase_preserved(self):
        """Test that snake_case parameters are preserved"""
        raw = {
            "order_type": "market",
            "quantity": 2,
            "side": "buy",
            "symbol": "AAPL",
            "time_in_force": "day"
        }
        normalized = _normalize_tool_parameters("place_option_order", raw)
        
        assert normalized == raw
    
    def test_mixed_naming(self):
        """Test mixed camelCase and snake_case"""
        raw = {
            "orderType": "limit",
            "quantity": 3,
            "limitPrice": 1.50,
            "side": "sell",
            "symbol": "TSLA"
        }
        normalized = _normalize_tool_parameters("place_option_order", raw)
        
        assert normalized["order_type"] == "limit"
        assert normalized["quantity"] == 3
        assert normalized["limit_price"] == 1.50
        assert normalized["side"] == "sell"
        assert normalized["symbol"] == "TSLA"
    
    def test_quantity_type_conversion(self):
        """Test quantity is converted to int from string/float"""
        raw1 = {"symbol": "SPY", "side": "buy", "quantity": "1.0"}
        norm1 = _normalize_tool_parameters("place_option_order", raw1)
        assert norm1["quantity"] == 1
        assert isinstance(norm1["quantity"], int)
        
        raw2 = {"symbol": "SPY", "side": "buy", "quantity": 2.5}
        norm2 = _normalize_tool_parameters("place_option_order", raw2)
        assert norm2["quantity"] == 2
        assert isinstance(norm2["quantity"], int)
        
        raw3 = {"symbol": "SPY", "side": "buy", "qty": "3"}
        norm3 = _normalize_tool_parameters("place_option_order", raw3)
        assert norm3["quantity"] == 3
        assert isinstance(norm3["quantity"], int)
    
    def test_order_type_normalization(self):
        """Test order_type values are normalized"""
        raw1 = {"symbol": "SPY", "side": "buy", "quantity": 1, "orderType": "MarketOrder"}
        norm1 = _normalize_tool_parameters("place_option_order", raw1)
        assert norm1["order_type"] == "market"
        
        raw2 = {"symbol": "SPY", "side": "buy", "quantity": 1, "order_type": "limit"}
        norm2 = _normalize_tool_parameters("place_option_order", raw2)
        assert norm2["order_type"] == "limit"
    
    def test_missing_required_parameters(self):
        """Test that missing required parameters raise ValueError"""
        # Missing symbol
        with pytest.raises(ValueError, match="missing required arguments.*symbol"):
            _normalize_tool_parameters("place_option_order", {"side": "buy", "quantity": 1})
        
        # Missing side
        with pytest.raises(ValueError, match="missing required arguments.*side"):
            _normalize_tool_parameters("place_option_order", {"symbol": "SPY", "quantity": 1})
        
        # Missing quantity
        with pytest.raises(ValueError, match="missing required arguments.*quantity"):
            _normalize_tool_parameters("place_option_order", {"symbol": "SPY", "side": "buy"})
        
        # All missing
        with pytest.raises(ValueError):
            _normalize_tool_parameters("place_option_order", {})
    
    def test_invalid_quantity_raises_error(self):
        """Test that invalid quantity values raise ValueError"""
        with pytest.raises(ValueError, match="Invalid quantity value"):
            _normalize_tool_parameters("place_option_order", {
                "symbol": "SPY",
                "side": "buy",
                "quantity": "invalid"
            })


class TestPlaceMultiLegOptionOrderNormalization:
    """Test parameter normalization for place_multi_leg_option_order"""
    
    def test_basic_normalization(self):
        """Test basic parameter normalization"""
        raw = {
            "orderType": "MarketOrder",
            "qty": "2",
            "legs": [
                {"symbol": "SPY241220C00450000", "side": "buy", "ratio_qty": 1},
                {"symbol": "SPY241220C00451000", "side": "sell", "ratio_qty": 1}
            ]
        }
        normalized = _normalize_tool_parameters("place_multi_leg_option_order", raw)
        
        assert normalized["order_type"] == "market"
        assert normalized["quantity"] == 2
        assert len(normalized["legs"]) == 2
        assert normalized["legs"][0]["side"] == "buy"
        assert normalized["legs"][1]["side"] == "sell"
    
    def test_leg_side_normalization(self):
        """Test that leg side values are normalized"""
        raw = {
            "legs": [
                {"symbol": "SPY241220C00450000", "side": "Long"},
                {"symbol": "SPY241220C00451000", "side": "Short"}
            ],
            "quantity": 1
        }
        normalized = _normalize_tool_parameters("place_multi_leg_option_order", raw)
        
        assert normalized["legs"][0]["side"] == "buy"
        assert normalized["legs"][1]["side"] == "sell"
    
    def test_missing_required_parameters(self):
        """Test that missing required parameters raise ValueError"""
        # Missing legs
        with pytest.raises(ValueError, match="missing required arguments.*legs"):
            _normalize_tool_parameters("place_multi_leg_option_order", {"quantity": 1})
        
        # Missing quantity
        with pytest.raises(ValueError, match="missing required arguments.*quantity"):
            _normalize_tool_parameters("place_multi_leg_option_order", {
                "legs": [{"symbol": "SPY", "side": "buy"}]
            })
        
        # Empty legs list
        with pytest.raises(ValueError, match="requires 'legs' to be a non-empty list"):
            _normalize_tool_parameters("place_multi_leg_option_order", {
                "legs": [],
                "quantity": 1
            })
    
    def test_invalid_legs_structure(self):
        """Test that invalid leg structures raise ValueError"""
        # Legs not a list
        with pytest.raises(ValueError, match="Each leg must be a dictionary"):
            _normalize_tool_parameters("place_multi_leg_option_order", {
                "legs": "not a list",
                "quantity": 1
            })
        
        # Leg missing symbol
        with pytest.raises(ValueError, match="Each leg must have a 'symbol' field"):
            _normalize_tool_parameters("place_multi_leg_option_order", {
                "legs": [{"side": "buy"}],
                "quantity": 1
            })
        
        # Leg missing side
        with pytest.raises(ValueError, match="Each leg must have a 'side' field"):
            _normalize_tool_parameters("place_multi_leg_option_order", {
                "legs": [{"symbol": "SPY"}],
                "quantity": 1
            })
    
    def test_empty_dict_raises_error(self):
        """Test that empty dict raises appropriate error"""
        with pytest.raises(ValueError):
            _normalize_tool_parameters("place_multi_leg_option_order", {})


class TestCloseOptionPositionNormalization:
    """Test parameter normalization for close_option_position"""
    
    def test_basic_normalization(self):
        """Test basic parameter normalization"""
        raw = {"symbol": "SPY241220C00450000", "qty": "1"}
        normalized = _normalize_tool_parameters("close_option_position", raw)
        
        assert normalized["symbol"] == "SPY241220C00450000"
        assert normalized["quantity"] == 1
    
    def test_missing_required_parameters(self):
        """Test that missing symbol raises ValueError"""
        with pytest.raises(ValueError, match="missing required arguments.*symbol"):
            _normalize_tool_parameters("close_option_position", {"quantity": 1})


class TestGetOptionContractsNormalization:
    """Test parameter normalization for get_option_contracts"""
    
    def test_parameter_aliases(self):
        """Test that parameter aliases are mapped correctly"""
        raw = {
            "underlying": "SPY",
            "type": "call",
            "expiration_after": "2024-07-01",
            "strike_gte": 450.0
        }
        normalized = _normalize_tool_parameters("get_option_contracts", raw)
        
        assert normalized["underlying_symbol"] == "SPY"
        assert normalized["contract_type"] == "call"
        assert normalized["expiration_date_gte"] == "2024-07-01"
        assert normalized["strike_price_gte"] == 450.0


class TestGetOptionsChainNormalization:
    """Test parameter normalization for get_options_chain"""
    
    def test_parameter_aliases(self):
        """Test that parameter aliases are mapped correctly"""
        raw = {
            "underlying": "SPY",
            "expiration": "2024-08-16",
            "type": "call"
        }
        normalized = _normalize_tool_parameters("get_options_chain", raw)
        
        assert normalized["underlying_symbol"] == "SPY"
        assert normalized["expiration_date"] == "2024-08-16"
        assert normalized["contract_type"] == "call"


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_non_dict_input(self):
        """Test that non-dict input returns empty dict"""
        result = _normalize_tool_parameters("place_option_order", None)
        assert result == {}
        
        result = _normalize_tool_parameters("place_option_order", "not a dict")
        assert result == {}
    
    def test_unknown_function_passes_through(self):
        """Test that unknown functions pass parameters through"""
        raw = {"param1": "value1", "param2": 2}
        normalized = _normalize_tool_parameters("unknown_function", raw)
        # Should pass through unchanged (no mappings defined)
        assert normalized == raw
    
    def test_extra_parameters_preserved(self):
        """Test that unmapped parameters are preserved"""
        raw = {
            "symbol": "SPY",
            "side": "buy",
            "quantity": 1,
            "extra_param": "extra_value"
        }
        normalized = _normalize_tool_parameters("place_option_order", raw)
        
        assert "extra_param" in normalized
        assert normalized["extra_param"] == "extra_value"


class TestRealWorldScenarios:
    """Test real-world scenarios from error logs"""
    
    def test_error_from_log_1(self):
        """Test the exact error from the log: orderType, qty, side: Long, transactTime"""
        raw = {
            "orderType": "MarketOrder",
            "qty": "1.0",
            "side": "Long",
            "symbol": "SPY",
            "timeInForce": "Day",
            "transactTime": "get_current_datetime"
        }
        normalized = _normalize_tool_parameters("place_option_order", raw)
        
        # Should normalize correctly
        assert normalized["order_type"] == "market"
        assert normalized["quantity"] == 1
        assert normalized["side"] == "buy"
        assert normalized["symbol"] == "SPY"
        assert normalized["time_in_force"] == "Day"
        # Invalid parameter should be removed
        assert "transactTime" not in normalized
    
    def test_error_from_log_2(self):
        """Test the exact error from the log: empty dict for multi-leg"""
        raw = {}
        with pytest.raises(ValueError):
            _normalize_tool_parameters("place_multi_leg_option_order", raw)
        
        # Should provide helpful error message
        try:
            _normalize_tool_parameters("place_multi_leg_option_order", raw)
        except ValueError as e:
            assert "legs" in str(e)
            assert "quantity" in str(e)

