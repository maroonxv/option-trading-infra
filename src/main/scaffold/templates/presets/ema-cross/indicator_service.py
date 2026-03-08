from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from src.strategy.domain.domain_service.signal.indicator_service import IIndicatorService
from src.strategy.domain.value_object.signal import IndicatorComputationResult, IndicatorContext

if TYPE_CHECKING:
    from src.strategy.domain.entity.target_instrument import TargetInstrument


class EmaCrossIndicatorService(IIndicatorService):
    def __init__(self, fast_period: int = 8, slow_period: int = 21, **kwargs):
        self.fast_period = int(fast_period)
        self.slow_period = int(slow_period)
        self.config = dict(kwargs)

    def calculate_bar(
        self,
        instrument: "TargetInstrument",
        bar: dict,
        context: Optional[IndicatorContext] = None,
    ) -> IndicatorComputationResult:
        bars = instrument.bars
        if len(bars) < self.slow_period:
            return IndicatorComputationResult.noop(summary="EMA 样本不足")

        close = bars["close"].astype(float)
        fast_series = close.ewm(span=self.fast_period, adjust=False).mean()
        slow_series = close.ewm(span=self.slow_period, adjust=False).mean()
        prev_fast = float(fast_series.iloc[-2])
        prev_slow = float(slow_series.iloc[-2])
        fast = float(fast_series.iloc[-1])
        slow = float(slow_series.iloc[-1])

        payload = {
            "fast": fast,
            "slow": slow,
            "prev_fast": prev_fast,
            "prev_slow": prev_slow,
        }
        instrument.indicators["ema_cross"] = payload
        return IndicatorComputationResult(
            indicator_key="ema_cross",
            updated_indicator_keys=["ema_cross"],
            values=payload,
            summary="EMA Cross 指标已更新",
        )
