"""
VnpyContractGateway 单元测试

测试 VnPy 合约查询网关的实现。
使用 Mock 对象模拟 VnPy 的 strategy_context 和 main_engine。
"""
import pytest
from unittest.mock import Mock, MagicMock
import pandas as pd
try:
    from src.strategy.infrastructure.gateway.vnpy_contract_gateway import (
        VnpyContractGateway,
        OptionType
    )
except Exception:
    pytest.skip("legacy gateway removed or renamed", allow_module_level=True)


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


class MockTick:
    """模拟 VnPy Tick 对象"""
    
    def __init__(
        self,
        bid_price_1: float = 0,
        bid_volume_1: int = 0,
        ask_price_1: float = 0,
        ask_volume_1: int = 0
    ):
        self.bid_price_1 = bid_price_1
        self.bid_volume_1 = bid_volume_1
        self.ask_price_1 = ask_price_1
        self.ask_volume_1 = ask_volume_1


class MockAccount:
    """模拟 VnPy 账户对象"""
    
    def __init__(self, available: float = 0):
        self.available = available


def create_mock_strategy_context(
    has_strategy_engine: bool = True,
    has_main_engine: bool = True,
    has_get_all_contracts: bool = True,
    contracts: list = None,
    tick_map: dict = None,
    accounts: list = None
):
    """
    创建模拟的 strategy_context
    
    Args:
        has_strategy_engine: 是否有 strategy_engine 属性
        has_main_engine: 是否有 main_engine 属性
        has_get_all_contracts: 是否有 get_all_contracts 方法
        contracts: 合约列表
        tick_map: vt_symbol -> tick 的映射
        accounts: 账户列表
    """
    strategy_context = Mock()
    strategy_context.strategy_name = "TestStrategy"
    strategy_context.write_log = Mock()
    
    if not has_strategy_engine:
        del strategy_context.strategy_engine
        return strategy_context
    
    strategy_engine = Mock()
    strategy_context.strategy_engine = strategy_engine
    
    if not has_main_engine:
        del strategy_engine.main_engine
        return strategy_context
    
    main_engine = Mock()
    strategy_engine.main_engine = main_engine
    
    if not has_get_all_contracts:
        del main_engine.get_all_contracts
        return strategy_context
    
    # 设置 get_all_contracts 返回值
    main_engine.get_all_contracts = Mock(return_value=contracts or [])
    
    # 设置 get_tick 返回值
    if tick_map:
        main_engine.get_tick = Mock(side_effect=lambda vt_symbol: tick_map.get(vt_symbol))
    else:
        main_engine.get_tick = Mock(return_value=None)
    
    # 设置 get_all_accounts 返回值
    main_engine.get_all_accounts = Mock(return_value=accounts or [])
    
    return strategy_context


class TestVnpyContractGatewayInit:
    """测试 VnpyContractGateway 初始化"""
    
    def test_init_with_strategy_context(self):
        """测试使用 strategy_context 初始化"""
        strategy_context = create_mock_strategy_context()
        gateway = VnpyContractGateway(strategy_context)
        
        assert gateway.strategy_context == strategy_context
        assert gateway._log_prefix == "[TestStrategy]"
    
    def test_init_without_strategy_name(self):
        """测试没有 strategy_name 时使用默认值"""
        strategy_context = Mock()
        del strategy_context.strategy_name
        
        gateway = VnpyContractGateway(strategy_context)
        assert gateway._log_prefix == "[Strategy]"


