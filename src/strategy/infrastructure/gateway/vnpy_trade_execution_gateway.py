from typing import List
from ...domain.demand_interface.trade_execution_interface import ITradeExecutionGateway
from ...domain.value_object.order_instruction import OrderInstruction, Direction, Offset
from .vnpy_gateway_adapter import VnpyGatewayAdapter

class VnpyTradeExecutionGateway(VnpyGatewayAdapter, ITradeExecutionGateway):
    """VnPy 交易执行网关实现"""
    
    def send_order(self, instruction: OrderInstruction) -> List[str]:
        """
        发送订单
        
        VnPy 策略模板提供了 buy/sell/short/cover 方法。
        """
        if hasattr(self.context, "paper_trading") and self.context.paper_trading:
            self._log(f"[PAPER] 模拟下单: {instruction}")
            return ["PAPER_ORDER"]

        vt_orderids = []
        
        # 提取参数
        vt_symbol = instruction.vt_symbol
        try:
            price = float(instruction.price)
        except Exception:
            price = instruction.price
        try:
            volume = int(instruction.volume)
        except Exception:
            volume = instruction.volume
        direction = instruction.direction
        offset = instruction.offset
        
        # 根据指令调用对应方法
        # 注意: self.context 是策略实例
        method_name = None
        if direction == Direction.LONG:
            if offset == Offset.OPEN:
                method_name = "buy"
            elif offset == Offset.CLOSE:
                method_name = "cover"
        elif direction == Direction.SHORT:
            if offset == Offset.OPEN:
                method_name = "short"
            elif offset == Offset.CLOSE:
                method_name = "sell"

        if not method_name:
            self._log(f"下单失败：无法映射指令到下单方法: {instruction}")
            return []

        if not hasattr(self.context, method_name):
            self._log(f"下单失败：策略缺少方法 {method_name}()，指令: {instruction}")
            return []

        try:
            vt_orderids = getattr(self.context, method_name)(vt_symbol, price, volume)
        except Exception as e:
            self._log(f"下单异常：{method_name}({vt_symbol}, {price}, {volume}) 失败，指令: {instruction}, 错误: {e}")
            return []
        
        # VnPy 的下单函数返回的是 list[vt_orderid] 或 str(vt_orderid)
        # 这里统一处理为 list
        if isinstance(vt_orderids, str):
            return [vt_orderids]
        vt_orderids = vt_orderids or []
        if not vt_orderids:
            self._log(f"下单返回空订单号：{method_name}() 未产生委托，指令: {instruction}")
        return vt_orderids

    def cancel_order(self, vt_orderid: str) -> None:
        if hasattr(self.context, "cancel_order"):
            self.context.cancel_order(vt_orderid)

    def cancel_all_orders(self) -> None:
        if hasattr(self.context, "cancel_all"):
            self.context.cancel_all()
