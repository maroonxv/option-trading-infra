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


class DeltaNeutralSignalService(ISignalService):
    def __init__(self, open_spread_threshold: float = 0.05, close_spread_threshold: float = 0.01, **kwargs):
        self.open_spread_threshold = float(open_spread_threshold)
        self.close_spread_threshold = float(close_spread_threshold)
        self.config = dict(kwargs)

    def check_open_signal(
        self,
        instrument: "TargetInstrument",
        context: Optional[SignalContext] = None,
    ) -> Optional[SignalDecision]:
        snapshot = instrument.indicators.get("delta_neutral") or {}
        if snapshot.get("vol_spread", 0.0) >= self.open_spread_threshold:
            return SignalDecision(
                action="adjust",
                signal_name="delta_neutral_setup",
                rationale="隐波高于已实现波动率，适合构造中性组合",
                selection_preference=OptionSelectionPreference(
                    combination_type="straddle",
                    target_delta=0.0,
                ),
            )
        return None

    def check_close_signal(
        self,
        instrument: "TargetInstrument",
        position: "Position",
        context: Optional[SignalContext] = None,
    ) -> Optional[SignalDecision]:
        snapshot = instrument.indicators.get("delta_neutral") or {}
        if abs(snapshot.get("vol_spread", 0.0)) <= self.close_spread_threshold:
            return SignalDecision(
                action="close",
                signal_name="delta_neutral_take_profit",
                rationale="波动率价差回归，结束中性结构",
                close_target_symbol=getattr(position, "vt_symbol", ""),
            )
        return None
