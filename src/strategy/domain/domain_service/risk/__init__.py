"""
风险管理领域服务模块

导出所有风险监控服务类、值对象和配置类。
"""

# 现有服务
from .portfolio_risk_aggregator import PortfolioRiskAggregator
from .position_sizing_service import PositionSizingService

# 新增的五个风险监控服务
from .stop_loss_manager import StopLossManager
from .risk_budget_allocator import RiskBudgetAllocator
from .liquidity_risk_monitor import LiquidityRiskMonitor
from .concentration_monitor import ConcentrationMonitor
from .time_decay_monitor import TimeDecayMonitor

# 值对象和配置类
from ...value_object.risk import (
    # 现有值对象
    RiskThresholds,
    RiskCheckResult,
    PortfolioGreeks,
    PositionGreeksEntry,
    
    # 止损相关
    StopLossConfig,
    StopLossTrigger,
    PortfolioStopLossTrigger,
    
    # 风险预算相关
    RiskBudgetConfig,
    GreeksBudget,
    GreeksUsage,
    BudgetCheckResult,
    
    # 流动性监控相关
    LiquidityMonitorConfig,
    MarketData,
    LiquidityScore,
    LiquidityWarning,
    
    # 集中度监控相关
    ConcentrationConfig,
    ConcentrationMetrics,
    ConcentrationWarning,
    
    # 时间衰减监控相关
    TimeDecayConfig,
    ThetaMetrics,
    ExpiringPosition,
    ExpiryGroup,
)

__all__ = [
    # 现有服务
    "PortfolioRiskAggregator",
    "PositionSizingService",
    
    # 新增的五个风险监控服务
    "StopLossManager",
    "RiskBudgetAllocator",
    "LiquidityRiskMonitor",
    "ConcentrationMonitor",
    "TimeDecayMonitor",
    
    # 现有值对象
    "RiskThresholds",
    "RiskCheckResult",
    "PortfolioGreeks",
    "PositionGreeksEntry",
    
    # 止损相关值对象
    "StopLossConfig",
    "StopLossTrigger",
    "PortfolioStopLossTrigger",
    
    # 风险预算相关值对象
    "RiskBudgetConfig",
    "GreeksBudget",
    "GreeksUsage",
    "BudgetCheckResult",
    
    # 流动性监控相关值对象
    "LiquidityMonitorConfig",
    "MarketData",
    "LiquidityScore",
    "LiquidityWarning",
    
    # 集中度监控相关值对象
    "ConcentrationConfig",
    "ConcentrationMetrics",
    "ConcentrationWarning",
    
    # 时间衰减监控相关值对象
    "TimeDecayConfig",
    "ThetaMetrics",
    "ExpiringPosition",
    "ExpiryGroup",
]
