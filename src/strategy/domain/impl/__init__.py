"""
示例实现模块 (impl)

本模块提供了策略框架核心接口的示例实现，帮助开发者理解如何使用框架开发自定义策略。

包含的示例实现:
- DemoIndicatorService: 指标计算服务示例（MACD, EMA）
- DemoSignalService: 信号生成服务示例（即将实现）
- DemoPositionSizingService: 仓位计算服务示例（即将实现）

使用方式:
    from src.strategy.domain.impl import DemoIndicatorService
    
    indicator_service = DemoIndicatorService(fast_period=12, slow_period=26)
"""

from .demo_indicator_service import DemoIndicatorService

__all__ = [
    "DemoIndicatorService",
]
