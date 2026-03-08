from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from src.strategy.domain.domain_service.signal.indicator_service import IIndicatorService
from src.strategy.domain.value_object.signal import IndicatorComputationResult, IndicatorContext

if TYPE_CHECKING:
    from src.strategy.domain.entity.target_instrument import TargetInstrument


class DeltaNeutralIndicatorService(IIndicatorService):
    def __init__(self, rv_window: int = 20, **kwargs):
        self.rv_window = int(rv_window)
        self.config = dict(kwargs)

    def calculate_bar(
        self,
        instrument: "TargetInstrument",
        bar: dict,
        context: Optional[IndicatorContext] = None,
    ) -> IndicatorComputationResult:
        bars = instrument.bars
        if len(bars) < self.rv_window + 1:
            return IndicatorComputationResult.noop(summary="历史波动率样本不足")

        close = bars["close"].astype(float)
        returns = close.pct_change().dropna().tail(self.rv_window)
        realized_vol = float(returns.std() * (252 ** 0.5)) if not returns.empty else 0.0

        option_chain = context.option_chain if context else None
        iv_values = [
            entry.quote.implied_volatility
            for entry in getattr(option_chain, "entries", [])
            if entry.quote.implied_volatility is not None
        ]
        avg_iv = float(sum(iv_values) / len(iv_values)) if iv_values else 0.0

        instrument.indicators["delta_neutral"] = {
            "realized_vol": realized_vol,
            "avg_iv": avg_iv,
            "vol_spread": avg_iv - realized_vol,
        }
        return IndicatorComputationResult(
            indicator_key="delta_neutral",
            updated_indicator_keys=["delta_neutral"],
            values=dict(instrument.indicators["delta_neutral"]),
            summary="Delta Neutral 指标已更新",
        )
