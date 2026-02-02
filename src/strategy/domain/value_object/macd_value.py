"""
MACDValue 值对象 - MACD 指标快照

存储某一时刻的 MACD 指标值，不可变对象。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MACDValue:
    """
    MACD 指标快照值对象
    
    Attributes:
        dif: 快线 (DIF = EMA12 - EMA26)
        dea: 慢线 (DEA = EMA9(DIF))
        macd_bar: MACD 柱状图 (MACD = 2 * (DIF - DEA))
    """
    dif: float
    dea: float
    macd_bar: float
    
    @property
    def is_golden_cross(self) -> bool:
        """判断是否处于金叉状态 (DIF > DEA)"""
        return self.dif > self.dea
    
    @property
    def is_death_cross(self) -> bool:
        """判断是否处于死叉状态 (DIF < DEA)"""
        return self.dif < self.dea
    
    @property
    def is_above_zero(self) -> bool:
        """判断 DIF 是否在零轴上方"""
        return self.dif > 0
    
    @property
    def is_below_zero(self) -> bool:
        """判断 DIF 是否在零轴下方"""
        return self.dif < 0
    
    def __repr__(self) -> str:
        return f"MACDValue(dif={self.dif:.4f}, dea={self.dea:.4f}, macd={self.macd_bar:.4f})"
