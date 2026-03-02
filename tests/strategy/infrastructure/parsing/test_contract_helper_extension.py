"""
ContractHelper 扩展功能单元测试

测试新增的到期日提取和行权价分组方法。
"""
import pytest

from src.strategy.infrastructure.parsing.contract_helper import ContractHelper


class TestContractHelperExtension:
    """ContractHelper 扩展功能单元测试"""
    
    # 到期日提取测试
    
    def test_extract_expiry_from_io_symbol(self):
        """测试从 IO 期权合约提取到期日"""
        assert ContractHelper.extract_expiry_from_symbol("IO2401-C-4000.CFFEX") == "2401"
        assert ContractHelper.extract_expiry_from_symbol("IO2509-P-4500.CFFEX") == "2509"
        assert ContractHelper.extract_expiry_from_symbol("IO2412-C-5000.CFFEX") == "2412"
    
    def test_extract_expiry_from_mo_symbol(self):
        """测试从 MO 期权合约提取到期日"""
        assert ContractHelper.extract_expiry_from_symbol("MO2401-C-3000.CFFEX") == "2401"
        assert ContractHelper.extract_expiry_from_symbol("MO2506-P-3500.CFFEX") == "2506"
    
    def test_extract_expiry_from_ho_symbol(self):
        """测试从 HO 期权合约提取到期日"""
        assert ContractHelper.extract_expiry_from_symbol("HO2401-C-2000.CFFEX") == "2401"
        assert ContractHelper.extract_expiry_from_symbol("HO2503-P-2500.CFFEX") == "2503"
    
    def test_extract_expiry_from_commodity_symbol(self):
        """测试从商品期权合约提取到期日"""
        assert ContractHelper.extract_expiry_from_symbol("m2509-C-2800.DCE") == "2509"
        assert ContractHelper.extract_expiry_from_symbol("c2501-P-3000.DCE") == "2501"
        assert ContractHelper.extract_expiry_from_symbol("SR2405-C-6000.CZCE") == "2405"
        assert ContractHelper.extract_expiry_from_symbol("CF2409-P-15000.CZCE") == "2409"
    
    def test_extract_expiry_without_exchange(self):
        """测试不带交易所后缀的合约代码"""
        assert ContractHelper.extract_expiry_from_symbol("IO2401-C-4000") == "2401"
        assert ContractHelper.extract_expiry_from_symbol("m2509-C-2800") == "2509"
    
    def test_extract_expiry_with_compact_format(self):
        """测试紧凑格式的合约代码（无分隔符）"""
        assert ContractHelper.extract_expiry_from_symbol("IO2401C4000.CFFEX") == "2401"
        assert ContractHelper.extract_expiry_from_symbol("m2509P2800.DCE") == "2509"
    
    def test_extract_expiry_invalid_format(self):
        """测试无效格式返回 unknown"""
        assert ContractHelper.extract_expiry_from_symbol("INVALID") == "unknown"
        assert ContractHelper.extract_expiry_from_symbol("") == "unknown"
        assert ContractHelper.extract_expiry_from_symbol("ABC") == "unknown"
    
    # 行权价分组测试
    
    def test_group_by_strike_range_small_strike(self):
        """测试小行权价（< 1000）的分组，区间宽度 100"""
        assert ContractHelper.group_by_strike_range("m2509-C-800.DCE") == "800-900"
        assert ContractHelper.group_by_strike_range("m2509-C-950.DCE") == "900-1000"
        assert ContractHelper.group_by_strike_range("c2501-P-500.DCE") == "500-600"
    
    def test_group_by_strike_range_medium_strike(self):
        """测试中等行权价（1000-5000）的分组，区间宽度 500"""
        assert ContractHelper.group_by_strike_range("IO2401-C-4000.CFFEX") == "4000-4500"
        assert ContractHelper.group_by_strike_range("IO2401-C-4200.CFFEX") == "4000-4500"
        assert ContractHelper.group_by_strike_range("IO2401-C-4500.CFFEX") == "4500-5000"
        assert ContractHelper.group_by_strike_range("m2509-C-2800.DCE") == "2500-3000"
        assert ContractHelper.group_by_strike_range("HO2401-P-2000.CFFEX") == "2000-2500"
    
    def test_group_by_strike_range_large_strike(self):
        """测试大行权价（>= 5000）的分组，区间宽度 1000"""
        assert ContractHelper.group_by_strike_range("SR2405-C-6000.CZCE") == "6000-7000"
        assert ContractHelper.group_by_strike_range("SR2405-C-6500.CZCE") == "6000-7000"
        assert ContractHelper.group_by_strike_range("CF2409-P-15000.CZCE") == "15000-16000"
        assert ContractHelper.group_by_strike_range("IO2401-C-5000.CFFEX") == "5000-6000"
    
    def test_group_by_strike_range_boundary_1000(self):
        """测试边界值 1000"""
        assert ContractHelper.group_by_strike_range("m2509-C-1000.DCE") == "1000-1500"
        assert ContractHelper.group_by_strike_range("m2509-C-999.DCE") == "900-1000"
    
    def test_group_by_strike_range_boundary_5000(self):
        """测试边界值 5000"""
        assert ContractHelper.group_by_strike_range("IO2401-C-5000.CFFEX") == "5000-6000"
        assert ContractHelper.group_by_strike_range("IO2401-C-4999.CFFEX") == "4500-5000"
    
    def test_group_by_strike_range_without_exchange(self):
        """测试不带交易所后缀的合约代码"""
        assert ContractHelper.group_by_strike_range("IO2401-C-4000") == "4000-4500"
        assert ContractHelper.group_by_strike_range("m2509-C-2800") == "2500-3000"
    
    def test_group_by_strike_range_with_compact_format(self):
        """测试紧凑格式的合约代码（无分隔符）"""
        assert ContractHelper.group_by_strike_range("IO2401C4000.CFFEX") == "4000-4500"
        assert ContractHelper.group_by_strike_range("m2509P2800.DCE") == "2500-3000"
    
    def test_group_by_strike_range_with_decimal_strike(self):
        """测试带小数的行权价"""
        assert ContractHelper.group_by_strike_range("IO2401-C-4000.5.CFFEX") == "4000-4500"
        assert ContractHelper.group_by_strike_range("m2509-C-2850.5.DCE") == "2500-3000"
    
    def test_group_by_strike_range_invalid_format(self):
        """测试无效格式返回 unknown"""
        assert ContractHelper.group_by_strike_range("INVALID") == "unknown"
        assert ContractHelper.group_by_strike_range("") == "unknown"
        assert ContractHelper.group_by_strike_range("ABC") == "unknown"
    
    # 综合测试
    
    def test_extract_expiry_and_group_strike_together(self):
        """测试同时提取到期日和分组行权价"""
        symbol = "IO2401-C-4000.CFFEX"
        expiry = ContractHelper.extract_expiry_from_symbol(symbol)
        strike_range = ContractHelper.group_by_strike_range(symbol)
        
        assert expiry == "2401"
        assert strike_range == "4000-4500"
    
    def test_various_option_types(self):
        """测试不同期权类型（看涨/看跌）"""
        # 看涨期权
        assert ContractHelper.extract_expiry_from_symbol("IO2401-C-4000.CFFEX") == "2401"
        assert ContractHelper.group_by_strike_range("IO2401-C-4000.CFFEX") == "4000-4500"
        
        # 看跌期权
        assert ContractHelper.extract_expiry_from_symbol("IO2401-P-4000.CFFEX") == "2401"
        assert ContractHelper.group_by_strike_range("IO2401-P-4000.CFFEX") == "4000-4500"
    
    def test_various_exchanges(self):
        """测试不同交易所的合约"""
        # CFFEX
        assert ContractHelper.extract_expiry_from_symbol("IO2401-C-4000.CFFEX") == "2401"
        assert ContractHelper.group_by_strike_range("IO2401-C-4000.CFFEX") == "4000-4500"
        
        # DCE
        assert ContractHelper.extract_expiry_from_symbol("m2509-C-2800.DCE") == "2509"
        assert ContractHelper.group_by_strike_range("m2509-C-2800.DCE") == "2500-3000"
        
        # CZCE
        assert ContractHelper.extract_expiry_from_symbol("SR2405-C-6000.CZCE") == "2405"
        assert ContractHelper.group_by_strike_range("SR2405-C-6000.CZCE") == "6000-7000"
        
        # SHFE
        assert ContractHelper.extract_expiry_from_symbol("cu2506-C-70000.SHFE") == "2506"
        assert ContractHelper.group_by_strike_range("cu2506-C-70000.SHFE") == "70000-71000"
