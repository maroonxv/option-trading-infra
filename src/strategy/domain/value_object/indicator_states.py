"""
IndicatorResultDTO - 指标计算结果数据传输对象

聚合所有指标计算结果，用于 IndicatorService 向调用方返回统一结果。
"""
from dataclasses import dataclass
from typing import Optional

from .macd_value import MACDValue
from .td_value import TDValue
from .ema_state import EMAState
from .dullness_state import DullnessState
from .divergence_state import DivergenceState


@dataclass
class IndicatorResultDTO:
    """
    指标计算结果数据传输对象
    
    由 IndicatorService.calculate_all() 返回，
    包含所有指标的计算结果和状态更新。
    
    Attributes:
        macd_value: MACD 指标值
        td_value: TD 序列值
        ema_state: EMA 均线状态
        dullness_state: 钝化状态
        divergence_state: 背离状态
    """
    macd_value: Optional[MACDValue] = None
    td_value: Optional[TDValue] = None
    ema_state: Optional[EMAState] = None
    dullness_state: Optional[DullnessState] = None
    divergence_state: Optional[DivergenceState] = None
    
    @property
    def is_complete(self) -> bool:
        """判断所有指标是否都已计算完成"""
        return all([
            self.macd_value is not None,
            self.td_value is not None,
            self.ema_state is not None,
            self.dullness_state is not None,
            self.divergence_state is not None,
        ])
    
    def __repr__(self) -> str:
        parts = []
        if self.macd_value:
            parts.append(f"MACD={self.macd_value.macd_bar:.4f}")
        if self.td_value:
            parts.append(f"TD={self.td_value.td_count}")
        if self.ema_state:
            parts.append(f"趋势={self.ema_state.trend_status}")
        if self.dullness_state and self.dullness_state.is_active:
            parts.append("钝化=激活")
        if self.divergence_state and self.divergence_state.is_confirmed:
            parts.append("背离=确认")
        return f"IndicatorResultDTO({', '.join(parts)})"
