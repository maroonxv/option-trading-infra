from typing import List, Optional, Any
from ...domain.demand_interface.account_interface import IAccountGateway
from .vnpy_gateway_adapter import VnpyGatewayAdapter

class VnpyAccountGateway(VnpyGatewayAdapter, IAccountGateway):
    """VnPy 账户资金/持仓网关实现"""
    
    def get_balance(self) -> float:
        """
        获取账户可用资金
        注意: VnPy 策略层通常很难直接获取"账户总资金"，
        通常只能获取通过 strategy_engine 传递的 account 信息，
        或者在回测中获取 capital。
        """
        # 尝试从 main_engine 获取所有账户并求和 (仅实盘有效)
        if self.main_engine:
            accounts = self.main_engine.get_all_accounts()
            total_balance = sum([ac.balance for ac in accounts])
            if total_balance > 0:
                return total_balance
        
        # 回测模式下，context 可能有 capital 属性 (视具体引擎实现而定)
        # 这里返回一个默认值或抛出警告
        return 0.0

    def get_position(self, vt_symbol: str, direction: Any) -> Optional[Any]:
        """
        获取特定持仓
        注意: VnPy 的 get_position 通常需要 vt_positionid (vt_symbol.Direction)
        """
        if self.main_engine:
            # 构造 vt_positionid
            # VnPy Direction: LONG="多", SHORT="空"
            # 需要根据具体 Direction 枚举转换
            pass
        return None

    def get_all_positions(self) -> List[Any]:
        if self.main_engine:
            return self.main_engine.get_all_positions()
        return []
