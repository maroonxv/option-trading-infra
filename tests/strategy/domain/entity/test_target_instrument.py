"""
Property-Based Tests for TargetInstrument Entity

Tests the anemic model design of TargetInstrument, specifically:
- Property 2: TargetInstrument indicators dictionary is writable
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
from typing import Any, Dict

from src.strategy.domain.entity.target_instrument import TargetInstrument


class TestTargetInstrumentProperties:
    """Property-based tests for TargetInstrument"""
    
    @settings(max_examples=100)
    @given(
        vt_symbol=st.text(min_size=1, max_size=20),
        key=st.text(min_size=1, max_size=50),
        value=st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(),
            st.booleans(),
            st.none(),
            st.dictionaries(st.text(min_size=1, max_size=10), st.integers()),
            st.lists(st.integers())
        )
    )
    def test_property_indicators_dict_writable(
        self, 
        vt_symbol: str, 
        key: str, 
        value: Any
    ):
        """
        Property 2: TargetInstrument indicators 字典可写入
        
        For any TargetInstrument instance and any key-value pair,
        the indicators dictionary should support dynamic write and read operations.
        
        Validates: Requirements 1.5
        """
        # Create a TargetInstrument instance
        instrument = TargetInstrument(vt_symbol=vt_symbol)
        
        # Write to indicators dictionary
        instrument.indicators[key] = value
        
        # Verify the value can be read back
        assert key in instrument.indicators
        assert instrument.indicators[key] == value
    
    @settings(max_examples=100)
    @given(
        vt_symbol=st.text(min_size=1, max_size=20),
        indicators_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.text(),
                st.dictionaries(
                    st.text(min_size=1, max_size=10),
                    st.floats(allow_nan=False, allow_infinity=False)
                )
            ),
            min_size=0,
            max_size=10
        )
    )
    def test_property_indicators_dict_multiple_writes(
        self,
        vt_symbol: str,
        indicators_data: Dict[str, Any]
    ):
        """
        Property 2 (Extended): Multiple indicator writes should all be preserved
        
        For any TargetInstrument instance and multiple key-value pairs,
        all writes to the indicators dictionary should be preserved.
        
        Validates: Requirements 1.5
        """
        # Create a TargetInstrument instance
        instrument = TargetInstrument(vt_symbol=vt_symbol)
        
        # Write multiple indicators
        for key, value in indicators_data.items():
            instrument.indicators[key] = value
        
        # Verify all values are preserved
        assert len(instrument.indicators) == len(indicators_data)
        for key, value in indicators_data.items():
            assert key in instrument.indicators
            assert instrument.indicators[key] == value
    
    @settings(max_examples=100)
    @given(
        vt_symbol=st.text(min_size=1, max_size=20),
        key=st.text(min_size=1, max_size=50),
        initial_value=st.integers(),
        updated_value=st.integers()
    )
    def test_property_indicators_dict_update(
        self,
        vt_symbol: str,
        key: str,
        initial_value: int,
        updated_value: int
    ):
        """
        Property 2 (Extended): Indicator values can be updated
        
        For any TargetInstrument instance, indicator values should be updatable.
        
        Validates: Requirements 1.5
        """
        # Create a TargetInstrument instance
        instrument = TargetInstrument(vt_symbol=vt_symbol)
        
        # Write initial value
        instrument.indicators[key] = initial_value
        assert instrument.indicators[key] == initial_value
        
        # Update the value
        instrument.indicators[key] = updated_value
        assert instrument.indicators[key] == updated_value


class TestTargetInstrumentBasicFunctionality:
    """Unit tests for basic TargetInstrument functionality"""
    
    def test_initialization(self):
        """Test basic initialization"""
        instrument = TargetInstrument(vt_symbol="rb2501.SHFE")
        
        assert instrument.vt_symbol == "rb2501.SHFE"
        assert instrument.bars.empty
        assert len(instrument.indicators) == 0
        assert instrument.last_update_time is None
    
    def test_append_bar(self):
        """Test appending bar data"""
        instrument = TargetInstrument(vt_symbol="rb2501.SHFE")
        
        bar_data = {
            "datetime": datetime(2025, 1, 1, 9, 0),
            "open": 3500.0,
            "high": 3520.0,
            "low": 3490.0,
            "close": 3510.0,
            "volume": 1000
        }
        
        instrument.append_bar(bar_data)
        
        assert len(instrument.bars) == 1
        assert instrument.latest_close == 3510.0
        assert instrument.latest_high == 3520.0
        assert instrument.latest_low == 3490.0
    
    def test_indicators_dict_complex_structure(self):
        """Test storing complex indicator structures"""
        instrument = TargetInstrument(vt_symbol="rb2501.SHFE")
        
        # Store MACD-like indicator
        instrument.indicators['macd'] = {
            'dif': 0.5,
            'dea': 0.3,
            'macd_bar': 0.2
        }
        
        # Store EMA-like indicator
        instrument.indicators['ema'] = {
            'fast': 3500.0,
            'slow': 3480.0
        }
        
        # Store TD-like indicator
        instrument.indicators['td'] = {
            'count': 5,
            'setup': True
        }
        
        # Verify all indicators are stored correctly
        assert instrument.indicators['macd']['dif'] == 0.5
        assert instrument.indicators['ema']['fast'] == 3500.0
        assert instrument.indicators['td']['count'] == 5
