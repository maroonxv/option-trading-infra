"""
仓位计算与风控服务接口 (IPositionSizingService)

职责: 计算实际开平仓手数，执行风控检查

设计原则:
- 负责所有风控逻辑和仓位计算
- 返回实际可执行的手数（可能小于请求手数）
- 支持任意风控规则的自定义实现
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.strategy.domain.entity.target_instrument import TargetInstrument
    from src.strategy.domain.entity.position import Position


class IPositionSizingService(ABC):
    """
    仓位计算与风控服务接口
    
    实现此接口的类负责计算实际开平仓手数，并执行风控检查。
    """

    @abstractmethod
    def calculate_open_volume(
        self,
        desired_volume: int,
        instrument: "TargetInstrument",
        account: dict
    ) -> int:
        """
        计算实际开仓手数
        
        此方法在生成开仓信号后被调用，用于确定实际可开仓的手数。
        
        参数:
            desired_volume (int): 期望开仓手数
            instrument (TargetInstrument): 标的实体，包含合约信息和最新价格
            account (dict): 账户信息，包含可用资金、持仓等数据
        
        返回:
            int: 实际可开仓手数
                - 返回值 > 0: 允许开仓，返回实际手数
                - 返回值 == 0: 拒绝开仓（风控限制）
        
        实现指导:
            内部应包含以下风控检查:
            1. 检查品种最大持仓限制
            2. 检查是否已有同方向持仓（防止重复开仓）
            3. 检查账户可用资金是否充足
            4. 检查单笔开仓限制
        
        示例:
            >>> def calculate_open_volume(self, desired_volume, instrument, account):
            ...     # 检查最大持仓限制
            ...     max_volume = self.max_position_per_product
            ...     if desired_volume > max_volume:
            ...         return max_volume
            ...     
            ...     # 检查账户资金
            ...     required_margin = desired_volume * instrument.latest_close * 0.1
            ...     if account['available'] < required_margin:
            ...         return 0
            ...     
            ...     # 检查是否已有持仓
            ...     existing_position = self._get_existing_position(instrument.vt_symbol)
            ...     if existing_position and existing_position.volume > 0:
            ...         return 0  # 已有持仓，拒绝重复开仓
            ...     
            ...     return desired_volume
        
        异常处理:
            - 如果账户信息不完整，应返回 0 而不是抛出异常
            - 如果计算过程出错，应返回 0 并记录错误
        """
        pass

    @abstractmethod
    def calculate_exit_volume(
        self,
        desired_volume: int,
        current_position: "Position"
    ) -> int:
        """
        计算实际平仓手数
        
        此方法在生成平仓信号后被调用，用于确定实际可平仓的手数。
        
        参数:
            desired_volume (int): 期望平仓手数
            current_position (Position): 当前持仓，包含方向、手数等信息
        
        返回:
            int: 实际可平仓手数
                - 返回值 > 0: 允许平仓，返回实际手数
                - 返回值 == 0: 拒绝平仓
        
        实现指导:
            1. 检查平仓手数是否超出当前持仓数
            2. 返回实际可平仓的手数
        
        示例:
            >>> def calculate_exit_volume(self, desired_volume, current_position):
            ...     # 不能平仓超过当前持仓数
            ...     if desired_volume > current_position.volume:
            ...         return current_position.volume
            ...     
            ...     return desired_volume
        
        异常处理:
            - 如果持仓信息不完整，应返回 0 而不是抛出异常
            - 如果计算过程出错，应返回 0 并记录错误
        """
        pass
