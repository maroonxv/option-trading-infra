"""
LiquidityRiskMonitor 单元测试

测试持仓流动性监控服务的流动性评分计算、趋势识别和警告触发功能。
"""
import pytest
from datetime import datetime, timedelta

from src.strategy.domain.domain_service.risk.liquidity_risk_monitor import LiquidityRiskMonitor
from src.strategy.domain.entity.position import Position
from src.strategy.domain.value_object.risk.risk import (
    LiquidityMonitorConfig,
    MarketData,
    LiquidityScore,
    LiquidityWarning,
)


class TestLiquidityRiskMonitorConfig:
    """测试流动性监控配置"""
    
    def test_valid_config(self):
        """测试有效配置"""
        config = LiquidityMonitorConfig(
            volume_weight=0.4,
            spread_weight=0.3,
            open_interest_weight=0.3,
            liquidity_score_threshold=0.3,
            lookback_days=5,
        )
        monitor = LiquidityRiskMonitor(config)
        assert monitor is not None
    
    def test_invalid_config_weight_sum_not_one(self):
        """测试权重总和不等于 1.0 的配置"""
        config = LiquidityMonitorConfig(
            volume_weight=0.5,
            spread_weight=0.3,
            open_interest_weight=0.3,  # 总和 = 1.1
        )
        with pytest.raises(ValueError, match="权重总和必须等于 1.0"):
            LiquidityRiskMonitor(config)


