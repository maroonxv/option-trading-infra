from typing import Any
from ..logging.logging_utils import setup_strategy_logger

class VnpyGatewayAdapter:
    """VnPy 网关适配器基类"""
    
    def __init__(self, strategy_context: Any):
        """
        Args:
            strategy_context: VnPy 策略实例 (CtaTemplate 或 StrategyTemplate)
        """
        self.context = strategy_context
        
        # 尝试提取 main_engine (部分高级功能需要)
        self.main_engine = None
        if hasattr(strategy_context, "strategy_engine"):
            if hasattr(strategy_context.strategy_engine, "main_engine"):
                self.main_engine = strategy_context.strategy_engine.main_engine
        
        # 初始化 Logger
        # 优先使用策略名称
        strategy_name = getattr(strategy_context, "strategy_name", "Gateway")
        self.logger = setup_strategy_logger(strategy_name, "strategy.log")

    def _log(self, msg: str) -> None:
        if self.logger:
            self.logger.info(f"[Gateway] {msg}")
        else:
            print(f"[Gateway] {msg}")