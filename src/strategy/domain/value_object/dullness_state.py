"""
DullnessState 值对象 - MACD 钝化状态

记录 MACD 顶/底钝化的激活状态和相关参数，不可变对象。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class DullnessState:
    """
    MACD 钝化状态值对象
    
    钝化定义: MACD 柱状图持续缩小但未形成有效背离的状态
    
    Attributes:
        is_top_active: 顶钝化是否激活
        is_bottom_active: 底钝化是否激活
        start_time: 钝化开始时间
        start_price: 钝化开始时的价格
        start_diff: 钝化开始时的 DIF 值
        is_top_invalidated: 顶钝化是否已失效
        is_bottom_invalidated: 底钝化是否已失效
    """
    is_top_active: bool = False
    is_bottom_active: bool = False
    start_time: Optional[datetime] = None
    start_price: float = 0.0
    start_diff: float = 0.0
    is_top_invalidated: bool = False
    is_bottom_invalidated: bool = False
    
    @property
    def is_active(self) -> bool:
        """判断是否有任何钝化处于激活状态"""
        return self.is_top_active or self.is_bottom_active
    
    @property
    def is_invalidated(self) -> bool:
        """判断是否有任何钝化已失效"""
        return self.is_top_invalidated or self.is_bottom_invalidated
    
    def with_top_active(
        self,
        start_time: datetime,
        start_price: float,
        start_diff: float
    ) -> "DullnessState":
        """
        返回一个新的激活顶钝化的状态
        
        Args:
            start_time: 钝化开始时间
            start_price: 钝化开始时的价格
            start_diff: 钝化开始时的 DIF 值
            
        Returns:
            新的 DullnessState 对象
        """
        return DullnessState(
            is_top_active=True,
            is_bottom_active=False,
            start_time=start_time,
            start_price=start_price,
            start_diff=start_diff,
            is_top_invalidated=False,
            is_bottom_invalidated=False,
        )
    
    def with_bottom_active(
        self,
        start_time: datetime,
        start_price: float,
        start_diff: float
    ) -> "DullnessState":
        """
        返回一个新的激活底钝化的状态
        
        Args:
            start_time: 钝化开始时间
            start_price: 钝化开始时的价格
            start_diff: 钝化开始时的 DIF 值
            
        Returns:
            新的 DullnessState 对象
        """
        return DullnessState(
            is_top_active=False,
            is_bottom_active=True,
            start_time=start_time,
            start_price=start_price,
            start_diff=start_diff,
            is_top_invalidated=False,
            is_bottom_invalidated=False,
        )
    
    def with_top_invalidated(self) -> "DullnessState":
        """返回一个顶钝化失效的状态"""
        return DullnessState(
            is_top_active=False,
            is_bottom_active=self.is_bottom_active,
            start_time=self.start_time,
            start_price=self.start_price,
            start_diff=self.start_diff,
            is_top_invalidated=True,
            is_bottom_invalidated=self.is_bottom_invalidated,
        )
    
    def with_bottom_invalidated(self) -> "DullnessState":
        """返回一个底钝化失效的状态"""
        return DullnessState(
            is_top_active=self.is_top_active,
            is_bottom_active=False,
            start_time=self.start_time,
            start_price=self.start_price,
            start_diff=self.start_diff,
            is_top_invalidated=self.is_top_invalidated,
            is_bottom_invalidated=True,
        )
    
    def reset(self) -> "DullnessState":
        """返回一个重置后的初始状态"""
        return DullnessState()
    
    def __repr__(self) -> str:
        states = []
        if self.is_top_active:
            states.append("TopActive")
        if self.is_bottom_active:
            states.append("BottomActive")
        if self.is_top_invalidated:
            states.append("TopInvalid")
        if self.is_bottom_invalidated:
            states.append("BottomInvalid")
        return f"DullnessState({', '.join(states) if states else 'Inactive'})"
