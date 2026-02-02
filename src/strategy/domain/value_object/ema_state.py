"""
EMAState 值对象 - 均线状态快照

存储某一时刻的 EMA 均线状态，不可变对象。
"""
from dataclasses import dataclass
from typing import Literal


TrendStatus = Literal["up", "down", "neutral"]


@dataclass(frozen=True)
class EMAState:
    """
    EMA 均线状态快照值对象
    
    Attributes:
        fast_ema: 快速均线值 (如 EMA5)
        slow_ema: 慢速均线值 (如 EMA20)
        trend_status: 趋势状态 ('up', 'down', 'neutral')
    """
    fast_ema: float
    slow_ema: float
    trend_status: TrendStatus
    
    @property
    def is_bullish(self) -> bool:
        """判断是否为多头排列 (快线在慢线上方)"""
        return self.fast_ema > self.slow_ema
    
    @property
    def is_bearish(self) -> bool:
        """判断是否为空头排列 (快线在慢线下方)"""
        return self.fast_ema < self.slow_ema
    
    @property
    def is_uptrend(self) -> bool:
        """判断是否处于上升趋势"""
        return self.trend_status == "up"
    
    @property
    def is_downtrend(self) -> bool:
        """判断是否处于下降趋势"""
        return self.trend_status == "down"
    
    @property
    def spread(self) -> float:
        """快慢均线差值"""
        return self.fast_ema - self.slow_ema
    
    @property
    def spread_pct(self) -> float:
        """快慢均线差值百分比"""
        if self.slow_ema == 0:
            return 0.0
        return (self.fast_ema - self.slow_ema) / self.slow_ema * 100
    
    def __repr__(self) -> str:
        return f"EMAState(fast={self.fast_ema:.4f}, slow={self.slow_ema:.4f}, trend={self.trend_status})"
