"""
VnpyOrderGateway - 订单查询网关

封装 vnpy MainEngine/OmsEngine 的订单和成交查询能力。
"""
from typing import List, Optional, Any
from .vnpy_gateway_adapter import VnpyGatewayAdapter


class VnpyOrderGateway(VnpyGatewayAdapter):
    """
    订单查询网关
    
    封装订单和成交的查询能力，包括：
    - 单个订单查询
    - 所有订单查询
    - 活动订单查询
    - 单个成交查询
    - 所有成交查询
    """
    
    def get_order(self, vt_orderid: str) -> Optional[Any]:
        """
        获取指定订单
        
        Args:
            vt_orderid: 订单唯一标识 (格式: {gateway_name}.{orderid})
            
        Returns:
            OrderData 对象，如果不存在则返回 None
        """
        if not self.main_engine:
            self._log(f"MainEngine 不可用，无法查询订单: {vt_orderid}")
            return None
        
        try:
            return self.main_engine.get_order(vt_orderid)
        except Exception as e:
            self._log(f"查询订单失败: {vt_orderid}, 错误: {e}")
            return None
    
    def get_all_orders(self) -> List[Any]:
        """
        获取所有订单
        
        Returns:
            当前交易日所有订单的列表
        """
        if not self.main_engine:
            self._log("MainEngine 不可用，无法查询所有订单")
            return []
        
        try:
            return self.main_engine.get_all_orders()
        except Exception as e:
            self._log(f"查询所有订单失败: {e}")
            return []
    
    def get_all_active_orders(self) -> List[Any]:
        """
        获取所有活动订单
        
        活动订单指状态为 SUBMITTING、NOTTRADED 或 PARTTRADED 的订单。
        
        Returns:
            所有活动订单的列表
        """
        if not self.main_engine:
            self._log("MainEngine 不可用，无法查询活动订单")
            return []
        
        try:
            return self.main_engine.get_all_active_orders()
        except Exception as e:
            self._log(f"查询活动订单失败: {e}")
            return []
    
    def get_trade(self, vt_tradeid: str) -> Optional[Any]:
        """
        获取指定成交
        
        Args:
            vt_tradeid: 成交唯一标识 (格式: {gateway_name}.{tradeid})
            
        Returns:
            TradeData 对象，如果不存在则返回 None
        """
        if not self.main_engine:
            self._log(f"MainEngine 不可用，无法查询成交: {vt_tradeid}")
            return None
        
        try:
            return self.main_engine.get_trade(vt_tradeid)
        except Exception as e:
            self._log(f"查询成交失败: {vt_tradeid}, 错误: {e}")
            return None
    
    def get_all_trades(self) -> List[Any]:
        """
        获取所有成交
        
        Returns:
            当前交易日所有成交记录的列表
        """
        if not self.main_engine:
            self._log("MainEngine 不可用，无法查询所有成交")
            return []
        
        try:
            return self.main_engine.get_all_trades()
        except Exception as e:
            self._log(f"查询所有成交失败: {e}")
            return []
    
    def get_orders_by_symbol(self, vt_symbol: str) -> List[Any]:
        """
        获取指定合约的所有订单
        
        Args:
            vt_symbol: 合约代码
            
        Returns:
            该合约的所有订单列表
        """
        all_orders = self.get_all_orders()
        return [order for order in all_orders if order.vt_symbol == vt_symbol]
    
    def get_active_orders_by_symbol(self, vt_symbol: str) -> List[Any]:
        """
        获取指定合约的活动订单
        
        Args:
            vt_symbol: 合约代码
            
        Returns:
            该合约的活动订单列表
        """
        active_orders = self.get_all_active_orders()
        return [order for order in active_orders if order.vt_symbol == vt_symbol]
    
    def get_trades_by_symbol(self, vt_symbol: str) -> List[Any]:
        """
        获取指定合约的所有成交
        
        Args:
            vt_symbol: 合约代码
            
        Returns:
            该合约的所有成交列表
        """
        all_trades = self.get_all_trades()
        return [trade for trade in all_trades if trade.vt_symbol == vt_symbol]
    
    def get_trades_by_orderid(self, vt_orderid: str) -> List[Any]:
        """
        获取指定订单的所有成交
        
        Args:
            vt_orderid: 订单唯一标识
            
        Returns:
            该订单的所有成交列表
        """
        all_trades = self.get_all_trades()
        return [trade for trade in all_trades if trade.vt_orderid == vt_orderid]
