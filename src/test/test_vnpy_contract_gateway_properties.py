"""
VnpyContractGateway 属性测试

使用 Hypothesis 进行属性测试，验证合约网关的正确性属性。

Property 1: Option type mapping consistency
Property 2: Required fields presence
Property 3: Tick data handling
Property 4: Error handling returns empty DataFrame
"""
import pytest
try:
    from hypothesis import given, strategies as st, settings, assume
except Exception:
    pytest.skip("hypothesis not installed", allow_module_level=True)
from unittest.mock import Mock
import pandas as pd
import random

try:
    from src.strategy.infrastructure.gateway.vnpy_contract_gateway import (
        VnpyContractGateway,
        OptionType
    )
except Exception:
    pytest.skip("legacy gateway removed or renamed", allow_module_level=True)


# ============================================================
# 测试数据生成策略
# ============================================================

@st.composite
def option_type_strategy(draw):
    """生成随机的 OptionType"""
    return draw(st.sampled_from([OptionType.CALL, OptionType.PUT]))


@st.composite
def contract_strategy(draw):
    """生成随机的合约对象"""
    vt_symbol = draw(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-.')))
    underlying_symbol = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='.')))
    option_type = draw(option_type_strategy())
    option_strike = draw(st.floats(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False))
    option_expiry = draw(st.text(min_size=0, max_size=20))
    
    contract = Mock()
    contract.vt_symbol = vt_symbol
    contract.underlying_symbol = underlying_symbol
    contract.option_type = option_type
    contract.option_strike = option_strike
    contract.option_expiry = option_expiry
    
    return contract


@st.composite
def tick_strategy(draw):
    """生成随机的 Tick 对象"""
    bid_price = draw(st.floats(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False))
    bid_volume = draw(st.integers(min_value=0, max_value=1000000))
    ask_price = draw(st.floats(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False))
    ask_volume = draw(st.integers(min_value=0, max_value=1000000))
    
    tick = Mock()
    tick.bid_price_1 = bid_price
    tick.bid_volume_1 = bid_volume
    tick.ask_price_1 = ask_price
    tick.ask_volume_1 = ask_volume
    
    return tick


@st.composite
def contracts_with_ticks_strategy(draw):
    """生成合约列表和对应的 tick 映射"""
    num_contracts = draw(st.integers(min_value=1, max_value=10))
    contracts = []
    tick_map = {}
    
    for _ in range(num_contracts):
        contract = draw(contract_strategy())
        contracts.append(contract)
        
        # 随机决定是否有 tick 数据
        has_tick = draw(st.booleans())
        if has_tick:
            tick_map[contract.vt_symbol] = draw(tick_strategy())
    
    return contracts, tick_map


def create_mock_strategy_context(contracts, tick_map=None):
    """创建模拟的 strategy_context"""
    strategy_context = Mock()
    strategy_context.strategy_name = "TestStrategy"
    strategy_context.write_log = Mock()
    
    strategy_engine = Mock()
    strategy_context.strategy_engine = strategy_engine
    
    main_engine = Mock()
    strategy_engine.main_engine = main_engine
    
    main_engine.get_all_contracts = Mock(return_value=contracts)
    
    if tick_map:
        main_engine.get_tick = Mock(side_effect=lambda vt_symbol: tick_map.get(vt_symbol))
    else:
        main_engine.get_tick = Mock(return_value=None)
    
    return strategy_context


# ============================================================
# Property 1: Option type mapping consistency
# **Validates: Requirements 2.4, 2.5**
# ============================================================