class TestLiquidityScoreCalculation:
    """测试流动性评分计算"""
    
    def test_calculate_liquidity_score_with_historical_data(self):
        """测试有历史数据时的流动性评分计算"""
        config = LiquidityMonitorConfig(
            volume_weight=0.4,
            spread_weight=0.3,
            open_interest_weight=0.3,
        )
        monitor = LiquidityRiskMonitor(config)
        
        # 创建历史数据（5天）
        base_time = datetime(2024, 1, 1, 9, 30)
        historical_data = [
            MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=base_time + timedelta(days=i),
                volume=1000.0,
                bid_price=0.5,
                ask_price=0.51,
                open_interest=5000.0,
            )
            for i in range(5)
        ]
        
        # 当前数据：成交量和持仓量与历史平均相同，价差相同
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=base_time + timedelta(days=5),
            volume=1000.0,
            bid_price=0.5,
            ask_price=0.51,
            open_interest=5000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, historical_data
        )
        
        assert score.vt_symbol == "10005000C2412.SSE"
        assert 0.0 <= score.overall_score <= 1.0
        assert 0.0 <= score.volume_score <= 1.0
        assert 0.0 <= score.spread_score <= 1.0
        assert 0.0 <= score.open_interest_score <= 1.0
        assert score.trend in ["improving", "stable", "deteriorating"]
        
        # 验证综合评分是加权平均
        expected_overall = (
            score.volume_score * 0.4 +
            score.spread_score * 0.3 +
            score.open_interest_score * 0.3
        )
        assert abs(score.overall_score - expected_overall) < 1e-6
    
    def test_calculate_liquidity_score_without_historical_data(self):
        """测试无历史数据时的流动性评分计算"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 当前数据：良好的流动性
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=2000.0,  # > 1000，应该得到高分
            bid_price=0.5,
            ask_price=0.505,  # 相对价差 1%
            open_interest=10000.0,  # > 5000，应该得到高分
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, []
        )
        
        assert score.vt_symbol == "10005000C2412.SSE"
        assert 0.0 <= score.overall_score <= 1.0
        assert score.trend == "stable"  # 无历史数据，趋势为 stable
    
    def test_volume_score_high_volume(self):
        """测试高成交量的评分"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 历史平均成交量 1000
        historical_data = [
            MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=datetime.now(),
                volume=1000.0,
                bid_price=0.5,
                ask_price=0.51,
                open_interest=5000.0,
            )
            for _ in range(5)
        ]
        
        # 当前成交量 1500（高于历史平均）
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1500.0,
            bid_price=0.5,
            ask_price=0.51,
            open_interest=5000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, historical_data
        )
        
        # 成交量是历史平均的 1.5 倍，但评分上限为 1.0
        assert score.volume_score == 1.0

    def test_spread_score_narrow_spread(self):
        """测试窄价差的评分"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 窄价差：相对价差 0.5%
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1000.0,
            bid_price=0.5,
            ask_price=0.5025,  # 相对价差 = 0.0025 / 0.50125 ≈ 0.5%
            open_interest=5000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, []
        )
        
        # 窄价差应该得到高分
        assert score.spread_score > 0.9
    
    def test_spread_score_wide_spread(self):
        """测试宽价差的评分"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 宽价差：相对价差 5%
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1000.0,
            bid_price=0.5,
            ask_price=0.525,  # 相对价差 = 0.025 / 0.5125 ≈ 4.88%
            open_interest=5000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, []
        )
        
        # 宽价差应该得到低分
        assert score.spread_score < 0.7
    
    def test_open_interest_score_high_oi(self):
        """测试高持仓量的评分"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 历史平均持仓量 5000
        historical_data = [
            MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=datetime.now(),
                volume=1000.0,
                bid_price=0.5,
                ask_price=0.51,
                open_interest=5000.0,
            )
            for _ in range(5)
        ]
        
        # 当前持仓量 7500（高于历史平均）
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1000.0,
            bid_price=0.5,
            ask_price=0.51,
            open_interest=7500.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, historical_data
        )
        
        # 持仓量是历史平均的 1.5 倍，但评分上限为 1.0
        assert score.open_interest_score == 1.0


class TestLiquidityTrendIdentification:
    """测试流动性趋势识别"""
    
    def test_trend_improving(self):
        """测试流动性改善趋势"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 历史数据：成交量 1000，价差 2%，持仓量 5000
        base_time = datetime(2024, 1, 1, 9, 30)
        historical_data = [
            MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=base_time + timedelta(days=i),
                volume=1000.0,
                bid_price=0.5,
                ask_price=0.51,  # 相对价差 ≈ 1.98%
                open_interest=5000.0,
            )
            for i in range(5)
        ]
        
        # 当前数据：成交量增加 20%，价差缩小到 1%，持仓量增加 20%
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=base_time + timedelta(days=5),
            volume=1200.0,  # 增加 20%
            bid_price=0.5,
            ask_price=0.505,  # 相对价差 ≈ 0.99%，缩小超过 10%
            open_interest=6000.0,  # 增加 20%
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, historical_data
        )
        
        # 三个维度都改善，应该识别为 improving
        assert score.trend == "improving"
    
    def test_trend_deteriorating(self):
        """测试流动性恶化趋势"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 历史数据：成交量 1000，价差 1%，持仓量 5000
        base_time = datetime(2024, 1, 1, 9, 30)
        historical_data = [
            MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=base_time + timedelta(days=i),
                volume=1000.0,
                bid_price=0.5,
                ask_price=0.505,  # 相对价差 ≈ 0.99%
                open_interest=5000.0,
            )
            for i in range(5)
        ]
        
        # 当前数据：成交量减少 20%，价差扩大到 2%，持仓量减少 20%
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=base_time + timedelta(days=5),
            volume=800.0,  # 减少 20%
            bid_price=0.5,
            ask_price=0.51,  # 相对价差 ≈ 1.98%，扩大超过 10%
            open_interest=4000.0,  # 减少 20%
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, historical_data
        )
        
        # 三个维度都恶化，应该识别为 deteriorating
        assert score.trend == "deteriorating"

    def test_trend_stable(self):
        """测试流动性稳定趋势"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 历史数据
        base_time = datetime(2024, 1, 1, 9, 30)
        historical_data = [
            MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=base_time + timedelta(days=i),
                volume=1000.0,
                bid_price=0.5,
                ask_price=0.505,
                open_interest=5000.0,
            )
            for i in range(5)
        ]
        
        # 当前数据：与历史平均基本相同（变化小于 10%）
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=base_time + timedelta(days=5),
            volume=1050.0,  # 增加 5%
            bid_price=0.5,
            ask_price=0.506,  # 价差略微扩大
            open_interest=5100.0,  # 增加 2%
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, historical_data
        )
        
        # 变化不明显，应该识别为 stable
        assert score.trend == "stable"
    
    def test_trend_mixed_signals(self):
        """测试混合信号的趋势识别"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 历史数据
        base_time = datetime(2024, 1, 1, 9, 30)
        historical_data = [
            MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=base_time + timedelta(days=i),
                volume=1000.0,
                bid_price=0.5,
                ask_price=0.505,
                open_interest=5000.0,
            )
            for i in range(5)
        ]
        
        # 当前数据：成交量增加，但价差扩大
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=base_time + timedelta(days=5),
            volume=1200.0,  # 增加 20%（改善信号）
            bid_price=0.5,
            ask_price=0.512,  # 价差扩大超过 10%（恶化信号）
            open_interest=5050.0,  # 基本不变
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, historical_data
        )
        
        # 混合信号，应该识别为 stable
        assert score.trend == "stable"


class TestLiquidityWarningTrigger:
    """测试流动性警告触发"""
    
    def test_warning_triggered_low_score(self):
        """测试低流动性评分触发警告"""
        config = LiquidityMonitorConfig(
            volume_weight=0.4,
            spread_weight=0.3,
            open_interest_weight=0.3,
            liquidity_score_threshold=0.5,
        )
        monitor = LiquidityRiskMonitor(config)
        
        # 创建持仓
        positions = [
            Position(
                vt_symbol="10005000C2412.SSE",
                underlying_vt_symbol="510050.SSE",
                signal="open_signal",
                volume=2,
                direction="short",
                open_price=0.5,
            )
        ]
        
        # 市场数据：低流动性（低成交量、宽价差、低持仓量）
        market_data = {
            "10005000C2412.SSE": MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=datetime.now(),
                volume=100.0,  # 很低
                bid_price=0.5,
                ask_price=0.55,  # 宽价差 ≈ 9.5%
                open_interest=500.0,  # 很低
            )
        }
        
        historical_data = {}
        
        warnings = monitor.monitor_positions(positions, market_data, historical_data)
        
        assert len(warnings) == 1
        assert warnings[0].vt_symbol == "10005000C2412.SSE"
        assert warnings[0].current_score < 0.5
        assert warnings[0].threshold == 0.5
        assert "流动性恶化警告" in warnings[0].message
    
    def test_warning_not_triggered_high_score(self):
        """测试高流动性评分不触发警告"""
        config = LiquidityMonitorConfig(
            liquidity_score_threshold=0.3,
        )
        monitor = LiquidityRiskMonitor(config)
        
        # 创建持仓
        positions = [
            Position(
                vt_symbol="10005000C2412.SSE",
                underlying_vt_symbol="510050.SSE",
                signal="open_signal",
                volume=2,
                direction="short",
                open_price=0.5,
            )
        ]
        
        # 市场数据：高流动性
        market_data = {
            "10005000C2412.SSE": MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=datetime.now(),
                volume=2000.0,
                bid_price=0.5,
                ask_price=0.505,  # 窄价差
                open_interest=10000.0,
            )
        }
        
        historical_data = {}
        
        warnings = monitor.monitor_positions(positions, market_data, historical_data)
        
        assert len(warnings) == 0

    def test_multiple_positions_mixed_warnings(self):
        """测试多个持仓的混合警告场景"""
        config = LiquidityMonitorConfig(
            liquidity_score_threshold=0.4,
        )
        monitor = LiquidityRiskMonitor(config)
        
        # 创建多个持仓
        positions = [
            Position(
                vt_symbol="10005000C2412.SSE",
                underlying_vt_symbol="510050.SSE",
                signal="open_signal",
                volume=2,
                direction="short",
                open_price=0.5,
            ),
            Position(
                vt_symbol="10005100C2412.SSE",
                underlying_vt_symbol="510050.SSE",
                signal="open_signal",
                volume=3,
                direction="short",
                open_price=0.6,
            ),
        ]
        
        # 市场数据：一个低流动性，一个高流动性
        market_data = {
            "10005000C2412.SSE": MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=datetime.now(),
                volume=100.0,  # 低
                bid_price=0.5,
                ask_price=0.55,  # 宽价差
                open_interest=500.0,  # 低
            ),
            "10005100C2412.SSE": MarketData(
                vt_symbol="10005100C2412.SSE",
                timestamp=datetime.now(),
                volume=2000.0,  # 高
                bid_price=0.6,
                ask_price=0.605,  # 窄价差
                open_interest=10000.0,  # 高
            ),
        }
        
        historical_data = {}
        
        warnings = monitor.monitor_positions(positions, market_data, historical_data)
        
        # 只有一个持仓触发警告
        assert len(warnings) == 1
        assert warnings[0].vt_symbol == "10005000C2412.SSE"


class TestBoundaryConditions:
    """测试边界情况"""
    
    def test_zero_volume(self):
        """测试零成交量"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=0.0,  # 零成交量
            bid_price=0.5,
            ask_price=0.51,
            open_interest=5000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, []
        )
        
        # 零成交量应该得到 0 分
        assert score.volume_score == 0.0
        assert 0.0 <= score.overall_score <= 1.0
    
    def test_zero_open_interest(self):
        """测试零持仓量"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1000.0,
            bid_price=0.5,
            ask_price=0.51,
            open_interest=0.0,  # 零持仓量
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, []
        )
        
        # 零持仓量应该得到 0 分
        assert score.open_interest_score == 0.0
        assert 0.0 <= score.overall_score <= 1.0
    
    def test_invalid_spread_bid_greater_than_ask(self):
        """测试无效价差（买价大于卖价）"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1000.0,
            bid_price=0.51,  # 买价大于卖价
            ask_price=0.5,
            open_interest=5000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, []
        )
        
        # 无效价差应该得到 0 分
        assert score.spread_score == 0.0
    
    def test_zero_bid_price(self):
        """测试零买价"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1000.0,
            bid_price=0.0,  # 零买价
            ask_price=0.5,
            open_interest=5000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, []
        )
        
        # 零买价应该得到 0 分
        assert score.spread_score == 0.0
    
    def test_extremely_wide_spread(self):
        """测试极宽价差"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1000.0,
            bid_price=0.5,
            ask_price=1.0,  # 相对价差 ≈ 66.7%
            open_interest=5000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, []
        )
        
        # 极宽价差应该得到接近 0 的分数
        assert score.spread_score < 0.01

    def test_empty_historical_data(self):
        """测试空历史数据"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1000.0,
            bid_price=0.5,
            ask_price=0.51,
            open_interest=5000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, []
        )
        
        # 空历史数据应该使用简单归一化
        assert score.trend == "stable"
        assert 0.0 <= score.overall_score <= 1.0
    
    def test_single_historical_data_point(self):
        """测试单个历史数据点"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        historical_data = [
            MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=datetime.now(),
                volume=1000.0,
                bid_price=0.5,
                ask_price=0.51,
                open_interest=5000.0,
            )
        ]
        
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1200.0,
            bid_price=0.5,
            ask_price=0.51,
            open_interest=6000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, historical_data
        )
        
        # 单个历史数据点，趋势识别需要至少 2 个点
        assert score.trend == "stable"
    
    def test_inactive_position_not_monitored(self):
        """测试非活跃持仓不被监控"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 创建非活跃持仓
        positions = [
            Position(
                vt_symbol="10005000C2412.SSE",
                underlying_vt_symbol="510050.SSE",
                signal="open_signal",
                volume=0,  # 无持仓
                direction="short",
                open_price=0.5,
                is_closed=True,
            )
        ]
        
        # 市场数据：低流动性
        market_data = {
            "10005000C2412.SSE": MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=datetime.now(),
                volume=100.0,
                bid_price=0.5,
                ask_price=0.55,
                open_interest=500.0,
            )
        }
        
        warnings = monitor.monitor_positions(positions, market_data, {})
        
        # 非活跃持仓不应该生成警告
        assert len(warnings) == 0
    
    def test_missing_market_data(self):
        """测试缺失市场数据"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 创建持仓
        positions = [
            Position(
                vt_symbol="10005000C2412.SSE",
                underlying_vt_symbol="510050.SSE",
                signal="open_signal",
                volume=2,
                direction="short",
                open_price=0.5,
            )
        ]
        
        # 市场数据为空（缺失该合约的数据）
        market_data = {}
        
        warnings = monitor.monitor_positions(positions, market_data, {})
        
        # 缺失市场数据不应该生成警告
        assert len(warnings) == 0
    
    def test_empty_positions_list(self):
        """测试空持仓列表"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        positions = []
        market_data = {}
        
        warnings = monitor.monitor_positions(positions, market_data, {})
        
        # 空持仓列表不应该生成警告
        assert len(warnings) == 0
    
    def test_historical_data_with_zero_average_volume(self):
        """测试历史数据平均成交量为零"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 历史数据：所有成交量为 0
        historical_data = [
            MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=datetime.now(),
                volume=0.0,
                bid_price=0.5,
                ask_price=0.51,
                open_interest=5000.0,
            )
            for _ in range(5)
        ]
        
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1000.0,
            bid_price=0.5,
            ask_price=0.51,
            open_interest=5000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, historical_data
        )
        
        # 历史平均为 0，应该返回 0 分
        assert score.volume_score == 0.0
    
    def test_historical_data_with_zero_average_oi(self):
        """测试历史数据平均持仓量为零"""
        config = LiquidityMonitorConfig()
        monitor = LiquidityRiskMonitor(config)
        
        # 历史数据：所有持仓量为 0
        historical_data = [
            MarketData(
                vt_symbol="10005000C2412.SSE",
                timestamp=datetime.now(),
                volume=1000.0,
                bid_price=0.5,
                ask_price=0.51,
                open_interest=0.0,
            )
            for _ in range(5)
        ]
        
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=1000.0,
            bid_price=0.5,
            ask_price=0.51,
            open_interest=5000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, historical_data
        )
        
        # 历史平均为 0，应该返回 0 分
        assert score.open_interest_score == 0.0


