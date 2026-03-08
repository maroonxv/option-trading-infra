from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from src.strategy.domain.domain_service.signal.indicator_service import IIndicatorService
from src.strategy.domain.value_object.signal import IndicatorComputationResult, IndicatorContext

if TYPE_CHECKING:
    from src.strategy.domain.entity.target_instrument import TargetInstrument


class IvRankIndicatorService(IIndicatorService):
    def __init__(self, lookback: int = 20, **kwargs):
        self.lookback = int(lookback)
        self.config = dict(kwargs)

    def calculate_bar(
        self,
        instrument: "TargetInstrument",
        bar: dict,
        context: Optional[IndicatorContext] = None,
    ) -> IndicatorComputationResult:
        option_chain = context.option_chain if context else None
        iv_values = [
            entry.quote.implied_volatility
            for entry in getattr(option_chain, "entries", [])
            if entry.quote.implied_volatility is not None
        ]
        if not iv_values:
            return IndicatorComputationResult.noop(summary="当前期权链无可用 IV")

        avg_iv = float(sum(iv_values) / len(iv_values))
        history = list(instrument.indicators.get("iv_rank_history", []))
        history.append(avg_iv)
        history = history[-self.lookback:]
        iv_min = min(history)
        iv_max = max(history)
        iv_rank = 0.0 if iv_max == iv_min else (avg_iv - iv_min) / (iv_max - iv_min)

        instrument.indicators["iv_rank_history"] = history
        instrument.indicators["iv_rank"] = {
            "avg_iv": avg_iv,
            "iv_rank": iv_rank,
            "history_size": len(history),
        }
        return IndicatorComputationResult(
            indicator_key="iv_rank",
            updated_indicator_keys=["iv_rank", "iv_rank_history"],
            values=dict(instrument.indicators["iv_rank"]),
            summary="IV Rank 已更新",
        )