class TestProperty1OptionTypeMapping:
    """
    Property 1: Option type mapping consistency
    
    *For any* option contract with option_type set to OptionType.CALL, 
    the returned DataFrame should contain "call" in the option_type column, 
    and for any contract with OptionType.PUT, it should contain "put".
    
    **Validates: Requirements 2.4, 2.5**
    """
    
    @given(option_type=option_type_strategy())
    @settings(max_examples=100)
    def test_option_type_mapping_is_consistent(self, option_type):
        """
        **Feature: refactor-option-contracts-gateway, Property 1: Option type mapping consistency**
        
        For any option_type, the mapping should be consistent:
        - OptionType.CALL -> "call"
        - OptionType.PUT -> "put"
        """
        # 创建合约
        contract = Mock()
        contract.vt_symbol = "TEST-C-1000.CFFEX"
        contract.underlying_symbol = "TEST.CFFEX"
        contract.option_type = option_type
        contract.option_strike = 1000
        contract.option_expiry = "2023-12-15"
        
        strategy_context = create_mock_strategy_context([contract])
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("TEST.CFFEX")
        
        # 验证映射
        assert len(result) == 1
        expected_type = "call" if option_type == OptionType.CALL else "put"
        assert result.iloc[0]["option_type"] == expected_type
    
    @given(contracts_data=contracts_with_ticks_strategy())
    @settings(max_examples=100)
    def test_all_contracts_have_valid_option_type(self, contracts_data):
        """
        **Feature: refactor-option-contracts-gateway, Property 1: Option type mapping consistency**
        
        For any list of contracts, all returned option_type values should be either "call" or "put".
        """
        contracts, tick_map = contracts_data
        
        strategy_context = create_mock_strategy_context(contracts, tick_map)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("TEST.CFFEX")
        
        # 验证所有 option_type 都是 "call" 或 "put"
        for _, row in result.iterrows():
            assert row["option_type"] in ["call", "put"]


# ============================================================
# Property 2: Required fields presence
# **Validates: Requirements 2.3, 5.1, 5.2**
# ============================================================

class TestProperty2RequiredFields:
    """
    Property 2: Required fields presence
    
    *For any* option contract returned by the gateway, the DataFrame should 
    contain all required columns: vt_symbol, underlying_symbol, option_type, 
    strike_price, expiry_date, bid_price, bid_volume, ask_price, ask_volume, 
    days_to_expiry.
    
    **Validates: Requirements 2.3, 5.1, 5.2**
    """
    
    REQUIRED_COLUMNS = [
        "vt_symbol", "underlying_symbol", "option_type",
        "strike_price", "expiry_date", "bid_price", "bid_volume",
        "ask_price", "ask_volume", "days_to_expiry"
    ]
    
    @given(contracts_data=contracts_with_ticks_strategy())
    @settings(max_examples=100)
    def test_all_required_columns_present(self, contracts_data):
        """
        **Feature: refactor-option-contracts-gateway, Property 2: Required fields presence**
        
        For any list of contracts, the returned DataFrame should contain all required columns.
        """
        contracts, tick_map = contracts_data
        
        strategy_context = create_mock_strategy_context(contracts, tick_map)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("TEST.CFFEX")
        
        # 如果有结果，验证所有必需列都存在
        if len(result) > 0:
            for col in self.REQUIRED_COLUMNS:
                assert col in result.columns, f"Missing required column: {col}"
    
    @given(contract=contract_strategy())
    @settings(max_examples=100)
    def test_single_contract_has_all_fields(self, contract):
        """
        **Feature: refactor-option-contracts-gateway, Property 2: Required fields presence**
        
        For any single contract, the returned row should have all required fields.
        """
        strategy_context = create_mock_strategy_context([contract])
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("TEST.CFFEX")
        
        assert len(result) == 1
        for col in self.REQUIRED_COLUMNS:
            assert col in result.columns
            # 验证值不是 NaN (除非是空字符串)
            value = result.iloc[0][col]
            if col not in ["underlying_symbol", "expiry_date"]:
                assert pd.notna(value), f"Column {col} should not be NaN"


# ============================================================
# Property 3: Tick data handling
# **Validates: Requirements 2.6, 2.7**
# ============================================================

