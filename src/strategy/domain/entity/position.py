"""
Position 实体 - 策略持仓

追踪策略视角的持仓生命周期，关联开仓信号类型。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Position:
    """
    持仓实体
    
    职责:
    1. 策略视角持仓: 追踪策略发起的持仓，而不仅仅是账户层面的持仓
    2. 信号关联: 记录该持仓是基于哪个信号开仓的，用于后续平仓逻辑判断
    3. 生命周期: 追踪持仓的创建、成交、平仓状态
    
    Attributes:
        vt_symbol: 期权合约代码 (VnPy 格式)
        underlying_vt_symbol: 标的期货合约代码
        signal: 开仓信号类型
        volume: 当前持仓数量 (实际成交量)
        target_volume: 目标持仓数量 (委托量)
        direction: 持仓方向 ("long" 或 "short")
        open_price: 开仓均价
        create_time: 持仓创建时间
        open_time: 实际开仓时间 (首次成交时间)
        close_time: 平仓时间
        is_closed: 是否已平仓
        is_manually_closed: 是否被手动平仓
    """
    vt_symbol: str
    underlying_vt_symbol: str
    signal: str
    volume: int = 0
    target_volume: int = 0
    direction: str = "short"  # 卖权策略通常是 short
    open_price: float = 0.0
    create_time: datetime = field(default_factory=datetime.now)
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    is_closed: bool = False
    is_manually_closed: bool = False
    
    def add_fill(self, filled_volume: int, fill_price: float, fill_time: datetime) -> None:
        """
        记录成交
        
        Args:
            filled_volume: 成交数量
            fill_price: 成交价格
            fill_time: 成交时间
        """
        if self.volume == 0:
            # 首次成交
            self.open_price = fill_price
            self.open_time = fill_time
        else:
            # 后续成交，计算均价
            total_value = self.open_price * self.volume + fill_price * filled_volume
            self.volume += filled_volume
            self.open_price = total_value / self.volume if self.volume > 0 else 0.0
            return
        
        self.volume += filled_volume
    
    def reduce_volume(self, closed_volume: int, close_time_: Optional[datetime] = None) -> None:
        """
        减少持仓数量 (平仓)
        
        Args:
            closed_volume: 平仓数量
            close_time_: 平仓时间
        """
        self.volume = max(0, self.volume - closed_volume)
        
        if self.volume == 0:
            self.is_closed = True
            self.close_time = close_time_ or datetime.now()
    
    def mark_as_manually_closed(self, closed_volume: int) -> None:
        """
        标记为手动平仓
        
        Args:
            closed_volume: 手动平仓数量
        """
        self.is_manually_closed = True
        self.reduce_volume(closed_volume)
    
    @property
    def is_fully_filled(self) -> bool:
        """判断是否完全成交"""
        return self.volume >= self.target_volume
    
    @property
    def pending_volume(self) -> int:
        """获取未成交数量"""
        return max(0, self.target_volume - self.volume)
    
    @property
    def is_active(self) -> bool:
        """判断持仓是否活跃 (有持仓且未平仓)"""
        return self.volume > 0 and not self.is_closed
    
    @property
    def holding_time(self) -> Optional[float]:
        """获取持仓时长 (秒)"""
        if self.open_time is None:
            return None
        
        end_time = self.close_time or datetime.now()
        return (end_time - self.open_time).total_seconds()
    
    def is_for_open_signal(self, *signal_types: str) -> bool:
        """
        判断持仓是否由指定的开仓信号触发
        
        Args:
            signal_types: 一个或多个信号类型字符串
            
        Returns:
            如果持仓的信号类型在给定的信号类型中则返回 True
        """
        return self.signal in signal_types
    
    def __repr__(self) -> str:
        status = "Closed" if self.is_closed else f"Active({self.volume})"
        manual = " [Manual]" if self.is_manually_closed else ""
        return (
            f"Position({self.vt_symbol}, {self.signal}, "
            f"{self.direction}, {status}{manual})"
        )
