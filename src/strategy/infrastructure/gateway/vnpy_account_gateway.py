"""
VnpyAccountGateway - 账户/持仓网关

封装 vnpy MainEngine/OmsEngine 的账户和持仓查询能力。
"""
from typing import List, Optional, Any
from ...domain.value_object.account_snapshot import AccountSnapshot
from ...domain.value_object.position_snapshot import PositionSnapshot, PositionDirection
from .vnpy_gateway_adapter import VnpyGatewayAdapter


class VnpyAccountGateway(VnpyGatewayAdapter):
    """
    账户/持仓网关
    
    封装账户资金和持仓的查询能力，包括：
    - 账户资金快照查询
    - 多账户支持
    - 持仓查询（包含完整字段）
    """
    
    def get_balance(self) -> float:
        """获取账户总资金 (balance)"""
        snapshot = self.get_account_snapshot()
        return snapshot.balance if snapshot else 0.0

    def get_account_snapshot(self) -> Optional[AccountSnapshot]:
        """
        获取账户资金快照
        
        支持从 strategy_context.main_engine 获取 (实盘)
        或从 context 自身尝试 (回测兼容)
        
        Returns:
            AccountSnapshot 对象，包含 balance、available、frozen 字段
        """
        try:
            accounts = None
            # 1. 尝试从 strategy_context 获取 main_engine
            main_engine = getattr(self.context, "main_engine", None)
            if main_engine and hasattr(main_engine, "get_all_accounts"):
                accounts = main_engine.get_all_accounts()
            # 2. 尝试从 adapter 缓存的 main_engine 获取
            elif self.main_engine and hasattr(self.main_engine, "get_all_accounts"):
                accounts = self.main_engine.get_all_accounts()

            if accounts:
                first = accounts[0]
                return AccountSnapshot(
                    balance=float(getattr(first, "balance", 0.0) or 0.0),
                    available=float(getattr(first, "available", 0.0) or 0.0),
                    frozen=float(getattr(first, "frozen", 0.0) or 0.0),
                    accountid=str(getattr(first, "accountid", "") or "")
                )
        except Exception as e:
            self._log(f"获取账户快照失败: {e}")
            
        return None
    
    def get_account(self, vt_accountid: str) -> Optional[AccountSnapshot]:
        """
        获取指定账户
        
        Args:
            vt_accountid: 账户唯一标识 (格式: {gateway_name}.{accountid})
            
        Returns:
            AccountSnapshot 对象，如果不存在则返回 None
        """
        if not self.main_engine:
            self._log(f"MainEngine 不可用，无法查询账户: {vt_accountid}")
            return None
        
        try:
            account = self.main_engine.get_account(vt_accountid)
            if account:
                return AccountSnapshot(
                    balance=float(getattr(account, "balance", 0.0) or 0.0),
                    available=float(getattr(account, "available", 0.0) or 0.0),
                    frozen=float(getattr(account, "frozen", 0.0) or 0.0),
                    accountid=str(getattr(account, "accountid", "") or "")
                )
        except Exception as e:
            self._log(f"查询账户失败: {vt_accountid}, 错误: {e}")
        
        return None
    
    def get_all_accounts(self) -> List[AccountSnapshot]:
        """
        获取所有账户
        
        Returns:
            所有账户的 AccountSnapshot 列表
        """
        if not self.main_engine:
            self._log("MainEngine 不可用，无法查询所有账户")
            return []
        
        try:
            accounts = self.main_engine.get_all_accounts()
            return [
                AccountSnapshot(
                    balance=float(getattr(acc, "balance", 0.0) or 0.0),
                    available=float(getattr(acc, "available", 0.0) or 0.0),
                    frozen=float(getattr(acc, "frozen", 0.0) or 0.0),
                    accountid=str(getattr(acc, "accountid", "") or "")
                )
                for acc in accounts
            ]
        except Exception as e:
            self._log(f"查询所有账户失败: {e}")
            return []

    def get_position(self, vt_symbol: str, direction: Any) -> Optional[PositionSnapshot]:
        """
        获取特定持仓
        
        Args:
            vt_symbol: 合约代码 (VnPy 格式，如 "rb2501.SHFE")
            direction: 持仓方向 (可以是 PositionDirection 或 vnpy Direction)
            
        Returns:
            PositionSnapshot 对象，包含完整的持仓信息
        """
        if not self.main_engine:
            self._log(f"MainEngine 不可用，无法查询持仓: {vt_symbol}")
            return None
        
        try:
            # 转换方向为 vnpy 格式
            direction_value = self._convert_direction(direction)
            if direction_value is None:
                self._log(f"无效的持仓方向: {direction}")
                return None
            
            # 获取 gateway_name
            gateway_name = self._get_gateway_name()
            if not gateway_name:
                self._log("无法获取 gateway_name")
                return None
            
            # 构造 vt_positionid: {gateway_name}.{vt_symbol}.{direction}
            vt_positionid = f"{gateway_name}.{vt_symbol}.{direction_value}"
            
            position = self.main_engine.get_position(vt_positionid)
            if position:
                return self._convert_to_snapshot(position)
        except Exception as e:
            self._log(f"查询持仓失败: {vt_symbol}, 错误: {e}")
        
        return None
    
    def get_all_positions(self) -> List[PositionSnapshot]:
        """
        获取所有持仓
        
        Returns:
            所有持仓的 PositionSnapshot 列表
        """
        if not self.main_engine:
            self._log("MainEngine 不可用，无法查询所有持仓")
            return []
        
        try:
            positions = self.main_engine.get_all_positions()
            return [self._convert_to_snapshot(pos) for pos in positions if pos]
        except Exception as e:
            self._log(f"查询所有持仓失败: {e}")
            return []
    
    def get_positions_by_symbol(self, vt_symbol: str) -> List[PositionSnapshot]:
        """
        获取指定合约的所有持仓（多空两个方向）
        
        Args:
            vt_symbol: 合约代码
            
        Returns:
            该合约的所有持仓列表
        """
        all_positions = self.get_all_positions()
        return [pos for pos in all_positions if pos.vt_symbol == vt_symbol]
    
    def _convert_direction(self, direction: Any) -> Optional[str]:
        """
        转换持仓方向为 vnpy 格式的字符串
        
        vnpy Direction 枚举值: LONG="多", SHORT="空"
        """
        if isinstance(direction, PositionDirection):
            if direction == PositionDirection.LONG:
                return "多"
            elif direction == PositionDirection.SHORT:
                return "空"
            else:
                return "净"
        
        # 尝试从 vnpy Direction 枚举获取
        if hasattr(direction, "value"):
            return direction.value
        
        # 字符串处理
        if isinstance(direction, str):
            direction_lower = direction.lower()
            if direction_lower in ("long", "多"):
                return "多"
            elif direction_lower in ("short", "空"):
                return "空"
            elif direction_lower in ("net", "净"):
                return "净"
        
        return None
    
    def _get_gateway_name(self) -> Optional[str]:
        """获取当前使用的 gateway 名称"""
        # 尝试从 main_engine 获取
        if self.main_engine:
            gateway_names = self.main_engine.get_all_gateway_names()
            if gateway_names:
                return gateway_names[0]
        
        # 尝试从 context 获取
        if hasattr(self.context, "gateway_name"):
            return self.context.gateway_name
        
        return None
    
    def _convert_to_snapshot(self, position: Any) -> PositionSnapshot:
        """
        将 vnpy PositionData 转换为 PositionSnapshot
        """
        # 转换方向
        direction_value = getattr(position, "direction", None)
        if direction_value:
            direction_str = getattr(direction_value, "value", str(direction_value))
            if direction_str in ("多", "LONG", "long"):
                direction = PositionDirection.LONG
            elif direction_str in ("空", "SHORT", "short"):
                direction = PositionDirection.SHORT
            else:
                direction = PositionDirection.NET
        else:
            direction = PositionDirection.NET
        
        return PositionSnapshot(
            vt_symbol=getattr(position, "vt_symbol", ""),
            direction=direction,
            volume=float(getattr(position, "volume", 0.0) or 0.0),
            frozen=float(getattr(position, "frozen", 0.0) or 0.0),
            price=float(getattr(position, "price", 0.0) or 0.0),
            pnl=float(getattr(position, "pnl", 0.0) or 0.0),
            yd_volume=float(getattr(position, "yd_volume", 0.0) or 0.0)
        )
