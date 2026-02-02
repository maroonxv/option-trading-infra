"""
DivergenceState 值对象 - MACD 背离状态

记录 MACD 顶/底背离的确认状态和相关参数，不可变对象。
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class DivergenceState:
    """
    MACD 背离状态值对象
    
    背离定义:
    - 顶背离: 价格创新高，但 MACD 未创新高
    - 底背离: 价格创新低，但 MACD 未创新低
    
    Attributes:
        is_top_confirmed: 顶背离是否已确认
        is_bottom_confirmed: 底背离是否已确认
        confirm_time: 背离确认时间
        confirm_price: 背离确认时的价格
        confirm_diff: 背离确认时的 DIF 值
    """
    is_top_confirmed: bool = False
    is_bottom_confirmed: bool = False
    confirm_time: Optional[datetime] = None
    confirm_price: float = 0.0
    confirm_diff: float = 0.0
    
    @property
    def is_confirmed(self) -> bool:
        """判断是否有任何背离已确认"""
        return self.is_top_confirmed or self.is_bottom_confirmed
    
    def with_top_confirmed(
        self,
        confirm_time: datetime,
        confirm_price: float,
        confirm_diff: float
    ) -> "DivergenceState":
        """
        返回一个顶背离确认的状态
        
        Args:
            confirm_time: 确认时间
            confirm_price: 确认时的价格
            confirm_diff: 确认时的 DIF 值
            
        Returns:
            新的 DivergenceState 对象
        """
        return DivergenceState(
            is_top_confirmed=True,
            is_bottom_confirmed=False,
            confirm_time=confirm_time,
            confirm_price=confirm_price,
            confirm_diff=confirm_diff,
        )
    
    def with_bottom_confirmed(
        self,
        confirm_time: datetime,
        confirm_price: float,
        confirm_diff: float
    ) -> "DivergenceState":
        """
        返回一个底背离确认的状态
        
        Args:
            confirm_time: 确认时间
            confirm_price: 确认时的价格
            confirm_diff: 确认时的 DIF 值
            
        Returns:
            新的 DivergenceState 对象
        """
        return DivergenceState(
            is_top_confirmed=False,
            is_bottom_confirmed=True,
            confirm_time=confirm_time,
            confirm_price=confirm_price,
            confirm_diff=confirm_diff,
        )
    
    def reset(self) -> "DivergenceState":
        """返回一个重置后的初始状态"""
        return DivergenceState()
    
    def __repr__(self) -> str:
        if self.is_top_confirmed:
            return f"DivergenceState(TopConfirmed at {self.confirm_price:.2f})"
        elif self.is_bottom_confirmed:
            return f"DivergenceState(BottomConfirmed at {self.confirm_price:.2f})"
        else:
            return "DivergenceState(None)"
