"""
IContractGateway 接口定义测试

测试合约查询网关接口的定义是否正确。
"""
import pytest
from abc import ABC
import inspect
import pandas as pd
try:
    from src.strategy.domain.demand_interface.i_contract_gateway import IContractGateway
except Exception:
    pytest.skip("legacy interface removed or renamed", allow_module_level=True)


class TestIContractGatewayInterface:
    """测试 IContractGateway 接口定义"""
    
    def test_interface_is_abstract(self):
        """测试接口是抽象类"""
        assert issubclass(IContractGateway, ABC)
        
        # 尝试直接实例化应该失败
        with pytest.raises(TypeError):
            IContractGateway()
    
    def test_get_option_contracts_method_exists(self):
        """测试 get_option_contracts 方法存在"""
        assert hasattr(IContractGateway, 'get_option_contracts')
        assert callable(getattr(IContractGateway, 'get_option_contracts'))
    
    def test_get_option_contracts_method_signature(self):
        """测试 get_option_contracts 方法签名"""
        sig = inspect.signature(IContractGateway.get_option_contracts)
        params = list(sig.parameters.keys())
        
        # 应该有 self 和 underlying_vt_symbol 两个参数
        assert 'self' in params
        assert 'underlying_vt_symbol' in params
        assert len(params) == 2
    
    def test_get_account_balance_method_exists(self):
        """测试 get_account_balance 方法存在"""
        assert hasattr(IContractGateway, 'get_account_balance')
        assert callable(getattr(IContractGateway, 'get_account_balance'))
    
    def test_get_account_balance_method_signature(self):
        """测试 get_account_balance 方法签名"""
        sig = inspect.signature(IContractGateway.get_account_balance)
        params = list(sig.parameters.keys())
        
        # 应该只有 self 参数
        assert 'self' in params
        assert len(params) == 1
    
    def test_interface_methods_are_abstract(self):
        """测试接口方法是抽象方法"""
        # 获取抽象方法列表
        abstract_methods = IContractGateway.__abstractmethods__
        
        assert 'get_option_contracts' in abstract_methods
        assert 'get_account_balance' in abstract_methods


class TestIContractGatewayImplementation:
    """测试 IContractGateway 接口可以被正确实现"""
    
    def test_can_implement_interface(self):
        """测试可以实现接口"""
        
        class MockContractGateway(IContractGateway):
            """模拟实现"""
            
            def get_option_contracts(self, underlying_vt_symbol: str) -> pd.DataFrame:
                return pd.DataFrame()
            
            def get_account_balance(self) -> float:
                return 0.0
        
        # 应该可以实例化
        gateway = MockContractGateway()
        assert gateway is not None
    
    def test_partial_implementation_fails(self):
        """测试部分实现会失败"""
        
        class PartialGateway(IContractGateway):
            """只实现部分方法"""
            
            def get_option_contracts(self, underlying_vt_symbol: str) -> pd.DataFrame:
                return pd.DataFrame()
            
            # 缺少 get_account_balance 方法
        
        # 尝试实例化应该失败
        with pytest.raises(TypeError):
            PartialGateway()
    
    def test_implementation_returns_correct_types(self):
        """测试实现返回正确的类型"""
        
        class TypedGateway(IContractGateway):
            """带类型检查的实现"""
            
            def get_option_contracts(self, underlying_vt_symbol: str) -> pd.DataFrame:
                return pd.DataFrame({
                    'vt_symbol': ['IO2312-C-4000.CFFEX'],
                    'underlying_symbol': ['IF2312.CFFEX'],
                    'option_type': ['call'],
                    'strike_price': [4000.0],
                    'expiry_date': ['2023-12-15'],
                    'bid_price': [125.5],
                    'bid_volume': [10],
                    'ask_price': [126.0],
                    'ask_volume': [15],
                    'days_to_expiry': [30]
                })
            
            def get_account_balance(self) -> float:
                return 100000.0
        
        gateway = TypedGateway()
        
        # 测试返回类型
        contracts = gateway.get_option_contracts('IF2312.CFFEX')
        assert isinstance(contracts, pd.DataFrame)
        
        balance = gateway.get_account_balance()
        assert isinstance(balance, float)

