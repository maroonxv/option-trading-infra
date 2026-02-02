"""
TDValue 值对象 - TD 序列指标快照

存储某一时刻的 TD 序列状态，不可变对象。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TDValue:
    """
    TD 序列指标快照值对象
    
    Attributes:
        td_count: 当前 TD 计数 (正数为买入序列，负数为卖出序列)
        td_setup: 当前 Setup 阶段计数
        has_buy_8_9: 是否出现买入 8/9 信号 (低8/9)
        has_sell_8_9: 是否出现卖出 8/9 信号 (高8/9)
    """
    td_count: int
    td_setup: int
    has_buy_8_9: bool
    has_sell_8_9: bool
    
    @property
    def is_buy_setup_complete(self) -> bool:
        """判断买入 Setup 是否完成 (计数达到 9)"""
        return self.td_count >= 9
    
    @property
    def is_sell_setup_complete(self) -> bool:
        """判断卖出 Setup 是否完成 (计数达到 -9)"""
        return self.td_count <= -9
    
    @property
    def is_buy_signal_active(self) -> bool:
        """判断是否有活跃的买入信号"""
        return self.has_buy_8_9 or self.is_buy_setup_complete
    
    @property
    def is_sell_signal_active(self) -> bool:
        """判断是否有活跃的卖出信号"""
        return self.has_sell_8_9 or self.is_sell_setup_complete
    
    def __repr__(self) -> str:
        buy_flag = "B8/9" if self.has_buy_8_9 else ""
        sell_flag = "S8/9" if self.has_sell_8_9 else ""
        flags = " ".join(filter(None, [buy_flag, sell_flag]))
        return f"TDValue(count={self.td_count}, setup={self.td_setup}{', ' + flags if flags else ''})"
