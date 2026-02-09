"""
示例 IPositionSizingService 实现 - 仓位计算与风控服务

本示例展示如何实现 IPositionSizingService 接口，提供仓位计算和风控检查功能。

实现策略:
1. 固定手数模式: 每次开仓固定手数
2. 比例仓位模式: 根据账户资金按比例计算手数
3. 风控检查: 最大持仓限制、资金充足性检查、重复开仓检查

Requirements: 9.3, 9.5
"""

from typing import TYPE_CHECKING, Optional, Dict
from src.strategy.domain.interface import IPositionSizingService

if TYPE_CHECKING:
    from src.strategy.domain.entity.target_instrument import TargetInstrument
    from src.strategy.domain.entity.position import Position


class DemoPositionSizingService(IPositionSizingService):
    """
    示例仓位计算服务
    
    提供两种仓位计算模式:
    1. 固定手数模式 (fixed_volume_mode=True)
    2. 比例仓位模式 (fixed_volume_mode=False)
    
    风控规则:
    - 单品种最大持仓限制
    - 账户资金充足性检查
    - 防止重复开仓
    - 平仓手数不超过当前持仓
    
    参数:
        fixed_volume_mode (bool): 是否使用固定手数模式，默认 True
        fixed_volume (int): 固定手数模式下的开仓手数，默认 1
        position_ratio (float): 比例仓位模式下的仓位比例 (0-1)，默认 0.1 (10%)
        max_position_per_product (int): 单品种最大持仓限制，默认 5
        margin_ratio (float): 保证金比例，默认 0.15 (15%)
        position_tracker (Dict): 持仓追踪器，用于检查重复开仓
    """
    
    def __init__(
        self,
        fixed_volume_mode: bool = True,
        fixed_volume: int = 1,
        position_ratio: float = 0.1,
        max_position_per_product: int = 5,
        margin_ratio: float = 0.15,
        position_tracker: Optional[Dict[str, "Position"]] = None
    ):
        """
        初始化仓位计算服务
        
        Args:
            fixed_volume_mode: 是否使用固定手数模式
            fixed_volume: 固定手数模式下的开仓手数
            position_ratio: 比例仓位模式下的仓位比例 (0-1)
            max_position_per_product: 单品种最大持仓限制
            margin_ratio: 保证金比例
            position_tracker: 持仓追踪器，用于检查重复开仓
        """
        self.fixed_volume_mode = fixed_volume_mode
        self.fixed_volume = fixed_volume
        self.position_ratio = position_ratio
        self.max_position_per_product = max_position_per_product
        self.margin_ratio = margin_ratio
        self.position_tracker = position_tracker or {}
    
    def calculate_open_volume(
        self,
        desired_volume: int,
        instrument: "TargetInstrument",
        account: dict
    ) -> int:
        """
        计算实际开仓手数
        
        执行以下风控检查:
        1. 检查账户信息完整性
        2. 检查是否已有同标的持仓（防止重复开仓）
        3. 根据模式计算目标手数
        4. 检查单品种最大持仓限制
        5. 检查账户资金充足性
        
        Args:
            desired_volume: 期望开仓手数（通常为 1，由信号服务提供）
            instrument: 标的实体，包含合约信息和最新价格
            account: 账户信息，包含 'available' (可用资金) 等字段
        
        Returns:
            实际可开仓手数，0 表示拒绝开仓
        """
        # 风控检查 1: 验证账户信息完整性
        if not account or 'available' not in account:
            print(f"[风控拒绝] 账户信息不完整: {account}")
            return 0
        
        available_funds = account['available']
        
        # 风控检查 2: 检查是否已有同标的持仓（防止重复开仓）
        if self._has_existing_position(instrument.vt_symbol):
            print(f"[风控拒绝] 标的 {instrument.vt_symbol} 已有持仓，拒绝重复开仓")
            return 0
        
        # 根据模式计算目标手数
        if self.fixed_volume_mode:
            # 固定手数模式
            target_volume = self.fixed_volume
            print(f"[仓位计算] 固定手数模式: {target_volume} 手")
        else:
            # 比例仓位模式: 根据账户资金和仓位比例计算
            target_volume = self._calculate_volume_by_ratio(
                available_funds,
                instrument.latest_close,
                self.position_ratio
            )
            print(f"[仓位计算] 比例仓位模式: 可用资金={available_funds:.2f}, "
                  f"比例={self.position_ratio:.2%}, 计算手数={target_volume}")
        
        # 风控检查 3: 检查单品种最大持仓限制
        if target_volume > self.max_position_per_product:
            print(f"[风控限制] 目标手数 {target_volume} 超过单品种最大持仓 "
                  f"{self.max_position_per_product}，调整为最大值")
            target_volume = self.max_position_per_product
        
        # 风控检查 4: 检查账户资金充足性
        required_margin = self._calculate_required_margin(
            target_volume,
            instrument.latest_close
        )
        
        if required_margin > available_funds:
            print(f"[风控拒绝] 资金不足: 需要保证金={required_margin:.2f}, "
                  f"可用资金={available_funds:.2f}")
            return 0
        
        print(f"[风控通过] 标的={instrument.vt_symbol}, 开仓手数={target_volume}, "
              f"需要保证金={required_margin:.2f}, 可用资金={available_funds:.2f}")
        
        return target_volume
    
    def calculate_exit_volume(
        self,
        desired_volume: int,
        current_position: "Position"
    ) -> int:
        """
        计算实际平仓手数
        
        执行以下检查:
        1. 检查持仓信息完整性
        2. 确保平仓手数不超过当前持仓数
        
        Args:
            desired_volume: 期望平仓手数
            current_position: 当前持仓，包含方向、手数等信息
        
        Returns:
            实际可平仓手数，0 表示拒绝平仓
        """
        # 检查持仓信息完整性
        if not current_position or current_position.volume <= 0:
            print(f"[平仓拒绝] 持仓信息无效: {current_position}")
            return 0
        
        # 确保平仓手数不超过当前持仓数
        actual_volume = min(desired_volume, current_position.volume)
        
        if actual_volume < desired_volume:
            print(f"[平仓调整] 期望平仓 {desired_volume} 手，但当前持仓仅 "
                  f"{current_position.volume} 手，调整为 {actual_volume} 手")
        else:
            print(f"[平仓通过] 标的={current_position.vt_symbol}, "
                  f"平仓手数={actual_volume}/{current_position.volume}")
        
        return actual_volume
    
    # ==================== 私有辅助方法 ====================
    
    def _has_existing_position(self, vt_symbol: str) -> bool:
        """
        检查是否已有同标的持仓
        
        Args:
            vt_symbol: 合约代码
        
        Returns:
            True 表示已有持仓，False 表示无持仓
        """
        # 从持仓追踪器中查找活跃持仓
        for position in self.position_tracker.values():
            if position.vt_symbol == vt_symbol and position.is_active:
                return True
        return False
    
    def _calculate_volume_by_ratio(
        self,
        available_funds: float,
        price: float,
        ratio: float
    ) -> int:
        """
        根据资金比例计算手数
        
        计算公式:
        手数 = (可用资金 × 仓位比例) / (价格 × 保证金比例)
        
        Args:
            available_funds: 可用资金
            price: 合约价格
            ratio: 仓位比例 (0-1)
        
        Returns:
            计算得到的手数（向下取整）
        """
        if price <= 0:
            return 0
        
        # 计算可用于开仓的资金
        position_funds = available_funds * ratio
        
        # 计算单手所需保证金
        margin_per_lot = price * self.margin_ratio
        
        # 计算手数（向下取整）
        volume = int(position_funds / margin_per_lot)
        
        return max(0, volume)
    
    def _calculate_required_margin(
        self,
        volume: int,
        price: float
    ) -> float:
        """
        计算所需保证金
        
        计算公式:
        保证金 = 手数 × 价格 × 保证金比例
        
        Args:
            volume: 手数
            price: 合约价格
        
        Returns:
            所需保证金金额
        """
        return volume * price * self.margin_ratio


