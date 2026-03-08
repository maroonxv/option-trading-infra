"""
IndicatorService - 指标计算领域服务（模板）

本文件是框架模板，提供指标计算服务的骨架结构。
使用本模板时，请根据你的策略需求实现具体的指标计算逻辑。

═══════════════════════════════════════════════════════════════════
  开发指南
═══════════════════════════════════════════════════════════════════

1. 本类实现 IIndicatorService 接口，负责在每根 K 线到达时计算技术指标。

2. 计算结果应写入 instrument.indicators 字典，例如:
   - instrument.indicators['my_indicator'] = {'value': 42.0, 'signal': True}
   - 键名和数据结构完全由你自定义，框架不做任何约束。

3. 典型的指标计算流程:
   a. 从 instrument.bars (pd.DataFrame) 读取历史 K 线数据
   b. 使用 pandas / numpy / ta-lib 等库计算指标
   c. 将结果写入 instrument.indicators 字典

4. 如果你的策略需要多个指标，建议:
   - 在 calculation_service/ 目录下为每个指标创建独立的计算服务
   - 在本类中协调调用各计算服务
   - 或者直接在 calculate_bar() 中实现所有计算

5. 直接在本文件中实现你的指标计算逻辑即可
"""
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

from ...value_object.signal.strategy_contract import (
    IndicatorComputationResult,
    IndicatorContext,
)

if TYPE_CHECKING:
    from ...entity.target_instrument import TargetInstrument


class IIndicatorService(ABC):
    """指标计算服务接口"""

    @abstractmethod
    def calculate_bar(
        self,
        instrument: "TargetInstrument",
        bar: dict,
        context: Optional[IndicatorContext] = None,
    ) -> IndicatorComputationResult:
        """K 线更新时的指标计算逻辑"""
        raise NotImplementedError


class IndicatorService(IIndicatorService):
    """
    指标计算服务（模板）

    使用时请根据策略需求:
    1. 在 __init__ 中定义指标参数（周期、阈值等）
    2. 在 calculate_bar() 中实现指标计算逻辑
    3. 将计算结果写入 instrument.indicators 字典
    """

    def __init__(self, **kwargs):
        """
        初始化指标服务

        TODO: 根据策略需求添加参数，例如:
            def __init__(self, fast_period=12, slow_period=26):
                self.fast_period = fast_period
                self.slow_period = slow_period
        """
        self.config = dict(kwargs)

    def calculate_bar(
        self,
        instrument: "TargetInstrument",
        bar: dict,
        context: Optional[IndicatorContext] = None,
    ) -> IndicatorComputationResult:
        """
        K 线更新时的指标计算逻辑

        TODO: 实现你的指标计算，例如:
            bars = instrument.bars
            if len(bars) < self.min_bars:
                return

            close = bars['close']
            fast_ema = close.ewm(span=self.fast_period, adjust=False).mean().iloc[-1]
            slow_ema = close.ewm(span=self.slow_period, adjust=False).mean().iloc[-1]

            instrument.indicators['ema'] = {
                'fast': float(fast_ema),
                'slow': float(slow_ema),
            }

        Args:
            instrument: 标的实体，包含历史 K 线数据 (instrument.bars)
            bar: 新 K 线数据字典 (datetime, open, high, low, close, volume)
        """
        summary = "未配置具体指标逻辑，返回空指标结果"
        instrument.indicators.setdefault("_contract", {})["indicator_service"] = {
            "service": type(self).__name__,
            "summary": summary,
            "last_bar_dt": bar.get("datetime"),
        }
        if context is not None:
            instrument.indicators["_contract"]["indicator_context"] = {
                "vt_symbol": context.vt_symbol,
                "underlying_price": context.underlying_price,
            }
        return IndicatorComputationResult.noop(summary=summary)
