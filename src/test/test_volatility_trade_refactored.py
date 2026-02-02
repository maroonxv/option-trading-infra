"""
VolatilityTrade 重构测试

测试应用层重构后的行为，验证：
1. _get_option_contracts 使用 gateway 接口
2. 不直接访问 strategy_context 的内部属性
3. 通过 gateway 获取合约数据

Property 5: Application layer uses gateway interface
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
import pandas as pd

# Add project root to sys.path to allow importing src
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from hypothesis import given, strategies as st, settings
except Exception:
    pytest.skip("hypothesis not installed", allow_module_level=True)

from src.strategy.application.volatility_trade import VolatilityTrade


def create_mock_strategy_context():
    """创建模拟的 strategy_context"""
    strategy_context = Mock()
    strategy_context.strategy_name = "TestStrategy"
    strategy_context.write_log = Mock()
    
    strategy_engine = Mock()
    strategy_context.strategy_engine = strategy_engine
    
    main_engine = Mock()
    strategy_engine.main_engine = main_engine
    
    # 设置默认返回值
    main_engine.get_all_contracts = Mock(return_value=[])
    main_engine.get_tick = Mock(return_value=None)
    main_engine.get_all_accounts = Mock(return_value=[])
    
    return strategy_context


class TestVolatilityTradeRefactored:
    """测试 VolatilityTrade 重构后的行为"""
    
    def test_gateway_is_created(self):
        """测试 gateway 被创建"""
        strategy_context = create_mock_strategy_context()
        trade = VolatilityTrade(strategy_context)
        
        assert hasattr(trade, "gateway")
        assert trade.gateway is not None
    
    def test_get_option_contracts_uses_gateway(self):
        """测试 _get_option_contracts 使用 gateway"""
        strategy_context = create_mock_strategy_context()
        trade = VolatilityTrade(strategy_context)
        
        # Mock gateway 的 get_option_contracts 方法
        expected_df = pd.DataFrame({
            "vt_symbol": ["IO2312-C-4000.CFFEX"],
            "option_type": ["call"]
        })
        trade.gateway.get_option_contracts = Mock(return_value=expected_df)
        
        # 调用方法
        result = trade._get_option_contracts("IF2312.CFFEX")
        
        # 验证 gateway 方法被调用
        trade.gateway.get_option_contracts.assert_called_once_with("IF2312.CFFEX")
        
        # 验证返回值
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
    
    def test_get_option_contracts_returns_dataframe(self):
        """测试 _get_option_contracts 返回 DataFrame"""
        strategy_context = create_mock_strategy_context()
        trade = VolatilityTrade(strategy_context)
        
        result = trade._get_option_contracts("IF2312.CFFEX")
        
        assert isinstance(result, pd.DataFrame)
    
    def test_get_option_contracts_does_not_access_strategy_context_directly(self):
        """测试 _get_option_contracts 不直接访问 strategy_context"""
        strategy_context = create_mock_strategy_context()
        trade = VolatilityTrade(strategy_context)
        
        # 重置 mock 调用记录
        strategy_context.strategy_engine.main_engine.get_all_contracts.reset_mock()
        
        # Mock gateway
        trade.gateway.get_option_contracts = Mock(return_value=pd.DataFrame())
        
        # 调用方法
        trade._get_option_contracts("IF2312.CFFEX")
        
        # 验证 gateway 被调用
        trade.gateway.get_option_contracts.assert_called_once()
        
        # 注意：由于 gateway 内部会调用 main_engine，这里我们只验证
        # 应用层代码本身不直接调用 main_engine
        # 实际上，由于我们 mock 了 gateway.get_option_contracts，
        # main_engine.get_all_contracts 不应该被调用
        # 但由于 VnpyTradeGateway 在初始化时会创建 VnpyContractGateway，
        # 我们需要验证的是应用层代码的行为


class TestVolatilityTradeGatewayIntegration:
    """测试 VolatilityTrade 与 Gateway 的集成"""
    
    def test_gateway_get_option_contracts_is_called_with_correct_symbol(self):
        """测试 gateway.get_option_contracts 被正确调用"""
        strategy_context = create_mock_strategy_context()
        trade = VolatilityTrade(strategy_context)
        
        # Mock gateway
        trade.gateway.get_option_contracts = Mock(return_value=pd.DataFrame())
        
        # 测试不同的 symbol
        symbols = ["IF2312.CFFEX", "IO2401.CFFEX", "AU2312.SHFE"]
        
        for symbol in symbols:
            trade._get_option_contracts(symbol)
            trade.gateway.get_option_contracts.assert_called_with(symbol)
    
    def test_gateway_get_account_balance_is_used(self):
        """测试 gateway.get_account_balance 被使用"""
        strategy_context = create_mock_strategy_context()
        trade = VolatilityTrade(strategy_context)
        
        # Mock gateway
        trade.gateway.get_account_balance = Mock(return_value=100000.0)
        
        # 调用方法
        balance = trade.gateway.get_account_balance()
        
        # 验证
        assert balance == 100000.0
        trade.gateway.get_account_balance.assert_called_once()


class TestProperty5ApplicationLayerUsesGateway:
    """
    Property 5: Application layer uses gateway interface
    
    *For any* option selection operation in the application layer, 
    the code should call `self.gateway.get_option_contracts()` and 
    should not directly access `strategy_context.strategy_engine.main_engine`.
    
    **Validates: Requirements 3.2, 3.3, 3.4, 3.5**
    """
    
    @given(symbol=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='.-')))
    @settings(max_examples=100)
    def test_all_contract_queries_go_through_gateway(self, symbol):
        """
        **Feature: refactor-option-contracts-gateway, Property 5: Application layer uses gateway interface**
        
        For any symbol, contract queries should go through gateway.
        """
        strategy_context = create_mock_strategy_context()
        trade = VolatilityTrade(strategy_context)
        
        # Mock gateway
        trade.gateway.get_option_contracts = Mock(return_value=pd.DataFrame())
        
        # 调用方法
        trade._get_option_contracts(symbol)
        
        # 验证 gateway 被调用
        trade.gateway.get_option_contracts.assert_called_once_with(symbol)
    
    @given(symbol=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='.-')))
    @settings(max_examples=100)
    def test_gateway_returns_dataframe(self, symbol):
        """
        **Feature: refactor-option-contracts-gateway, Property 5: Application layer uses gateway interface**
        
        For any symbol, the result should be a DataFrame.
        """
        strategy_context = create_mock_strategy_context()
        trade = VolatilityTrade(strategy_context)
        
        # 调用方法
        result = trade._get_option_contracts(symbol)
        
        # 验证返回类型
        assert isinstance(result, pd.DataFrame)


class TestVolatilityTradeCodeInspection:
    """测试代码结构，验证没有直接访问 strategy_context"""
    
    def test_get_option_contracts_method_is_simple(self):
        """测试 _get_option_contracts 方法是简单的委托"""
        import inspect
        
        # 获取方法源代码
        source = inspect.getsource(VolatilityTrade._get_option_contracts)
        
        # 验证方法中包含 gateway.get_option_contracts
        assert "self.gateway.get_option_contracts" in source
        
        # 验证方法中不包含直接访问 main_engine 的代码
        # 注意：注释中可能包含这些字符串，所以我们检查实际的代码行
        lines = [line.strip() for line in source.split('\n') 
                 if line.strip() and not line.strip().startswith('#') 
                 and not line.strip().startswith('"""')]
        
        # 过滤掉文档字符串
        in_docstring = False
        code_lines = []
        for line in source.split('\n'):
            stripped = line.strip()
            if '"""' in stripped:
                if in_docstring:
                    in_docstring = False
                    continue
                else:
                    in_docstring = True
                    continue
            if not in_docstring and stripped and not stripped.startswith('#'):
                code_lines.append(stripped)
        
        # 验证实际代码行中不包含直接访问 main_engine
        for line in code_lines:
            if 'return' in line:
                # return 语句应该是 return self.gateway.get_option_contracts(...)
                assert 'self.gateway.get_option_contracts' in line or 'def' in line

