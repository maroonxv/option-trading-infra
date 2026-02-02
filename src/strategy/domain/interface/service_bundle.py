"""
服务包数据类 (ServiceBundle)

职责: 聚合所有策略所需的服务接口

设计原则:
- 作为依赖注入的容器
- 包含所有必需的服务接口字段
- 由 GenericStrategyAdapter.setup_services() 返回
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .indicator_service import IIndicatorService
    from .signal_service import ISignalService
    from .position_sizing_service import IPositionSizingService
    from src.strategy.domain.domain_service.future_selection_service import BaseFutureSelector
    from src.strategy.domain.domain_service.option_selector_service import OptionSelectorService


@dataclass
class ServiceBundle:
    """
    领域服务包
    
    聚合所有策略所需的服务接口，由 GenericStrategyAdapter.setup_services() 返回。
    
    字段名严格对应 domain/domain_service 下的模块定义，确保框架能够正确注入。
    
    属性:
        indicator_service (IIndicatorService): 指标计算服务
        signal_service (ISignalService): 信号生成服务
        position_sizing_service (IPositionSizingService): 仓位计算与风控服务
        future_selection_service (BaseFutureSelector): 期货标的筛选服务
        option_selector_service (OptionSelectorService): 期权选择服务
    
    示例:
        >>> from src.strategy.domain.interface import ServiceBundle
        >>> from my_strategy import MyIndicatorService, MySignalService, MyPositionSizing
        >>> from src.strategy.domain.domain_service import BaseFutureSelector, OptionSelectorService
        >>> 
        >>> services = ServiceBundle(
        ...     indicator_service=MyIndicatorService(),
        ...     signal_service=MySignalService(),
        ...     position_sizing_service=MyPositionSizing(),
        ...     future_selection_service=BaseFutureSelector(),
        ...     option_selector_service=OptionSelectorService()
        ... )
    """

    indicator_service: "IIndicatorService"
    signal_service: "ISignalService"
    position_sizing_service: "IPositionSizingService"
    future_selection_service: "BaseFutureSelector"
    option_selector_service: "OptionSelectorService"
