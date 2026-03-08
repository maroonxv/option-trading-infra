"""Signal 子模块 - 信号相关值对象。"""

from .signal_type import SignalType
from .strategy_contract import (
    DecisionTrace,
    IndicatorComputationResult,
    IndicatorContext,
    OptionSelectionPreference,
    PipelineStageRecord,
    SignalContext,
    SignalDecision,
)

__all__ = [
    "SignalType",
    "IndicatorContext",
    "IndicatorComputationResult",
    "SignalContext",
    "SignalDecision",
    "OptionSelectionPreference",
    "PipelineStageRecord",
    "DecisionTrace",
]
