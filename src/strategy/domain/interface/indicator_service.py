"""
指标计算服务接口 (IIndicatorService)

职责: 计算技术指标并更新 TargetInstrument 的 indicators 字典

设计原则:
- 作为计算主导者，负责所有指标计算
- 直接操作 instrument.indicators 字典
- 支持任意自定义指标，无需修改框架
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.strategy.domain.entity.target_instrument import TargetInstrument


class IIndicatorService(ABC):
    """
    指标计算服务接口
    
    实现此接口的类负责计算技术指标并将结果存储到 TargetInstrument 的 indicators 字典中。
    """

    @abstractmethod
    def calculate_bar(self, instrument: "TargetInstrument", bar: dict) -> None:
        """
        K 线更新时的指标计算逻辑
        
        此方法在每根新 K 线到达时被调用，实现应计算所需的技术指标并更新 instrument.indicators。
        
        参数:
            instrument (TargetInstrument): 标的实体，包含历史 K 线数据和指标容器
            bar (dict): 新 K 线数据，包含 datetime, open, high, low, close, volume 等字段
        
        实现指导:
            1. 从 instrument.bars 读取历史数据（如需要）
            2. 计算所需指标（MACD, EMA, TD 等）
            3. 将结果写入 instrument.indicators 字典
        
        示例:
            >>> def calculate_bar(self, instrument, bar):
            ...     # 计算 MACD 指标
            ...     dif, dea, macd_bar = self._calculate_macd(instrument.bars)
            ...     instrument.indicators['macd'] = {
            ...         'dif': dif,
            ...         'dea': dea,
            ...         'macd_bar': macd_bar
            ...     }
            ...     
            ...     # 计算 EMA 指标
            ...     fast_ema = self._calculate_ema(instrument.bars, 12)
            ...     slow_ema = self._calculate_ema(instrument.bars, 26)
            ...     instrument.indicators['ema'] = {
            ...         'fast': fast_ema,
            ...         'slow': slow_ema
            ...     }
        
        异常处理:
            - 如果数据不足以计算指标，应记录警告但不抛出异常
            - 如果计算过程出错，应记录错误但不中断策略执行
        """
        pass
