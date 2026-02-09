"""
StrategyEngine - 策略执行引擎（原 VolatilityTrade）

编排两个聚合根的协作，调用领域服务计算指标，
将领域事件转换为 VnPy Event，协调开仓/平仓业务流程。

设计模式: Application Service + Doer (执行者)

依赖注入:
GenericStrategyAdapter (Interface) 
    -> StrategyEngine (Application) 
        -> VnpyTradeGateway (Infrastructure)
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..domain.aggregate.target_instrument_aggregate import InstrumentManager
from ..domain.aggregate.position_aggregate import PositionAggregate
from ..domain.interface.indicator_service import IIndicatorService
from ..domain.interface.signal_service import ISignalService
from ..domain.interface.position_sizing_service import IPositionSizingService
from ..domain.domain_service.option_selector_service import OptionSelectorService
from ..domain.domain_service.future_selection_service import BaseFutureSelector
from ..domain.value_object.order_instruction import Direction, Offset, OrderInstruction
from ..domain.entity.order import Order
from ..domain.entity.position import Position
from ..domain.event.event_types import (
    EVENT_STRATEGY_ALERT,
    DomainEvent,
    ManualCloseDetectedEvent,
    ManualOpenDetectedEvent,
    RiskLimitExceededEvent,
    StrategyAlertData,
)
from ..infrastructure.gateway.vnpy_market_data_gateway import VnpyMarketDataGateway
from ..infrastructure.gateway.vnpy_account_gateway import VnpyAccountGateway
from ..infrastructure.gateway.vnpy_trade_execution_gateway import VnpyTradeExecutionGateway
from ..infrastructure.logging.logging_utils import setup_strategy_logger
from ..infrastructure.monitoring.strategy_monitor import StrategyMonitor
from ..infrastructure.persistence.state_repository import StateRepository
from ..infrastructure.utils.contract_helper import ContractHelper


class StrategyEngine:
    """
    策略执行引擎（原 VolatilityTrade）

    职责:
    1. 编排两个聚合根 (InstrumentManager, PositionAggregate) 的协作
    2. 调用领域服务计算指标 (IIndicatorService, ISignalService)
    3. 将领域事件转换为 VnPy Event 并发布
    4. 协调开仓/平仓业务流程

    设计模式:
    - Application Service: 编排领域层组件
    - Doer: 接收 PositionSizingService 的决策，通过 Gateway 执行
    """

    def __init__(
        self,
        strategy_context: Any,
        indicator_service: IIndicatorService,
        signal_service: ISignalService,
        position_sizing_service: IPositionSizingService,
        future_selection_service: BaseFutureSelector,
        option_selector_service: OptionSelectorService,
        target_products: Optional[List[str]] = None
    ) -> None:
        """
        初始化策略引擎

        Args:
            strategy_context: 接口层传入的策略实例
            indicator_service: 指标计算服务接口
            signal_service: 信号生成服务接口
            position_sizing_service: 仓位计算服务接口
            future_selection_service: 期货标的筛选服务
            option_selector_service: 期权选择服务
            target_products: 目标交易品种列表 (配置上下文)
        """
        # 0. 配置上下文
        self._target_scope = target_products or []

        # 1. 基础设施初始化
        # 使用分离的网关接口
        self.market_gateway = VnpyMarketDataGateway(strategy_context)
        self.account_gateway = VnpyAccountGateway(strategy_context)
        self.exec_gateway = VnpyTradeExecutionGateway(strategy_context)

        # 获取 EventEngine 用于发布事件 (通过 strategy_engine)
        self.event_engine = None
        if hasattr(strategy_context, "strategy_engine"):
            if hasattr(strategy_context.strategy_engine, "event_engine"):
                self.event_engine = strategy_context.strategy_engine.event_engine

        # 记录 strategy_name 用于日志/告警
        self.strategy_name = getattr(strategy_context, "strategy_name", "VolatilityStrategy")
        self.strategy_context = strategy_context

        # 初始化日志
        # 优先复用 context 里的 logger
        self.logger = getattr(strategy_context, "logger", None)
        if not self.logger:
            log_filename = "strategy.log"
            self.logger = setup_strategy_logger(self.strategy_name, log_filename)

        # 2. 领域聚合根初始化
        self.target_aggregate = InstrumentManager()
        self.position_aggregate = PositionAggregate()

        # 3. 领域服务初始化 - 通过依赖注入
        self.indicator_service = indicator_service
        self.signal_service = signal_service
        self.position_sizing_service = position_sizing_service
        self.future_selection_service = future_selection_service
        self.option_selector_service = option_selector_service

        # 4. 状态缓存初始化
        self.current_dt: datetime = datetime.now()

        # 5. 基础设施组件 (监控与持久化)
        self.variant_name = getattr(strategy_context, "strategy_name", "default")
        project_root = Path(__file__).resolve().parents[3]
        snapshot_path = str(project_root / "data" / "monitor" / f"snapshot_{self.variant_name}.pkl")

        monitor_db_config = {
            "host": os.getenv("VNPY_DATABASE_HOST", "") or "",
            "port": int(os.getenv("VNPY_DATABASE_PORT", "3306") or 3306),
            "user": os.getenv("VNPY_DATABASE_USER", "") or "",
            "password": os.getenv("VNPY_DATABASE_PASSWORD", "") or "",
            "database": os.getenv("VNPY_DATABASE_DATABASE", "") or "",
        }

        self.monitor = StrategyMonitor(
            variant_name=self.variant_name,
            monitor_instance_id=os.getenv("MONITOR_INSTANCE_ID", "default") or "default",
            snapshot_path=snapshot_path,
            monitor_db_config=monitor_db_config,
            logger=self.logger
        )

        self.state_repository = StateRepository(logger=self.logger)

        # 初始快照
        self._record_snapshot()


    def _record_snapshot(self) -> None:
        """记录状态快照"""
        try:
            snapshot = {
                "target_aggregate": self.target_aggregate.to_snapshot(),
                "position_aggregate": self.position_aggregate.to_snapshot(),
                "current_dt": self.current_dt
            }
            self.monitor.record_snapshot(snapshot)
        except Exception as e:
            self.logger.error(f"记录快照失败: {e}")

    def handle_bar_update(self, vt_symbol: str, bar_data: dict) -> None:
        """
        处理 K 线更新
        
        职责:
        1. 更新行情数据到 InstrumentManager
        2. 调用 IIndicatorService 计算指标
        3. 调用 ISignalService 检查开平仓信号
        4. 协调开平仓业务流程
        
        Args:
            vt_symbol: 合约代码
            bar_data: K 线数据字典 (包含 datetime, open, high, low, close, volume)
        
        设计原则:
        - 删除所有具体的 MACD、背离、钝化计算逻辑
        - 通过服务接口调用实现策略逻辑的可插拔性
        - 框架层仅负责编排，不包含具体策略逻辑
        """
        try:
            # 1. 更新行情数据
            instrument = self.target_aggregate.update_bar(vt_symbol, bar_data)
            
            # 2. 调用指标服务计算指标
            # 将指标计算逻辑委托给 IIndicatorService
            try:
                self.indicator_service.calculate_bar(instrument, bar_data)
            except Exception as e:
                self.logger.error(f"指标计算失败 [{vt_symbol}]: {e}")
                # 指标计算失败不中断策略执行
                return
            
            # 3. 检查开仓信号
            # 将信号生成逻辑委托给 ISignalService
            try:
                open_signal = self.signal_service.check_open_signal(instrument)
                if open_signal:
                    self.logger.info(f"检测到开仓信号 [{vt_symbol}]: {open_signal}")
                    self._execute_open(vt_symbol, open_signal)
            except Exception as e:
                self.logger.error(f"开仓信号检查失败 [{vt_symbol}]: {e}")
            
            # 4. 检查平仓信号
            # 遍历该标的下的所有持仓，检查是否需要平仓
            try:
                positions = self.position_aggregate.get_positions_by_underlying(vt_symbol)
                for position in positions:
                    close_signal = self.signal_service.check_close_signal(instrument, position)
                    if close_signal:
                        self.logger.info(
                            f"检测到平仓信号 [{position.vt_symbol}]: {close_signal}"
                        )
                        self._execute_close(position, close_signal)
            except Exception as e:
                self.logger.error(f"平仓信号检查失败 [{vt_symbol}]: {e}")
            
        except Exception as e:
            self.logger.error(f"处理 K 线更新失败 [{vt_symbol}]: {e}")

    def _execute_open(self, underlying_vt_symbol: str, signal: str) -> None:
        """
        执行开仓逻辑
        
        Args:
            underlying_vt_symbol: 标的合约代码
            signal: 开仓信号字符串
        """
        # TODO: 实现开仓逻辑
        # 这部分逻辑将在后续任务中实现
        self.logger.info(f"执行开仓: {underlying_vt_symbol}, 信号: {signal}")
        pass

    def _execute_close(self, position: Position, signal: str) -> None:
        """
        执行平仓逻辑
        
        Args:
            position: 持仓对象
            signal: 平仓信号字符串
        """
        # TODO: 实现平仓逻辑
        # 这部分逻辑将在后续任务中实现
        self.logger.info(f"执行平仓: {position.vt_symbol}, 信号: {signal}")
        pass
