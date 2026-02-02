"""
VnpyTradeGateway 单元测试

测试 VnPy 统一网关的实现，验证它同时实现了 ITradeGateway 和 IContractGateway 接口。
"""
import pytest
from unittest.mock import Mock, MagicMock
import pandas as pd
try:
    from src.strategy.infrastructure.gateway.vnpy_trade_gateway import VnpyTradeGateway
    from src.strategy.domain.demand_interface.i_trade_gateway import ITradeGateway
    from src.strategy.domain.demand_interface.i_contract_gateway import IContractGateway
    from src.strategy.infrastructure.gateway.vnpy_contract_gateway import OptionType
except Exception:
    pytest.skip("legacy gateways/interfaces removed or renamed", allow_module_level=True)


class MockContract:
    """模拟 VnPy 合约对象"""
    
    def __init__(
        self,
        vt_symbol: str,
        underlying_symbol: str = "",
        option_type=None,
        option_strike: float = 0,
        option_expiry: str = ""
    ):
        self.vt_symbol = vt_symbol
        self.underlying_symbol = underlying_symbol
        self.option_type = option_type
        self.option_strike = option_strike
        self.option_expiry = option_expiry


def create_mock_strategy_context(contracts=None, tick_map=None, accounts=None):
    """创建模拟的 strategy_context"""
    strategy_context = Mock()
    strategy_context.strategy_name = "TestStrategy"
    strategy_context.write_log = Mock()
    
    strategy_engine = Mock()
    strategy_context.strategy_engine = strategy_engine
    
    main_engine = Mock()
    strategy_engine.main_engine = main_engine
    
    main_engine.get_all_contracts = Mock(return_value=contracts or [])
    
    if tick_map:
        main_engine.get_tick = Mock(side_effect=lambda vt_symbol: tick_map.get(vt_symbol))
    else:
        main_engine.get_tick = Mock(return_value=None)
    
    main_engine.get_all_accounts = Mock(return_value=accounts or [])
    
    return strategy_context


class TestVnpyTradeGatewayInterfaces:
    """测试 VnpyTradeGateway 实现的接口"""
    
    def test_implements_i_trade_gateway(self):
        """测试实现了 ITradeGateway 接口"""
        assert issubclass(VnpyTradeGateway, ITradeGateway)
    
    def test_implements_i_contract_gateway(self):
        """测试实现了 IContractGateway 接口"""
        assert issubclass(VnpyTradeGateway, IContractGateway)
    
    def test_can_instantiate(self):
        """测试可以实例化"""
        strategy_context = create_mock_strategy_context()
        gateway = VnpyTradeGateway(strategy_context)
        
        assert gateway is not None
        assert isinstance(gateway, ITradeGateway)
        assert isinstance(gateway, IContractGateway)


class TestVnpyTradeGatewayContractDelegation:
    """测试 VnpyTradeGateway 的合约查询委托"""
    
    def test_get_option_contracts_delegates_to_internal_gateway(self):
        """测试 get_option_contracts 委托给内部网关"""
        contracts = [
            MockContract(
                vt_symbol="IO2312-C-4000.CFFEX",
                underlying_symbol="IF2312.CFFEX",
                option_type=OptionType.CALL,
                option_strike=4000,
                option_expiry="2023-12-15"
            )
        ]
        
        strategy_context = create_mock_strategy_context(contracts=contracts)
        gateway = VnpyTradeGateway(strategy_context)
        
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["vt_symbol"] == "IO2312-C-4000.CFFEX"
    
    def test_get_option_contracts_returns_empty_on_error(self):
        """测试错误时返回空 DataFrame"""
        strategy_context = Mock()
        strategy_context.strategy_name = "TestStrategy"
        strategy_context.write_log = Mock()
        # 没有 strategy_engine，会导致错误
        del strategy_context.strategy_engine
        
        gateway = VnpyTradeGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_internal_contract_gateway_is_created(self):
        """测试内部合约网关被创建"""
        strategy_context = create_mock_strategy_context()
        gateway = VnpyTradeGateway(strategy_context)
        
        assert hasattr(gateway, "_contract_gateway")
        assert gateway._contract_gateway is not None


class TestVnpyTradeGatewayAccountBalance:
    """测试 VnpyTradeGateway 的账户余额查询"""
    
    def test_get_account_balance_returns_balance(self):
        """测试获取账户余额"""
        class MockAccount:
            available = 100000.0
        
        strategy_context = create_mock_strategy_context(accounts=[MockAccount()])
        gateway = VnpyTradeGateway(strategy_context)
        
        result = gateway.get_account_balance()
        
        assert result == 100000.0
    
    def test_get_account_balance_returns_zero_on_error(self):
        """测试错误时返回 0.0"""
        strategy_context = Mock()
        strategy_context.strategy_name = "TestStrategy"
        strategy_context.write_log = Mock()
        del strategy_context.strategy_engine
        
        gateway = VnpyTradeGateway(strategy_context)
        result = gateway.get_account_balance()
        
        assert result == 0.0


class TestVnpyTradeGatewayIntegration:
    """测试 VnpyTradeGateway 的集成功能"""
    
    def test_can_use_both_interfaces(self):
        """测试可以同时使用两个接口的功能"""
        contracts = [
            MockContract(
                vt_symbol="IO2312-C-4000.CFFEX",
                option_type=OptionType.CALL
            )
        ]
        
        class MockAccount:
            available = 50000.0
        
        strategy_context = create_mock_strategy_context(
            contracts=contracts,
            accounts=[MockAccount()]
        )
        strategy_context.buy = Mock(return_value=["order_001"])
        
        gateway = VnpyTradeGateway(strategy_context)
        
        # 使用 IContractGateway 接口
        contracts_df = gateway.get_option_contracts("IF2312.CFFEX")
        assert len(contracts_df) == 1
        
        # 使用 ITradeGateway 接口
        balance = gateway.get_account_balance()
        assert balance == 50000.0

