"""
SPI 接口定义的单元测试

测试内容:
1. 接口是否可被正确继承
2. ServiceBundle 的字段完整性
"""

import pytest
from dataclasses import fields
from typing import Optional, Any

from src.strategy.domain.interface import (
    IIndicatorService,
    ISignalService,
    IPositionSizingService,
    ServiceBundle,
)


# Mock classes for testing (since TargetInstrument and Position are not yet refactored)
class MockTargetInstrument:
    """模拟 TargetInstrument 用于测试"""
    def __init__(self, vt_symbol: str):
        self.vt_symbol = vt_symbol
        self.indicators: dict = {}
        self.bars = []


class MockPosition:
    """模拟 Position 用于测试"""
    def __init__(self, volume: int = 10):
        self.volume = volume


class ConcreteIndicatorService(IIndicatorService):
    """具体的指标计算服务实现"""

    def calculate_bar(self, instrument: Any, bar: dict) -> None:
        """简单实现：将 bar 数据存储到 indicators"""
        instrument.indicators["test_bar"] = bar


class ConcreteSignalService(ISignalService):
    """具体的信号生成服务实现"""

    def check_open_signal(self, instrument: Any) -> Optional[str]:
        """简单实现：如果有指标数据则返回信号"""
        if instrument.indicators:
            return "test_open_signal"
        return None

    def check_close_signal(
        self, instrument: Any, position: Any
    ) -> Optional[str]:
        """简单实现：如果有指标数据则返回平仓信号"""
        if instrument.indicators:
            return "test_close_signal"
        return None


class ConcretePositionSizingService(IPositionSizingService):
    """具体的仓位计算服务实现"""

    def calculate_open_volume(
        self, desired_volume: int, instrument: Any, account: dict
    ) -> int:
        """简单实现：返回期望手数"""
        return desired_volume

    def calculate_exit_volume(
        self, desired_volume: int, current_position: Any
    ) -> int:
        """简单实现：返回期望手数"""
        return desired_volume


class TestIndicatorServiceInterface:
    """测试 IIndicatorService 接口"""

    def test_indicator_service_can_be_inherited(self):
        """测试 IIndicatorService 可被正确继承"""
        service = ConcreteIndicatorService()
        assert isinstance(service, IIndicatorService)

    def test_indicator_service_calculate_bar_method_exists(self):
        """测试 calculate_bar 方法存在"""
        service = ConcreteIndicatorService()
        assert hasattr(service, "calculate_bar")
        assert callable(service.calculate_bar)

    def test_indicator_service_calculate_bar_updates_indicators(self):
        """测试 calculate_bar 能够更新 indicators 字典"""
        service = ConcreteIndicatorService()
        instrument = MockTargetInstrument(vt_symbol="rb2501.SHFE")
        bar_data = {"open": 3500, "close": 3510, "volume": 1000}

        service.calculate_bar(instrument, bar_data)

        assert "test_bar" in instrument.indicators
        assert instrument.indicators["test_bar"] == bar_data


class TestSignalServiceInterface:
    """测试 ISignalService 接口"""

    def test_signal_service_can_be_inherited(self):
        """测试 ISignalService 可被正确继承"""
        service = ConcreteSignalService()
        assert isinstance(service, ISignalService)

    def test_signal_service_check_open_signal_method_exists(self):
        """测试 check_open_signal 方法存在"""
        service = ConcreteSignalService()
        assert hasattr(service, "check_open_signal")
        assert callable(service.check_open_signal)

    def test_signal_service_check_close_signal_method_exists(self):
        """测试 check_close_signal 方法存在"""
        service = ConcreteSignalService()
        assert hasattr(service, "check_close_signal")
        assert callable(service.check_close_signal)

    def test_signal_service_returns_string_or_none(self):
        """测试信号服务返回字符串或 None"""
        service = ConcreteSignalService()
        instrument = MockTargetInstrument(vt_symbol="rb2501.SHFE")

        # 无指标时返回 None
        signal = service.check_open_signal(instrument)
        assert signal is None

        # 有指标时返回字符串
        instrument.indicators["test"] = True
        signal = service.check_open_signal(instrument)
        assert isinstance(signal, str)
        assert signal == "test_open_signal"


class TestPositionSizingServiceInterface:
    """测试 IPositionSizingService 接口"""

    def test_position_sizing_service_can_be_inherited(self):
        """测试 IPositionSizingService 可被正确继承"""
        service = ConcretePositionSizingService()
        assert isinstance(service, IPositionSizingService)

    def test_position_sizing_service_calculate_open_volume_method_exists(self):
        """测试 calculate_open_volume 方法存在"""
        service = ConcretePositionSizingService()
        assert hasattr(service, "calculate_open_volume")
        assert callable(service.calculate_open_volume)

    def test_position_sizing_service_calculate_exit_volume_method_exists(self):
        """测试 calculate_exit_volume 方法存在"""
        service = ConcretePositionSizingService()
        assert hasattr(service, "calculate_exit_volume")
        assert callable(service.calculate_exit_volume)

    def test_position_sizing_service_returns_integer(self):
        """测试仓位计算服务返回整数"""
        service = ConcretePositionSizingService()
        instrument = MockTargetInstrument(vt_symbol="rb2501.SHFE")
        account = {"available": 100000}

        volume = service.calculate_open_volume(10, instrument, account)
        assert isinstance(volume, int)
        assert volume == 10


class TestServiceBundle:
    """测试 ServiceBundle 数据类"""

    def test_service_bundle_has_all_required_fields(self):
        """测试 ServiceBundle 包含所有必需字段"""
        bundle_fields = {f.name for f in fields(ServiceBundle)}

        required_fields = {
            "indicator_service",
            "signal_service",
            "position_sizing_service",
            "future_selection_service",
            "option_selector_service",
        }

        assert required_fields.issubset(bundle_fields), (
            f"ServiceBundle 缺少必需字段: {required_fields - bundle_fields}"
        )

    def test_service_bundle_can_be_instantiated(self):
        """测试 ServiceBundle 可被实例化"""
        # 创建 mock 对象用于测试
        mock_future_selector = type('MockFutureSelector', (), {})()
        mock_option_selector = type('MockOptionSelector', (), {})()

        bundle = ServiceBundle(
            indicator_service=ConcreteIndicatorService(),
            signal_service=ConcreteSignalService(),
            position_sizing_service=ConcretePositionSizingService(),
            future_selection_service=mock_future_selector,
            option_selector_service=mock_option_selector,
        )

        assert bundle.indicator_service is not None
        assert bundle.signal_service is not None
        assert bundle.position_sizing_service is not None
        assert bundle.future_selection_service is not None
        assert bundle.option_selector_service is not None

    def test_service_bundle_field_types_are_correct(self):
        """测试 ServiceBundle 字段类型正确"""
        # 创建 mock 对象用于测试
        mock_future_selector = type('MockFutureSelector', (), {})()
        mock_option_selector = type('MockOptionSelector', (), {})()

        bundle = ServiceBundle(
            indicator_service=ConcreteIndicatorService(),
            signal_service=ConcreteSignalService(),
            position_sizing_service=ConcretePositionSizingService(),
            future_selection_service=mock_future_selector,
            option_selector_service=mock_option_selector,
        )

        assert isinstance(bundle.indicator_service, IIndicatorService)
        assert isinstance(bundle.signal_service, ISignalService)
        assert isinstance(bundle.position_sizing_service, IPositionSizingService)
