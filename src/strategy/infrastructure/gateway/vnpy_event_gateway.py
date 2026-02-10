"""
VnpyEventGateway - 事件监听网关

封装 vnpy EventEngine 的事件订阅和回调注册能力。
"""
from typing import Callable, Dict, List, Any, Set
from .vnpy_gateway_adapter import VnpyGatewayAdapter


# 支持的事件类型常量
EVENT_ORDER = "eOrder."
EVENT_TRADE = "eTrade."
EVENT_POSITION = "ePosition."
EVENT_ACCOUNT = "eAccount."
EVENT_CONTRACT = "eContract."
EVENT_TICK = "eTick."
EVENT_QUOTE = "eQuote."
EVENT_LOG = "eLog"


class VnpyEventGateway(VnpyGatewayAdapter):
    """
    事件监听网关
    
    封装事件监听能力，包括：
    - 注册事件处理函数
    - 取消事件处理函数注册
    - 支持订单、成交、持仓、账户等事件
    """
    
    def __init__(self, strategy_context: Any):
        """
        初始化事件监听网关
        
        Args:
            strategy_context: VnPy 策略实例
        """
        super().__init__(strategy_context)
        
        # 记录已注册的事件处理函数，用于清理
        self._registered_handlers: Dict[str, Set[Callable]] = {}
    
    def register_event_handler(
        self, 
        event_type: str, 
        handler: Callable[[Any], None]
    ) -> bool:
        """
        注册事件处理函数
        
        Args:
            event_type: 事件类型 (如 EVENT_ORDER, EVENT_TRADE 等)
            handler: 事件处理函数，接收 Event 对象作为参数
            
        Returns:
            是否注册成功
        """
        event_engine = self._get_event_engine()
        if not event_engine:
            self._log(f"EventEngine 不可用，无法注册事件处理函数: {event_type}")
            return False
        
        try:
            event_engine.register(event_type, handler)
            
            # 记录已注册的处理函数
            if event_type not in self._registered_handlers:
                self._registered_handlers[event_type] = set()
            self._registered_handlers[event_type].add(handler)
            
            self._log(f"已注册事件处理函数: {event_type}")
            return True
            
        except Exception as e:
            self._log(f"注册事件处理函数失败: {event_type}, 错误: {e}")
            return False
    
    def unregister_event_handler(
        self, 
        event_type: str, 
        handler: Callable[[Any], None]
    ) -> bool:
        """
        取消事件处理函数注册
        
        Args:
            event_type: 事件类型
            handler: 要取消的事件处理函数
            
        Returns:
            是否取消成功
        """
        event_engine = self._get_event_engine()
        if not event_engine:
            self._log(f"EventEngine 不可用，无法取消事件处理函数: {event_type}")
            return False
        
        try:
            event_engine.unregister(event_type, handler)
            
            # 从记录中移除
            if event_type in self._registered_handlers:
                self._registered_handlers[event_type].discard(handler)
            
            self._log(f"已取消事件处理函数: {event_type}")
            return True
            
        except Exception as e:
            self._log(f"取消事件处理函数失败: {event_type}, 错误: {e}")
            return False
    
    def unregister_all_handlers(self) -> None:
        """
        取消所有已注册的事件处理函数
        
        用于策略停止时清理资源
        """
        event_engine = self._get_event_engine()
        if not event_engine:
            return
        
        for event_type, handlers in self._registered_handlers.items():
            for handler in list(handlers):
                try:
                    event_engine.unregister(event_type, handler)
                except Exception:
                    pass
        
        self._registered_handlers.clear()
        self._log("已取消所有事件处理函数")
    
    def get_registered_event_types(self) -> List[str]:
        """
        获取已注册处理函数的事件类型列表
        
        Returns:
            事件类型列表
        """
        return list(self._registered_handlers.keys())
    
    def _get_event_engine(self) -> Any:
        """获取 EventEngine 实例"""
        # 尝试从 main_engine 获取
        if self.main_engine:
            return getattr(self.main_engine, "event_engine", None)
        
        # 尝试从 strategy_engine 获取
        if hasattr(self.context, "strategy_engine"):
            strategy_engine = self.context.strategy_engine
            if hasattr(strategy_engine, "event_engine"):
                return strategy_engine.event_engine
            if hasattr(strategy_engine, "main_engine"):
                main_engine = strategy_engine.main_engine
                return getattr(main_engine, "event_engine", None)
        
        return None
    
    # 便捷方法：注册特定类型的事件处理函数
    
    def on_order(self, handler: Callable[[Any], None]) -> bool:
        """
        注册订单事件处理函数
        
        Args:
            handler: 处理函数，接收 OrderData 作为参数
        """
        return self.register_event_handler(EVENT_ORDER, handler)
    
    def on_trade(self, handler: Callable[[Any], None]) -> bool:
        """
        注册成交事件处理函数
        
        Args:
            handler: 处理函数，接收 TradeData 作为参数
        """
        return self.register_event_handler(EVENT_TRADE, handler)
    
    def on_position(self, handler: Callable[[Any], None]) -> bool:
        """
        注册持仓事件处理函数
        
        Args:
            handler: 处理函数，接收 PositionData 作为参数
        """
        return self.register_event_handler(EVENT_POSITION, handler)
    
    def on_account(self, handler: Callable[[Any], None]) -> bool:
        """
        注册账户事件处理函数
        
        Args:
            handler: 处理函数，接收 AccountData 作为参数
        """
        return self.register_event_handler(EVENT_ACCOUNT, handler)
    
    def on_tick(self, handler: Callable[[Any], None]) -> bool:
        """
        注册 Tick 事件处理函数
        
        Args:
            handler: 处理函数，接收 TickData 作为参数
        """
        return self.register_event_handler(EVENT_TICK, handler)
