from abc import ABC, abstractmethod
from typing import List
from ..value_object.order_instruction import OrderInstruction

class ITradeExecutionGateway(ABC):
    """交易执行网关接口"""
    
    @abstractmethod
    def send_order(self, instruction: OrderInstruction) -> List[str]:
        """
        发送订单
        
        Returns:
            订单ID列表 (vt_orderid list)
        """
        pass

    @abstractmethod
    def cancel_order(self, vt_orderid: str) -> None:
        """撤销订单"""
        pass

    @abstractmethod
    def cancel_all_orders(self) -> None:
        """撤销所有订单"""
        pass
