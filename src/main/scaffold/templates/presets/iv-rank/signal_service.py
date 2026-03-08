from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from src.strategy.domain.domain_service.signal.signal_service import ISignalService
from src.strategy.domain.value_object.signal import (
    OptionSelectionPreference,
    SignalContext,
    SignalDecision,
)

if TYPE_CHECKING:
    from src.strategy.domain.entity.position import Position
    from src.strategy.domain.entity.target_instrument import TargetInstrument


class IvRankSignalService(ISignalService):
    def __init__(self, entry_rank: float = 0.7, exit_rank: float = 0.4, **kwargs):
        self.entry_rank = float(entry_rank)
        self.exit_rank = float(exit_rank)
        self.config = dict(kwargs)

    def check_open_signal(
        self,
        instrument: "TargetInstrument",
        context: Optional[SignalContext] = None,
    ) -> Optional[SignalDecision]:
        snapshot = instrument.indicators.get("iv_rank") or {}
        if snapshot.get("iv_rank", 0.0) >= self.entry_rank:
            return SignalDecision(
                action="open",
                signal_name="iv_rank_high",
                rationale=f"IV Rank 高于阈值 {self.entry_rank}",
                selection_preference=OptionSelectionPreference(
                    option_type="put",
                    strike_level=2,
                    side="sell",
                ),
            )
        return None

    def check_close_signal(
        self,
        instrument: "TargetInstrument",
        position: "Position",
        context: Optional[SignalContext] = None,
    ) -> Optional[SignalDecision]:
        snapshot = instrument.indicators.get("iv_rank") or {}
        if snapshot.get("iv_rank", 0.0) <= self.exit_rank:
            return SignalDecision(
                action="close",
                signal_name="iv_rank_mean_revert",
                rationale=f"IV Rank 回落到阈值 {self.exit_rank} 以下",
                close_target_symbol=getattr(position, "vt_symbol", ""),
            )
        return None
