"""
信号生成服务接口 (ISignalService)

职责: 根据标的状态判断开平仓信号

设计原则:
- 完全字符串化，废弃 SignalType 枚举
- 用户可使用任意字符串定义信号
- 建议命名规范: ACTION_REASON_DETAIL（如 sell_call_divergence_td9）
- 框架层仅透传，不解析信号内容
"""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.strategy.domain.entity.target_instrument import TargetInstrument
    from src.strategy.domain.entity.position import Position


class ISignalService(ABC):
    """
    信号生成服务接口
    
    实现此接口的类负责根据标的的技术指标和市场状态生成开平仓信号。
    """

    @abstractmethod
    def check_open_signal(self, instrument: "TargetInstrument") -> Optional[str]:
        """
        检查开仓信号
        
        此方法在每根新 K 线到达时被调用，用于判断是否应该开仓。
        
        参数:
            instrument (TargetInstrument): 标的实体，包含最新的指标数据
        
        返回:
            str: 触发开仓时返回信号字符串（如 "long_macd_golden_cross"）
            None: 无开仓信号时返回 None
        
        实现指导:
            1. 从 instrument.indicators 读取指标数据
            2. 根据策略逻辑判断是否触发开仓
            3. 返回信号字符串或 None
        
        示例:
            >>> def check_open_signal(self, instrument):
            ...     if 'macd' not in instrument.indicators:
            ...         return None
            ...     
            ...     macd_data = instrument.indicators['macd']
            ...     if macd_data['dif'] > macd_data['dea']:
            ...         return "long_macd_golden_cross"
            ...     
            ...     return None
        
        信号命名建议:
            - 使用小写字母和下划线
            - 格式: ACTION_REASON_DETAIL
            - 示例: "buy_call_divergence", "sell_put_td9", "long_ema_crossover"
        
        异常处理:
            - 如果指标数据不完整，应返回 None 而不是抛出异常
            - 如果计算过程出错，应返回 None 并记录错误
        """
        pass

    @abstractmethod
    def check_close_signal(
        self,
        instrument: "TargetInstrument",
        position: "Position"
    ) -> Optional[str]:
        """
        检查平仓信号
        
        此方法在每根新 K 线到达时被调用，用于判断是否应该平仓现有持仓。
        
        参数:
            instrument (TargetInstrument): 标的实体，包含最新的指标数据
            position (Position): 当前持仓，包含方向、手数等信息
        
        返回:
            str: 触发平仓时返回信号字符串（如 "close_long_stop_loss"）
            None: 无平仓信号时返回 None
        
        实现指导:
            1. 从 instrument.indicators 读取指标数据
            2. 根据持仓方向和策略逻辑判断是否触发平仓
            3. 返回信号字符串或 None
        
        示例:
            >>> def check_close_signal(self, instrument, position):
            ...     if 'macd' not in instrument.indicators:
            ...         return None
            ...     
            ...     macd_data = instrument.indicators['macd']
            ...     
            ...     # 多头持仓，检查死叉平仓
            ...     if position.direction == Direction.LONG:
            ...         if macd_data['dif'] < macd_data['dea']:
            ...             return "close_long_macd_death_cross"
            ...     
            ...     # 空头持仓，检查死叉平仓
            ...     elif position.direction == Direction.SHORT:
            ...         if macd_data['dif'] > macd_data['dea']:
            ...             return "close_short_macd_death_cross"
            ...     
            ...     return None
        
        异常处理:
            - 如果指标数据不完整，应返回 None 而不是抛出异常
            - 如果计算过程出错，应返回 None 并记录错误
        """
        pass
