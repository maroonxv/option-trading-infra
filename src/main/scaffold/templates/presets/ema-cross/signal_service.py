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


class EmaCrossSignalService(ISignalService):
    def __init__(self, option_type: str = "call", strike_level: int = 1, **kwargs):
        self.option_type = option_type
        self.strike_level = int(strike_level)
        self.config = dict(kwargs)

    def check_open_signal(
        self,
        instrument: "TargetInstrument",
        context: Optional[SignalContext] = None,
    ) -> Optional[SignalDecision]:
        ema = instrument.indicators.get("ema_cross") or {}
        if not ema:
            return None
        if ema["prev_fast"] <= ema["prev_slow"] and ema["fast"] > ema["slow"]:
            return SignalDecision(
                action="open",
                signal_name="ema_cross_up",
                rationale="快线向上穿越慢线",
                selection_preference=OptionSelectionPreference(
                    option_type=self.option_type,
                    strike_level=self.strike_level,
                ),
            )
        return None

    def check_close_signal(
        self,
        instrument: "TargetInstrument",
        position: "Position",
        context: Optional[SignalContext] = None,
    ) -> Optional[SignalDecision]:
        ema = instrument.indicators.get("ema_cross") or {}
        if not ema:
            return None
        if ema["prev_fast"] >= ema["prev_slow"] and ema["fast"] < ema["slow"]:
            return SignalDecision(
                action="close",
                signal_name="ema_cross_down",
                rationale="快线向下跌破慢线",
                close_target_symbol=getattr(position, "vt_symbol", ""),
            )
        return None