# ==================== 使用示例 ====================

def example_usage():
    """
    示例: 如何使用 DemoPositionSizingService
    
    此示例展示了固定手数模式和比例仓位模式的使用方法。
    """
    from src.strategy.domain.entity.target_instrument import TargetInstrument
    from src.strategy.domain.entity.position import Position
    import pandas as pd
    
    # 创建模拟标的
    instrument = TargetInstrument(vt_symbol="rb2501.SHFE")
    instrument.bars = pd.DataFrame({
        "datetime": [pd.Timestamp.now()],
        "open": [3500.0],
        "high": [3520.0],
        "low": [3480.0],
        "close": [3510.0],
        "volume": [10000]
    })
    
    # 模拟账户信息
    account = {
        "available": 100000.0,  # 可用资金 10 万
        "balance": 150000.0,    # 账户余额 15 万
    }
    
    print("=" * 60)
    print("示例 1: 固定手数模式")
    print("=" * 60)
    
    # 创建固定手数模式的服务
    service_fixed = DemoPositionSizingService(
        fixed_volume_mode=True,
        fixed_volume=2,
        max_position_per_product=5
    )
    
    # 计算开仓手数
    open_volume = service_fixed.calculate_open_volume(
        desired_volume=1,
        instrument=instrument,
        account=account
    )
    print(f"结果: 实际开仓手数 = {open_volume}\n")
    
    print("=" * 60)
    print("示例 2: 比例仓位模式")
    print("=" * 60)
    
    # 创建比例仓位模式的服务
    service_ratio = DemoPositionSizingService(
        fixed_volume_mode=False,
        position_ratio=0.2,  # 使用 20% 的资金
        max_position_per_product=5,
        margin_ratio=0.15
    )
    
    # 计算开仓手数
    open_volume = service_ratio.calculate_open_volume(
        desired_volume=1,
        instrument=instrument,
        account=account
    )
    print(f"结果: 实际开仓手数 = {open_volume}\n")
    
    print("=" * 60)
    print("示例 3: 平仓手数计算")
    print("=" * 60)
    
    # 创建模拟持仓
    position = Position(
        vt_symbol="rb2501C3600.SHFE",
        underlying_vt_symbol="rb2501.SHFE",
        signal="sell_call_macd_divergence",
        volume=3,
        target_volume=3,
        direction="short"
    )
    
    # 计算平仓手数
    exit_volume = service_fixed.calculate_exit_volume(
        desired_volume=5,  # 期望平仓 5 手
        current_position=position
    )
    print(f"结果: 实际平仓手数 = {exit_volume}\n")


if __name__ == "__main__":
    # 运行示例
    example_usage()