class TestWeightedScoreCalculation:
    """测试加权评分计算"""
    
    def test_custom_weights(self):
        """测试自定义权重"""
        config = LiquidityMonitorConfig(
            volume_weight=0.5,
            spread_weight=0.3,
            open_interest_weight=0.2,
        )
        monitor = LiquidityRiskMonitor(config)
        
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=2000.0,
            bid_price=0.5,
            ask_price=0.505,
            open_interest=10000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, []
        )
        
        # 验证综合评分是加权平均
        expected_overall = (
            score.volume_score * 0.5 +
            score.spread_score * 0.3 +
            score.open_interest_score * 0.2
        )
        assert abs(score.overall_score - expected_overall) < 1e-6
    
    def test_equal_weights(self):
        """测试等权重"""
        config = LiquidityMonitorConfig(
            volume_weight=1.0 / 3,
            spread_weight=1.0 / 3,
            open_interest_weight=1.0 / 3,
        )
        monitor = LiquidityRiskMonitor(config)
        
        current_data = MarketData(
            vt_symbol="10005000C2412.SSE",
            timestamp=datetime.now(),
            volume=2000.0,
            bid_price=0.5,
            ask_price=0.505,
            open_interest=10000.0,
        )
        
        score = monitor.calculate_liquidity_score(
            "10005000C2412.SSE", current_data, []
        )
        
        # 验证综合评分是简单平均
        expected_overall = (
            score.volume_score + score.spread_score + score.open_interest_score
        ) / 3.0
        assert abs(score.overall_score - expected_overall) < 1e-6