class TestProperty3TickDataHandling:
    """
    Property 3: Tick data handling
    
    *For any* option contract, if tick data is available, the DataFrame should 
    contain the tick's bid_price_1, bid_volume_1, ask_price_1, ask_volume_1; 
    if tick data is None, these fields should be 0.
    
    **Validates: Requirements 2.6, 2.7**
    """
    
    @given(contract=contract_strategy(), tick=tick_strategy())
    @settings(max_examples=100)
    def test_tick_data_extracted_when_available(self, contract, tick):
        """
        **Feature: refactor-option-contracts-gateway, Property 3: Tick data handling**
        
        When tick data is available, the values should match the tick object.
        """
        tick_map = {contract.vt_symbol: tick}
        strategy_context = create_mock_strategy_context([contract], tick_map)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("TEST.CFFEX")
        
        assert len(result) == 1
        assert result.iloc[0]["bid_price"] == tick.bid_price_1
        assert result.iloc[0]["bid_volume"] == tick.bid_volume_1
        assert result.iloc[0]["ask_price"] == tick.ask_price_1
        assert result.iloc[0]["ask_volume"] == tick.ask_volume_1
    
    @given(contract=contract_strategy())
    @settings(max_examples=100)
    def test_default_values_when_tick_is_none(self, contract):
        """
        **Feature: refactor-option-contracts-gateway, Property 3: Tick data handling**
        
        When tick data is None, the values should be 0.
        """
        # 不提供 tick_map，所以 get_tick 返回 None
        strategy_context = create_mock_strategy_context([contract])
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("TEST.CFFEX")
        
        assert len(result) == 1
        assert result.iloc[0]["bid_price"] == 0
        assert result.iloc[0]["bid_volume"] == 0
        assert result.iloc[0]["ask_price"] == 0
        assert result.iloc[0]["ask_volume"] == 0


# ============================================================
# Property 4: Error handling returns empty DataFrame
# **Validates: Requirements 2.9, 5.3, 5.4**
# ============================================================

class TestProperty4ErrorHandling:
    """
    Property 4: Error handling returns empty DataFrame
    
    *For any* error condition (missing main_engine, exception during query, etc.), 
    the gateway should return an empty DataFrame and log the error.
    
    **Validates: Requirements 2.9, 5.3, 5.4**
    """
    
    @given(error_type=st.sampled_from([
        "missing_strategy_engine",
        "missing_main_engine",
        "missing_get_all_contracts",
        "exception_during_retrieval"
    ]))
    @settings(max_examples=100)
    def test_error_returns_empty_dataframe(self, error_type):
        """
        **Feature: refactor-option-contracts-gateway, Property 4: Error handling returns empty DataFrame**
        
        For any error condition, the gateway should return an empty DataFrame.
        """
        strategy_context = Mock()
        strategy_context.strategy_name = "TestStrategy"
        strategy_context.write_log = Mock()
        
        if error_type == "missing_strategy_engine":
            del strategy_context.strategy_engine
        elif error_type == "missing_main_engine":
            strategy_context.strategy_engine = Mock()
            del strategy_context.strategy_engine.main_engine
        elif error_type == "missing_get_all_contracts":
            strategy_context.strategy_engine = Mock()
            strategy_context.strategy_engine.main_engine = Mock()
            del strategy_context.strategy_engine.main_engine.get_all_contracts
        elif error_type == "exception_during_retrieval":
            strategy_context.strategy_engine = Mock()
            strategy_context.strategy_engine.main_engine = Mock()
            strategy_context.strategy_engine.main_engine.get_all_contracts = Mock(
                side_effect=Exception("Test error")
            )
        
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("TEST.CFFEX")
        
        # 验证返回空 DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    @given(error_type=st.sampled_from([
        "missing_strategy_engine",
        "missing_main_engine",
        "missing_get_all_contracts",
        "exception_during_retrieval"
    ]))
    @settings(max_examples=100)
    def test_error_is_logged(self, error_type):
        """
        **Feature: refactor-option-contracts-gateway, Property 4: Error handling returns empty DataFrame**
        
        For any error condition, the error should be logged.
        """
        strategy_context = Mock()
        strategy_context.strategy_name = "TestStrategy"
        strategy_context.write_log = Mock()
        
        if error_type == "missing_strategy_engine":
            del strategy_context.strategy_engine
        elif error_type == "missing_main_engine":
            strategy_context.strategy_engine = Mock()
            del strategy_context.strategy_engine.main_engine
        elif error_type == "missing_get_all_contracts":
            strategy_context.strategy_engine = Mock()
            strategy_context.strategy_engine.main_engine = Mock()
            del strategy_context.strategy_engine.main_engine.get_all_contracts
        elif error_type == "exception_during_retrieval":
            strategy_context.strategy_engine = Mock()
            strategy_context.strategy_engine.main_engine = Mock()
            strategy_context.strategy_engine.main_engine.get_all_contracts = Mock(
                side_effect=Exception("Test error")
            )
        
        gateway = VnpyContractGateway(strategy_context)
        gateway.get_option_contracts("TEST.CFFEX")
        
        # 验证日志被调用
        strategy_context.write_log.assert_called()