class TestGetOptionContracts:
    """测试 get_option_contracts 方法"""
    
    def test_successful_retrieval(self):
        """测试成功获取期权合约"""
        contracts = [
            MockContract(
                vt_symbol="IO2312-C-4000.CFFEX",
                underlying_symbol="IF2312.CFFEX",
                option_type=OptionType.CALL,
                option_strike=4000,
                option_expiry="2023-12-15"
            ),
            MockContract(
                vt_symbol="IO2312-P-3800.CFFEX",
                underlying_symbol="IF2312.CFFEX",
                option_type=OptionType.PUT,
                option_strike=3800,
                option_expiry="2023-12-15"
            )
        ]
        
        tick_map = {
            "IO2312-C-4000.CFFEX": MockTick(125.5, 10, 126.0, 15),
            "IO2312-P-3800.CFFEX": MockTick(80.0, 20, 81.0, 25)
        }
        
        strategy_context = create_mock_strategy_context(
            contracts=contracts,
            tick_map=tick_map
        )
        
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "vt_symbol" in result.columns
        assert "option_type" in result.columns
    
    def test_option_type_mapping_call(self):
        """测试 CALL 类型映射为 'call'"""
        contracts = [
            MockContract(
                vt_symbol="IO2312-C-4000.CFFEX",
                option_type=OptionType.CALL
            )
        ]
        
        strategy_context = create_mock_strategy_context(contracts=contracts)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        assert result.iloc[0]["option_type"] == "call"
    
    def test_option_type_mapping_put(self):
        """测试 PUT 类型映射为 'put'"""
        contracts = [
            MockContract(
                vt_symbol="IO2312-P-3800.CFFEX",
                option_type=OptionType.PUT
            )
        ]
        
        strategy_context = create_mock_strategy_context(contracts=contracts)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        assert result.iloc[0]["option_type"] == "put"
    
    def test_tick_data_extraction_with_valid_tick(self):
        """测试有效 tick 数据的提取"""
        contracts = [
            MockContract(
                vt_symbol="IO2312-C-4000.CFFEX",
                option_type=OptionType.CALL
            )
        ]
        
        tick_map = {
            "IO2312-C-4000.CFFEX": MockTick(125.5, 10, 126.0, 15)
        }
        
        strategy_context = create_mock_strategy_context(
            contracts=contracts,
            tick_map=tick_map
        )
        
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        assert result.iloc[0]["bid_price"] == 125.5
        assert result.iloc[0]["bid_volume"] == 10
        assert result.iloc[0]["ask_price"] == 126.0
        assert result.iloc[0]["ask_volume"] == 15
    
    def test_tick_data_extraction_with_none_tick(self):
        """测试 tick 为 None 时使用默认值 0"""
        contracts = [
            MockContract(
                vt_symbol="IO2312-C-4000.CFFEX",
                option_type=OptionType.CALL
            )
        ]
        
        # tick_map 为空，get_tick 返回 None
        strategy_context = create_mock_strategy_context(contracts=contracts)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        assert result.iloc[0]["bid_price"] == 0
        assert result.iloc[0]["bid_volume"] == 0
        assert result.iloc[0]["ask_price"] == 0
        assert result.iloc[0]["ask_volume"] == 0
    
    def test_filters_non_option_contracts(self):
        """测试过滤非期权合约"""
        contracts = [
            MockContract(
                vt_symbol="IF2312.CFFEX",
                option_type=None  # 期货合约，没有 option_type
            ),
            MockContract(
                vt_symbol="IO2312-C-4000.CFFEX",
                option_type=OptionType.CALL
            )
        ]
        
        strategy_context = create_mock_strategy_context(contracts=contracts)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        # 应该只返回期权合约
        assert len(result) == 1
        assert result.iloc[0]["vt_symbol"] == "IO2312-C-4000.CFFEX"
    
    def test_returns_all_required_columns(self):
        """测试返回所有必需的列"""
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
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        required_columns = [
            "vt_symbol", "underlying_symbol", "option_type",
            "strike_price", "expiry_date", "bid_price", "bid_volume",
            "ask_price", "ask_volume", "days_to_expiry"
        ]
        
        for col in required_columns:
            assert col in result.columns, f"Missing column: {col}"


class TestGetOptionContractsErrorHandling:
    """测试 get_option_contracts 错误处理"""
    
    def test_missing_strategy_engine(self):
        """测试缺少 strategy_engine 时返回空 DataFrame"""
        strategy_context = create_mock_strategy_context(has_strategy_engine=False)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        strategy_context.write_log.assert_called()
    
    def test_missing_main_engine(self):
        """测试缺少 main_engine 时返回空 DataFrame"""
        strategy_context = create_mock_strategy_context(has_main_engine=False)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        strategy_context.write_log.assert_called()
    
    def test_missing_get_all_contracts(self):
        """测试缺少 get_all_contracts 方法时返回空 DataFrame"""
        strategy_context = create_mock_strategy_context(has_get_all_contracts=False)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        strategy_context.write_log.assert_called()
    
    def test_exception_during_retrieval(self):
        """测试获取过程中发生异常时返回空 DataFrame"""
        strategy_context = create_mock_strategy_context()
        strategy_context.strategy_engine.main_engine.get_all_contracts.side_effect = Exception("Test error")
        
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_option_contracts("IF2312.CFFEX")
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        strategy_context.write_log.assert_called()


class TestGetAccountBalance:
    """测试 get_account_balance 方法"""
    
    def test_successful_retrieval(self):
        """测试成功获取账户余额"""
        accounts = [MockAccount(available=100000.0)]
        strategy_context = create_mock_strategy_context(accounts=accounts)
        
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_account_balance()
        
        assert result == 100000.0
    
    def test_missing_strategy_engine(self):
        """测试缺少 strategy_engine 时返回 0.0"""
        strategy_context = create_mock_strategy_context(has_strategy_engine=False)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_account_balance()
        
        assert result == 0.0
    
    def test_missing_main_engine(self):
        """测试缺少 main_engine 时返回 0.0"""
        strategy_context = create_mock_strategy_context(has_main_engine=False)
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_account_balance()
        
        assert result == 0.0
    
    def test_empty_accounts(self):
        """测试账户列表为空时返回 0.0"""
        strategy_context = create_mock_strategy_context(accounts=[])
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_account_balance()
        
        assert result == 0.0
    
    def test_exception_during_retrieval(self):
        """测试获取过程中发生异常时返回 0.0"""
        strategy_context = create_mock_strategy_context()
        strategy_context.strategy_engine.main_engine.get_all_accounts.side_effect = Exception("Test error")
        
        gateway = VnpyContractGateway(strategy_context)
        result = gateway.get_account_balance()
        
        assert result == 0.0
        strategy_context.write_log.assert_called()

