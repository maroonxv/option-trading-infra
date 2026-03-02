"""
ConcentrationMonitor 单元测试

测试集中度风险监控服务的品种、到期日、行权价集中度计算和 HHI 计算功能。
"""
import pytest

from src.strategy.domain.domain_service.risk.concentration_monitor import ConcentrationMonitor
from src.strategy.domain.entity.position import Position
from src.strategy.domain.value_object.risk.risk import (
    ConcentrationConfig,
    ConcentrationMetrics,
    ConcentrationWarning,
)


class TestConcentrationMonitorConfig:
    """测试集中度监控配置"""
    
    def test_valid_config(self):
        """测试有效配置"""
        config = ConcentrationConfig(
            underlying_concentration_limit=0.5,
            expiry_concentration_limit=0.6,
            strike_concentration_limit=0.4,
            hhi_threshold=0.25,
            concentration_basis="notional",
        )
        monitor = ConcentrationMonitor(config)
        assert monitor is not None
        assert monitor.config.underlying_concentration_limit == 0.5
        assert monitor.config.expiry_concentration_limit == 0.6
        assert monitor.config.strike_concentration_limit == 0.4
        assert monitor.config.hhi_threshold == 0.25
        assert monitor.config.concentration_basis == "notional"


class TestUnderlyingConcentration:
    """测试品种集中度计算"""
    
    def test_single_underlying(self):
        """测试单一品种的集中度"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建单一品种的持仓
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            )
        ]
        
        prices = {"IO2401-C-4000.CFFEX": 0.5}
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 单一品种，集中度应该是 100%
        assert len(metrics.underlying_concentration) == 1
        assert "IF2401.CFFEX" in metrics.underlying_concentration
        assert metrics.underlying_concentration["IF2401.CFFEX"] == 1.0
        assert metrics.max_underlying_ratio == 1.0
        assert metrics.underlying_hhi == 1.0
    
    def test_multiple_underlyings_equal_distribution(self):
        """测试多品种均匀分布的集中度"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建两个品种，各占 50%
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="HO2401-C-3000.CFFEX",
                underlying_vt_symbol="IH2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "HO2401-C-3000.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 两个品种各占 50%
        assert len(metrics.underlying_concentration) == 2
        assert abs(metrics.underlying_concentration["IF2401.CFFEX"] - 0.5) < 1e-6
        assert abs(metrics.underlying_concentration["IH2401.CFFEX"] - 0.5) < 1e-6
        assert abs(metrics.max_underlying_ratio - 0.5) < 1e-6
        # HHI = 0.5^2 + 0.5^2 = 0.5
        assert abs(metrics.underlying_hhi - 0.5) < 1e-6
    
    def test_multiple_underlyings_unequal_distribution(self):
        """测试多品种不均匀分布的集中度"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建三个品种：60%, 30%, 10%
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=12,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="HO2401-C-3000.CFFEX",
                underlying_vt_symbol="IH2401.CFFEX",
                signal="open_signal",
                volume=6,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="MO2401-C-5000.CFFEX",
                underlying_vt_symbol="IM2401.CFFEX",
                signal="open_signal",
                volume=2,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "HO2401-C-3000.CFFEX": 0.5,
            "MO2401-C-5000.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 验证占比
        assert len(metrics.underlying_concentration) == 3
        assert abs(metrics.underlying_concentration["IF2401.CFFEX"] - 0.6) < 1e-6
        assert abs(metrics.underlying_concentration["IH2401.CFFEX"] - 0.3) < 1e-6
        assert abs(metrics.underlying_concentration["IM2401.CFFEX"] - 0.1) < 1e-6
        assert abs(metrics.max_underlying_ratio - 0.6) < 1e-6
        # HHI = 0.6^2 + 0.3^2 + 0.1^2 = 0.36 + 0.09 + 0.01 = 0.46
        assert abs(metrics.underlying_hhi - 0.46) < 1e-6


class TestExpiryConcentration:
    """测试到期日集中度计算"""
    
    def test_single_expiry(self):
        """测试单一到期日的集中度"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建同一到期日的持仓
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="IO2401-C-4100.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=5,
                direction="short",
                open_price=0.6,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "IO2401-C-4100.CFFEX": 0.6,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 单一到期日，集中度应该是 100%
        assert len(metrics.expiry_concentration) == 1
        assert "2401" in metrics.expiry_concentration
        assert metrics.expiry_concentration["2401"] == 1.0
        assert metrics.max_expiry_ratio == 1.0
        assert metrics.expiry_hhi == 1.0
    
    def test_multiple_expiries(self):
        """测试多个到期日的集中度"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建不同到期日的持仓：70% 2401, 30% 2402
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=14,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="IO2402-C-4000.CFFEX",
                underlying_vt_symbol="IF2402.CFFEX",
                signal="open_signal",
                volume=6,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "IO2402-C-4000.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 验证占比
        assert len(metrics.expiry_concentration) == 2
        assert abs(metrics.expiry_concentration["2401"] - 0.7) < 1e-6
        assert abs(metrics.expiry_concentration["2402"] - 0.3) < 1e-6
        assert abs(metrics.max_expiry_ratio - 0.7) < 1e-6
        # HHI = 0.7^2 + 0.3^2 = 0.49 + 0.09 = 0.58
        assert abs(metrics.expiry_hhi - 0.58) < 1e-6



class TestStrikeConcentration:
    """测试行权价集中度计算"""
    
    def test_single_strike_range(self):
        """测试单一行权价区间的集中度"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建同一行权价区间的持仓（4000-4500 区间）
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="IO2401-C-4100.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=5,
                direction="short",
                open_price=0.6,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "IO2401-C-4100.CFFEX": 0.6,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 单一行权价区间，集中度应该是 100%
        assert len(metrics.strike_concentration) == 1
        assert "4000-4500" in metrics.strike_concentration
        assert metrics.strike_concentration["4000-4500"] == 1.0
        assert metrics.max_strike_ratio == 1.0
        assert metrics.strike_hhi == 1.0
    
    def test_multiple_strike_ranges(self):
        """测试多个行权价区间的集中度"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建不同行权价区间的持仓：60% 4000-4500, 40% 4500-5000
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=12,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="IO2401-C-4500.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=8,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "IO2401-C-4500.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 验证占比
        assert len(metrics.strike_concentration) == 2
        assert abs(metrics.strike_concentration["4000-4500"] - 0.6) < 1e-6
        assert abs(metrics.strike_concentration["4500-5000"] - 0.4) < 1e-6
        assert abs(metrics.max_strike_ratio - 0.6) < 1e-6
        # HHI = 0.6^2 + 0.4^2 = 0.36 + 0.16 = 0.52
        assert abs(metrics.strike_hhi - 0.52) < 1e-6


class TestHHICalculation:
    """测试 HHI 计算"""
    
    def test_hhi_perfect_concentration(self):
        """测试完全集中的 HHI（单一持仓）"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            )
        ]
        
        prices = {"IO2401-C-4000.CFFEX": 0.5}
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 完全集中，HHI = 1.0
        assert metrics.underlying_hhi == 1.0
        assert metrics.expiry_hhi == 1.0
        assert metrics.strike_hhi == 1.0
    
    def test_hhi_perfect_diversification(self):
        """测试完全分散的 HHI（四个品种均分）"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建四个品种，各占 25%
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=5,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="HO2401-C-3000.CFFEX",
                underlying_vt_symbol="IH2401.CFFEX",
                signal="open_signal",
                volume=5,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="MO2401-C-5000.CFFEX",
                underlying_vt_symbol="IM2401.CFFEX",
                signal="open_signal",
                volume=5,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="m2509-C-2800.DCE",
                underlying_vt_symbol="m2509.DCE",
                signal="open_signal",
                volume=5,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "HO2401-C-3000.CFFEX": 0.5,
            "MO2401-C-5000.CFFEX": 0.5,
            "m2509-C-2800.DCE": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # HHI = 4 * (0.25^2) = 4 * 0.0625 = 0.25
        assert abs(metrics.underlying_hhi - 0.25) < 1e-6


class TestConcentrationWarnings:
    """测试集中度超限警告"""
    
    def test_underlying_concentration_warning(self):
        """测试品种集中度超限警告"""
        config = ConcentrationConfig(
            underlying_concentration_limit=0.5,
        )
        monitor = ConcentrationMonitor(config)
        
        # 创建品种集中度 60% 的持仓（超过 50% 限额）
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=12,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="HO2401-C-3000.CFFEX",
                underlying_vt_symbol="IH2401.CFFEX",
                signal="open_signal",
                volume=8,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "HO2401-C-3000.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        warnings = monitor.check_concentration_limits(metrics)
        
        # 应该有一个品种集中度警告
        underlying_warnings = [w for w in warnings if w.dimension == "underlying"]
        assert len(underlying_warnings) == 1
        assert underlying_warnings[0].key == "IF2401.CFFEX"
        assert abs(underlying_warnings[0].concentration - 0.6) < 1e-6
        assert underlying_warnings[0].limit == 0.5
        assert "品种" in underlying_warnings[0].message
        assert "集中度" in underlying_warnings[0].message
    
    def test_expiry_concentration_warning(self):
        """测试到期日集中度超限警告"""
        config = ConcentrationConfig(
            expiry_concentration_limit=0.6,
        )
        monitor = ConcentrationMonitor(config)
        
        # 创建到期日集中度 70% 的持仓（超过 60% 限额）
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=14,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="IO2402-C-4000.CFFEX",
                underlying_vt_symbol="IF2402.CFFEX",
                signal="open_signal",
                volume=6,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "IO2402-C-4000.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        warnings = monitor.check_concentration_limits(metrics)
        
        # 应该有一个到期日集中度警告
        expiry_warnings = [w for w in warnings if w.dimension == "expiry"]
        assert len(expiry_warnings) == 1
        assert expiry_warnings[0].key == "2401"
        assert abs(expiry_warnings[0].concentration - 0.7) < 1e-6
        assert expiry_warnings[0].limit == 0.6
        assert "到期日" in expiry_warnings[0].message
    
    def test_strike_concentration_warning(self):
        """测试行权价集中度超限警告"""
        config = ConcentrationConfig(
            strike_concentration_limit=0.4,
        )
        monitor = ConcentrationMonitor(config)
        
        # 创建行权价集中度 60% 的持仓（超过 40% 限额）
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=12,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="IO2401-C-4500.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=8,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "IO2401-C-4500.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        warnings = monitor.check_concentration_limits(metrics)
        
        # 应该有一个行权价集中度警告
        strike_warnings = [w for w in warnings if w.dimension == "strike"]
        assert len(strike_warnings) == 1
        assert strike_warnings[0].key == "4000-4500"
        assert abs(strike_warnings[0].concentration - 0.6) < 1e-6
        assert strike_warnings[0].limit == 0.4
        assert "行权价" in strike_warnings[0].message
    
    def test_hhi_warning(self):
        """测试 HHI 超限警告"""
        config = ConcentrationConfig(
            hhi_threshold=0.25,
        )
        monitor = ConcentrationMonitor(config)
        
        # 创建高集中度持仓（HHI = 0.5）
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="HO2401-C-3000.CFFEX",
                underlying_vt_symbol="IH2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "HO2401-C-3000.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        warnings = monitor.check_concentration_limits(metrics)
        
        # 应该有三个 HHI 警告（品种、到期日、行权价各一个）
        hhi_warnings = [w for w in warnings if w.dimension == "hhi"]
        assert len(hhi_warnings) == 3
        
        # 验证品种 HHI 警告
        underlying_hhi_warning = [w for w in hhi_warnings if w.key == "underlying"][0]
        assert abs(underlying_hhi_warning.concentration - 0.5) < 1e-6
        assert underlying_hhi_warning.limit == 0.25
        assert "HHI" in underlying_hhi_warning.message
    
    def test_no_warnings_within_limits(self):
        """测试集中度在限额内不触发警告"""
        config = ConcentrationConfig(
            underlying_concentration_limit=0.7,
            expiry_concentration_limit=0.7,
            strike_concentration_limit=0.7,
            hhi_threshold=0.6,
        )
        monitor = ConcentrationMonitor(config)
        
        # 创建集中度 60% 的持仓（在限额内），使用不同到期日
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=12,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="HO2402-C-3000.CFFEX",
                underlying_vt_symbol="IH2402.CFFEX",
                signal="open_signal",
                volume=8,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "HO2402-C-3000.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        warnings = monitor.check_concentration_limits(metrics)
        
        # 不应该有任何警告
        assert len(warnings) == 0
    
    def test_multiple_warnings(self):
        """测试多个维度同时超限"""
        config = ConcentrationConfig(
            underlying_concentration_limit=0.5,
            expiry_concentration_limit=0.5,
            strike_concentration_limit=0.5,
            hhi_threshold=0.25,
        )
        monitor = ConcentrationMonitor(config)
        
        # 创建高集中度持仓（所有维度都超限）
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=12,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="IO2401-C-4100.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=8,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "IO2401-C-4100.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        warnings = monitor.check_concentration_limits(metrics)
        
        # 应该有多个警告
        assert len(warnings) > 0
        # 品种、到期日、行权价各一个，加上三个 HHI 警告
        assert len(warnings) == 6


class TestBoundaryConditions:
    """测试边界情况"""
    
    def test_empty_positions(self):
        """测试空持仓列表"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        positions = []
        prices = {}
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 空持仓应该返回零集中度
        assert len(metrics.underlying_concentration) == 0
        assert metrics.max_underlying_ratio == 0.0
        assert metrics.underlying_hhi == 0.0
        assert metrics.expiry_hhi == 0.0
        assert metrics.strike_hhi == 0.0
    
    def test_inactive_positions_excluded(self):
        """测试非活跃持仓被排除"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建一个活跃持仓和一个非活跃持仓
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="HO2401-C-3000.CFFEX",
                underlying_vt_symbol="IH2401.CFFEX",
                signal="open_signal",
                volume=0,  # 无持仓
                direction="short",
                open_price=0.5,
                is_closed=True,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "HO2401-C-3000.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 只有一个活跃持仓，集中度应该是 100%
        assert len(metrics.underlying_concentration) == 1
        assert "IF2401.CFFEX" in metrics.underlying_concentration
        assert metrics.underlying_concentration["IF2401.CFFEX"] == 1.0
    
    def test_missing_price_data(self):
        """测试缺失价格数据"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="HO2401-C-3000.CFFEX",
                underlying_vt_symbol="IH2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        # 只提供一个合约的价格
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 只计算有价格数据的持仓，集中度应该是 100%
        assert len(metrics.underlying_concentration) == 1
        assert "IF2401.CFFEX" in metrics.underlying_concentration
        assert metrics.underlying_concentration["IF2401.CFFEX"] == 1.0
    
    def test_zero_total_value(self):
        """测试总价值为零"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            )
        ]
        
        # 价格为零
        prices = {"IO2401-C-4000.CFFEX": 0.0}
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 总价值为零，应该返回零集中度
        assert len(metrics.underlying_concentration) == 0
        assert metrics.max_underlying_ratio == 0.0
        assert metrics.underlying_hhi == 0.0
    
    def test_different_prices(self):
        """测试不同价格的持仓"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建两个品种，但价格不同
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="HO2401-C-3000.CFFEX",
                underlying_vt_symbol="IH2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=1.0,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,  # 价值 = 0.5 * 10 = 5
            "HO2401-C-3000.CFFEX": 1.0,  # 价值 = 1.0 * 10 = 10
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 总价值 = 15，IF 占 5/15 = 1/3，IH 占 10/15 = 2/3
        assert len(metrics.underlying_concentration) == 2
        assert abs(metrics.underlying_concentration["IF2401.CFFEX"] - 1/3) < 1e-6
        assert abs(metrics.underlying_concentration["IH2401.CFFEX"] - 2/3) < 1e-6
        assert abs(metrics.max_underlying_ratio - 2/3) < 1e-6
    
    def test_concentration_sum_equals_one(self):
        """测试集中度占比总和等于 1.0"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建多个品种
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="HO2401-C-3000.CFFEX",
                underlying_vt_symbol="IH2401.CFFEX",
                signal="open_signal",
                volume=15,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="MO2401-C-5000.CFFEX",
                underlying_vt_symbol="IM2401.CFFEX",
                signal="open_signal",
                volume=5,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "HO2401-C-3000.CFFEX": 0.5,
            "MO2401-C-5000.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 验证品种集中度总和为 1.0
        underlying_sum = sum(metrics.underlying_concentration.values())
        assert abs(underlying_sum - 1.0) < 1e-6
        
        # 验证到期日集中度总和为 1.0
        expiry_sum = sum(metrics.expiry_concentration.values())
        assert abs(expiry_sum - 1.0) < 1e-6
        
        # 验证行权价集中度总和为 1.0
        strike_sum = sum(metrics.strike_concentration.values())
        assert abs(strike_sum - 1.0) < 1e-6
    
    def test_hhi_range(self):
        """测试 HHI 在 [0, 1] 范围内"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建随机分布的持仓
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=7,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="HO2401-C-3000.CFFEX",
                underlying_vt_symbol="IH2401.CFFEX",
                signal="open_signal",
                volume=13,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="MO2401-C-5000.CFFEX",
                underlying_vt_symbol="IM2401.CFFEX",
                signal="open_signal",
                volume=5,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "HO2401-C-3000.CFFEX": 0.5,
            "MO2401-C-5000.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 验证 HHI 在 [0, 1] 范围内
        assert 0.0 <= metrics.underlying_hhi <= 1.0
        assert 0.0 <= metrics.expiry_hhi <= 1.0
        assert 0.0 <= metrics.strike_hhi <= 1.0
    
    def test_unknown_expiry_handling(self):
        """测试无法提取到期日的合约"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建格式异常的合约代码
        positions = [
            Position(
                vt_symbol="INVALID_SYMBOL.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            )
        ]
        
        prices = {"INVALID_SYMBOL.CFFEX": 0.5}
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 应该归类到 "unknown"
        assert "unknown" in metrics.expiry_concentration
        assert metrics.expiry_concentration["unknown"] == 1.0
    
    def test_unknown_strike_handling(self):
        """测试无法提取行权价的合约"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建格式异常的合约代码
        positions = [
            Position(
                vt_symbol="INVALID_SYMBOL.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            )
        ]
        
        prices = {"INVALID_SYMBOL.CFFEX": 0.5}
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 应该归类到 "unknown"
        assert "unknown" in metrics.strike_concentration
        assert metrics.strike_concentration["unknown"] == 1.0


class TestStrikeRangeGrouping:
    """测试行权价区间分组"""
    
    def test_small_strike_grouping(self):
        """测试小行权价的分组（< 1000，区间 100）"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建小行权价的持仓
        positions = [
            Position(
                vt_symbol="m2509-C-800.DCE",
                underlying_vt_symbol="m2509.DCE",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="m2509-C-850.DCE",
                underlying_vt_symbol="m2509.DCE",
                signal="open_signal",
                volume=5,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "m2509-C-800.DCE": 0.5,
            "m2509-C-850.DCE": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 800 和 850 应该在同一区间 800-900
        assert len(metrics.strike_concentration) == 1
        assert "800-900" in metrics.strike_concentration
        assert metrics.strike_concentration["800-900"] == 1.0
    
    def test_medium_strike_grouping(self):
        """测试中等行权价的分组（1000-5000，区间 500）"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建中等行权价的持仓
        positions = [
            Position(
                vt_symbol="IO2401-C-4000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="IO2401-C-4200.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=5,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-4000.CFFEX": 0.5,
            "IO2401-C-4200.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 4000 和 4200 应该在同一区间 4000-4500
        assert len(metrics.strike_concentration) == 1
        assert "4000-4500" in metrics.strike_concentration
        assert metrics.strike_concentration["4000-4500"] == 1.0
    
    def test_large_strike_grouping(self):
        """测试大行权价的分组（>= 5000，区间 1000）"""
        config = ConcentrationConfig()
        monitor = ConcentrationMonitor(config)
        
        # 创建大行权价的持仓
        positions = [
            Position(
                vt_symbol="IO2401-C-5000.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=10,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="IO2401-C-5500.CFFEX",
                underlying_vt_symbol="IF2401.CFFEX",
                signal="open_signal",
                volume=5,
                direction="short",
                open_price=0.5,
            ),
        ]
        
        prices = {
            "IO2401-C-5000.CFFEX": 0.5,
            "IO2401-C-5500.CFFEX": 0.5,
        }
        
        metrics = monitor.calculate_concentration(positions, prices)
        
        # 5000 和 5500 应该在同一区间 5000-6000
        assert len(metrics.strike_concentration) == 1
        assert "5000-6000" in metrics.strike_concentration
        assert metrics.strike_concentration["5000-6000"] == 1.0
