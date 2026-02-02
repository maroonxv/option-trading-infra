"""
SPI (Service Provider Interface) 定义模块

本模块定义了策略框架的核心服务接口，开发者通过实现这些接口来定制策略逻辑。
"""

from .indicator_service import IIndicatorService
from .signal_service import ISignalService
from .position_sizing_service import IPositionSizingService
from .service_bundle import ServiceBundle

__all__ = [
    "IIndicatorService",
    "ISignalService",
    "IPositionSizingService",
    "ServiceBundle",
]
