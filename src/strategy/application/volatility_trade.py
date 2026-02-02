"""
VolatilityTrade - 波动率策略应用服务

编排两个聚合根的协作，调用领域服务计算指标，
将领域事件转换为 VnPy Event，协调开仓/平仓业务流程。

设计模式: Application Service + Doer (执行者)

依赖注入:
MacdTdIndexStrategy (Interface) 
    -> VolatilityTrade (Application) 
        -> VnpyTradeGateway (Infrastructure)
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..domain.aggregate.target_instrument_aggregate import TargetInstrumentAggregate
from ..domain.aggregate.position_aggregate import PositionAggregate
from ..domain.domain_service.indicator_service import IndicatorService
from ..domain.domain_service.signal_service import SignalService
from ..domain.domain_service.position_sizing_service import PositionSizingService
from ..domain.domain_service.option_selector_service import OptionSelectorService
from ..domain.domain_service.future_selection_service import FutureSelectionService
from ..domain.value_object.signal_type import SignalType
from ..domain.value_object.macd_value import MACDValue
from ..domain.value_object.dullness_state import DullnessState
from ..domain.value_object.divergence_state import DivergenceState
from ..domain.value_object.order_instruction import Direction, Offset, OrderInstruction
from ..domain.entity.order import Order
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


class VolatilityTrade:
    """
    波动率策略应用服务
    
    职责:
    1. 编排两个聚合根 (TargetInstrumentAggregate, PositionAggregate) 的协作
    2. 调用领域服务计算指标 (IndicatorService, SignalService)
    3. 将领域事件转换为 VnPy Event 并发布
    4. 协调开仓/平仓业务流程
    
    设计模式:
    - Application Service: 编排领域层组件
    - Doer: 接收 PositionSizingService 的决策，通过 Gateway 执行
    """
    
    def __init__(
        self,
        strategy_context: Any,
        target_products: Optional[List[str]] = None,
        indicator_service: Optional[IndicatorService] = None,
        signal_service: Optional[SignalService] = None,
        position_sizing_service: Optional[PositionSizingService] = None,
        option_selector_service: Optional[OptionSelectorService] = None
    ) -> None:
        """
        初始化应用服务
        
        Args:
            strategy_context: 接口层传入的策略实例
            target_products: 目标交易品种列表 (配置上下文)
            indicator_service: 指标服务
            signal_service: 信号服务
            position_sizing_service: 仓位服务
            option_selector_service: 期权选择服务
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
        self.target_aggregate = TargetInstrumentAggregate()
        self.position_aggregate = PositionAggregate()
        
        # 3. 领域服务初始化
        self.indicator_service = indicator_service or IndicatorService()
        self.position_sizing_service = position_sizing_service or PositionSizingService()
        self.option_selector_service = option_selector_service or OptionSelectorService()
        self.future_selection_service = FutureSelectionService()
        
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
    
    # ========== 持久化相关方法 ==========

    def _record_snapshot(self) -> None:
        self.monitor.record_snapshot(
            target_aggregate=self.target_aggregate,
            position_aggregate=self.position_aggregate,
            strategy_context=self.strategy_context
        )

    def dump_state(self, file_path: str) -> None:
        """
        保存策略运行时状态到文件
        """
        snapshot = {
            "version": 2,
            "saved_at": datetime.now(),
            "target_aggregate": self.target_aggregate.to_snapshot(),
            "position_aggregate": self.position_aggregate.to_snapshot(),
        }
        
        self.state_repository.save(file_path, snapshot)

    def load_state(self, file_path: str) -> bool:
        """
        从文件恢复策略运行时状态
        
        Returns:
            bool: 是否成功恢复
        """
        state = self.state_repository.load(file_path)
        if not state or not isinstance(state, dict):
            return False

        try:
            # 恢复聚合根状态
            # 1. PositionAggregate
            pos_snapshot = state.get("position_aggregate", {})
            self.position_aggregate = PositionAggregate.from_snapshot(pos_snapshot)

            # 2. TargetInstrumentAggregate
            target_snapshot = state.get("target_aggregate", {})
            if target_snapshot:
                self.target_aggregate = TargetInstrumentAggregate.from_snapshot(target_snapshot)
            
            return True
            
        except Exception as e:
            self.logger.error(f"恢复策略状态失败: {str(e)}")
            return False

    def resubscribe_active_contracts(self) -> None:
        active_contracts = self.target_aggregate.get_all_active_contracts()
        all_contracts = self.market_gateway.get_all_contracts()

        unique_contracts: List[str] = []
        seen = set()
        for vt_symbol in active_contracts:
            if vt_symbol and vt_symbol not in seen:
                seen.add(vt_symbol)
                unique_contracts.append(vt_symbol)

        for vt_symbol in unique_contracts:
            self.market_gateway.subscribe(vt_symbol)

        option_seen = set()
        for underlying_vt_symbol in unique_contracts:
            option_vt_symbols = ContractHelper.get_option_vt_symbols(
                all_contracts,
                underlying_vt_symbol,
                log_func=self.logger.warning
            )
            for option_vt_symbol in option_vt_symbols:
                if option_vt_symbol and option_vt_symbol not in option_seen:
                    option_seen.add(option_vt_symbol)
                    self.market_gateway.subscribe(option_vt_symbol)

        self.logger.info(f"已重新订阅活跃合约: {len(unique_contracts)}")

    # ========== 接口层调用的方法 ==========    
    
    def handle_universe_validation(self) -> None:
        """
        验证并确保交易标的完备性 (补漏逻辑)
        遍历配置的目标品种 (_target_scope)，检查聚合根中是否已有对应的活跃合约。
        如果缺失，则尝试从市场网关获取并初始化。
        该方法是幂等的。
        """
        all_contracts = self.market_gateway.get_all_contracts()
        current_date = datetime.now().date()

        self.resubscribe_active_contracts()

        for product in self._target_scope:
            # 1. 检查是否已存在
            if self.target_aggregate.get_active_contract(product):
                continue

            # 2. 补漏: 筛选该品种的期货合约
            product_contracts = [
                c for c in all_contracts 
                if ContractHelper.is_contract_of_product(c, product) and not getattr(c, "option_type", None)
            ]

            if not product_contracts:
                # 依然未找到，可能未上市或未推送
                continue

            # 3. 选择主力合约
            target_contract = self.future_selection_service.select_dominant_contract(
                product_contracts, current_date
            )

            if target_contract:
                self.logger.info(f"补录 {product} 的主力合约: {target_contract.vt_symbol}")
                # 4. 更新状态
                self.target_aggregate.set_active_contract(product, target_contract.vt_symbol)

                # 5. 订阅行情
                self.market_gateway.subscribe(target_contract.vt_symbol)
                option_vt_symbols = ContractHelper.get_option_vt_symbols(
                    all_contracts,
                    target_contract.vt_symbol,
                    log_func=self.logger.warning
                )
                for option_vt_symbol in option_vt_symbols:
                    self.market_gateway.subscribe(option_vt_symbol)



    def handle_universe_rollover_check(self, current_time: datetime) -> None:
        """
        检查并执行换月逻辑
        """
        all_contracts = self.market_gateway.get_all_contracts()
        current_date = current_time.date()

        # 遍历配置范围内的品种，而不是只遍历已激活的
        # 这样如果在换月检查时发现有漏的，也能顺便补上(虽然主要靠 validation)
        for product in self._target_scope:
            old_vt_symbol = self.target_aggregate.get_active_contract(product)

            # 1. 筛选新一轮候选
            product_contracts = [
                c for c in all_contracts 
                if ContractHelper.is_contract_of_product(c, product) and not getattr(c, "option_type", None)
            ]

            if not product_contracts:
                continue

            # 2. 选择新的主力
            new_contract = self.future_selection_service.select_dominant_contract(
                product_contracts, current_date
            )

            if not new_contract:
                continue

            # 3. 判断变化
            if old_vt_symbol != new_contract.vt_symbol:
                if old_vt_symbol:
                    self.logger.info(f"品种 {product} 触发换月: {old_vt_symbol} -> {new_contract.vt_symbol}")
                    # 发布告警
                    self._publish_alert(
                        "rollover",
                        f"品种 {product} 换月: {old_vt_symbol} -> {new_contract.vt_symbol}",
                        new_contract.vt_symbol
                    )
                else:
                    self.logger.info(f"品种 {product} 初始录入 (换月检查时): {new_contract.vt_symbol}")
                
                # 4. 更新状态
                self.target_aggregate.set_active_contract(product, new_contract.vt_symbol)
                
                # 5. 订阅新合约
                self.market_gateway.subscribe(new_contract.vt_symbol)
                option_vt_symbols = ContractHelper.get_option_vt_symbols(
                    all_contracts,
                    new_contract.vt_symbol,
                    log_func=self.logger.warning
                )
                for option_vt_symbol in option_vt_symbols:
                    self.market_gateway.subscribe(option_vt_symbol)
    
    def handle_bar_update(self, vt_symbol: str, bar_data: dict) -> None:
        """
        处理单个标的 K 线更新
        
        编排流程:
        1. 更新聚合根数据
        2. 调用领域服务计算指标
        3. 调用领域服务检查信号
        4. 执行交易逻辑
        5. 处理领域事件
        
        Args:
            vt_symbol: 合约代码
            bar_data: K 线数据字典
        """
        # 1. 更新行情数据
        instrument = self.target_aggregate.update_bar(vt_symbol, bar_data)
        # 1. 更新行情数据
        # 避免打印完整的 instrument 对象，因为它包含 DataFrame，且在 traceback 中可能导致 Loguru 格式化错误
        self.logger.debug(f"vt_symbol: {vt_symbol}, bars_count: {len(instrument.bars)}")
        
        # 检查数据量是否足够
        if not self.target_aggregate.has_enough_data(vt_symbol):
            return
        
        # 2. 计算指标 (调用领域服务)
        prev_dullness = instrument.dullness_state
        prev_divergence = instrument.divergence_state
        
        result = self.indicator_service.calculate_all(
            instrument,
            prev_dullness=prev_dullness,
            prev_divergence=prev_divergence,
            log_func=self.logger.debug
        )

        if result.macd_value:
            self.logger.debug(
                f"[DEBUG-IND] {vt_symbol} Time:{bar_data.get('datetime')} Price:{bar_data.get('close_price')} "
                f"MACD(dif={result.macd_value.dif:.3f}, dea={result.macd_value.dea:.3f}, macd_bar={result.macd_value.macd_bar:.3f}) "
                f"EMA(fast={result.ema_state.fast_ema:.3f}, slow={result.ema_state.slow_ema:.3f})"
            )
        
        if not result.is_complete or result.macd_value is None:
            return
        
        # 3. 检查钝化/背离状态 (已在 IndicatorService 中计算)
        dullness = result.dullness_state
        divergence = result.divergence_state
        
        if dullness.is_top_active or dullness.is_bottom_active:
            self.logger.debug(f"[DEBUG-DULL] {vt_symbol} Top:{dullness.is_top_active} Bottom:{dullness.is_bottom_active}")

        if divergence.is_top_confirmed or divergence.is_bottom_confirmed:
            self.logger.debug(f"[DEBUG-DIV] {vt_symbol} TopConf:{divergence.is_top_confirmed} BottomConf:{divergence.is_bottom_confirmed}")
        
        # 4. 更新聚合根状态
        self.target_aggregate.update_indicators(
            vt_symbol,
            result.macd_value,
            result.td_value,
            result.ema_state,
            dullness,
            divergence
        )
        
        # 5. 检查并执行交易
        can_trade = bool(getattr(self.strategy_context, "trading", True))
        if can_trade:
            self._check_and_execute_close(vt_symbol)
            self._check_and_execute_open(vt_symbol)
        
        # 7. 处理领域事件
        self._publish_domain_events()
    
    def handle_bars(self, bars: Dict[str, Any]) -> None:
        """
        处理多个 K 线更新 (由接口层的 on_bars 调用)
        
        Args:
            bars: K 线字典 {vt_symbol: BarData}
        """
        # 获取当前激活的所有主力合约
        active_contracts = self.target_aggregate.get_all_active_contracts()
        
        for vt_symbol, bar in bars.items():
            # 过滤非标的合约 (例如期权合约)
            # 只有在 active_contracts 中的合约才是我们需要计算信号的标的
            if vt_symbol not in active_contracts:
                continue
            
            bar_dt = getattr(bar, "datetime", None)
            if isinstance(bar_dt, datetime):
                self.current_dt = bar_dt

            # 转换为字典格式
            bar_data = {
                "datetime": getattr(bar, "datetime", datetime.now()),
                "open": getattr(bar, "open_price", 0),
                "high": getattr(bar, "high_price", 0),
                "low": getattr(bar, "low_price", 0),
                "close": getattr(bar, "close_price", 0),
                "volume": getattr(bar, "volume", 0),
            }
            self.handle_bar_update(vt_symbol, bar_data)
        
        # 处理完一轮 Bar 后，保存快照
        if bool(getattr(self.strategy_context, "trading", True)) and not bool(getattr(self.strategy_context, "warming_up", False)):
            self._record_snapshot()
    
    def handle_order_update(self, order_data: dict) -> None:
        """
        处理订单更新
        
        Args:
            order_data: 订单数据字典
        """
        self.position_aggregate.update_from_order(order_data)
        self._publish_domain_events()
        self._record_snapshot()
    
    def handle_trade_update(self, trade_data: dict) -> None:
        """
        处理成交更新
        
        Args:
            trade_data: 成交数据字典
        """
        self.position_aggregate.update_from_trade(trade_data)
        
        # 发送成交告警
        offset = trade_data.get("offset", "")
        vt_symbol = trade_data.get("vt_symbol", "")
        volume = trade_data.get("volume", 0)
        price = trade_data.get("price", 0.0)
        direction = trade_data.get("direction", "")
        
        # 简单判断开平仓 (根据接口层传入的字符串值)
        # 注意: 接口层已将枚举转换为 value (如 "开", "平") 或英文字符串
        is_open = "开" in str(offset) or "OPEN" in str(offset).upper()
        
        if is_open:
             self._publish_alert(
                 "position_opened",
                 f"开仓成交: {vt_symbol} {direction} 手数：{volume} 价格：{price}",
                 vt_symbol,
                 volume
             )
        else:
             self._publish_alert(
                 "position_closed",
                 f"平仓成交: {vt_symbol} {direction} 手数：{volume} 价格：{price}",
                 vt_symbol,
                 volume
             )

        # 风控状态更新已下沉到 PositionAggregate.update_from_trade
        self._publish_domain_events()
        self._record_snapshot()
    
    def handle_position_update(self, position_data: dict) -> None:
        """
        处理持仓更新
        
        Args:
            position_data: 持仓数据字典
        """
        self.position_aggregate.update_from_position(position_data)
        self._publish_domain_events()
        self._record_snapshot()
    
    # ========== 私有方法 ==========
    
    def _check_and_execute_open(self, vt_symbol: str) -> None:
        """检查并执行开仓"""
        if not bool(getattr(self.strategy_context, "trading", True)):
            return

        # 1. 每日限额重置逻辑
        current_date = self._get_current_date()
        self.position_aggregate.on_new_trading_day(current_date)

        instrument = self.target_aggregate.get_instrument(vt_symbol)
        if instrument is None:
            return
        
        # 检查开仓信号
        open_signal = SignalService.check_open_signal(instrument, log_func=self.logger.debug)
        if not open_signal:
            return

        open_bar_dt = None
        try:
            bars_df = getattr(instrument, "bars", None)
            if bars_df is not None and not getattr(bars_df, "empty", True):
                open_bar_dt = self.monitor.parse_bar_dt(bars_df.iloc[-1].get("datetime"))
        except Exception:
            open_bar_dt = None
        
        # 选择期权合约
        option_contract = self._select_option(vt_symbol, open_signal)
        if not option_contract:
            self.logger.warning(f"Option Selection Failed for {vt_symbol}")
            return

        # 计算当前限额使用情况 (已成交 + 挂单中)
        global_reserved = self.position_aggregate.get_reserved_open_volume()
        current_daily_open_count = self.position_aggregate.get_global_daily_open_volume() + global_reserved
        
        current_contract_filled = self.position_aggregate.get_daily_open_volume(option_contract.vt_symbol)
        contract_reserved = self.position_aggregate.get_reserved_open_volume(option_contract.vt_symbol)
        current_contract_open_count = current_contract_filled + contract_reserved

        # 4. 流动性深度检查 (New)
        # 获取最新 Tick 和 Contract 数据
        tick = self.market_gateway.get_tick(option_contract.vt_symbol)
        contract_data = self.market_gateway.get_contract(option_contract.vt_symbol)
        
        if not self.option_selector_service.check_liquidity(tick, contract_data, log_func=self.logger.info):
             return

        # 决策: 调用 PositionSizingService 生成指令 (Tell, Don't Ask)
        # 使用 AccountGateway 获取资金
        instruction_bid = self.position_sizing_service.calculate_open_volumn(
            account_balance=self.account_gateway.get_balance(),
            signal_type=open_signal,
            vt_symbol=option_contract.vt_symbol,
            contract_price=option_contract.bid_price,
            current_positions=self.position_aggregate.get_active_positions(),
            current_daily_open_count=current_daily_open_count,
            current_contract_open_count=current_contract_open_count
        )
        
        if instruction_bid:
            signal_event_key = (
                f"{self.variant_name}|{self.monitor.monitor_instance_id}|{vt_symbol}|"
                f"{(open_bar_dt.isoformat() if open_bar_dt else '')}|{open_signal.value}"
            )
            self.monitor.insert_monitor_event(
                event_type="signal",
                event_key=signal_event_key,
                payload={
                    "signal_type": open_signal.value,
                    "bar_dt": open_bar_dt.isoformat() if open_bar_dt else "",
                    "vt_symbol": vt_symbol,
                    "option_vt_symbol": getattr(option_contract, "vt_symbol", ""),
                    "price_hint": float(getattr(option_contract, "ask_price", 0.0) or 0.0),
                },
                vt_symbol=vt_symbol,
                bar_dt=open_bar_dt,
            )
            # 构造第二笔指令 (Ask Price)
            instruction_ask = OrderInstruction(
                vt_symbol=instruction_bid.vt_symbol,
                direction=instruction_bid.direction,
                offset=instruction_bid.offset,
                volume=instruction_bid.volume,
                price=option_contract.ask_price,
                signal_type=instruction_bid.signal_type
            )

            vt_orderids_bid = self.exec_gateway.send_order(instruction_bid)
            vt_orderids_ask = self.exec_gateway.send_order(instruction_ask)

            filled_intent_volume = 0
            if vt_orderids_bid:
                filled_intent_volume += instruction_bid.volume
            else:
                self.logger.warning(f"开仓下单失败(Bid): {instruction_bid}")

            if vt_orderids_ask:
                filled_intent_volume += instruction_ask.volume
            else:
                self.logger.warning(f"开仓下单失败(Ask): {instruction_ask}")

            if filled_intent_volume <= 0:
                self.logger.warning(
                    f"开仓信号触发但下单未产生订单号: {open_signal.value} 标的: {vt_symbol} 期权: {option_contract.vt_symbol}"
                )
                return

            self.position_aggregate.create_position(
                option_vt_symbol=option_contract.vt_symbol,
                underlying_vt_symbol=vt_symbol,
                signal_type=open_signal,
                target_volume=filled_intent_volume
            )
            
            self.logger.info(
                f"触发开仓信号(双价下单): {open_signal.value} 标的: {vt_symbol} "
                f"期权: {option_contract.vt_symbol} 总数量: {filled_intent_volume}"
            )

            # 记录订单 Bid
            for vt_orderid in vt_orderids_bid:
                order = Order(
                    vt_orderid=vt_orderid,
                    vt_symbol=instruction_bid.vt_symbol,
                    direction=instruction_bid.direction,
                    offset=instruction_bid.offset,
                    volume=instruction_bid.volume,
                    price=instruction_bid.price,
                    signal_type=open_signal
                )
                self.position_aggregate.add_pending_order(order)
            
            # 记录订单 Ask
            for vt_orderid in vt_orderids_ask:
                order = Order(
                    vt_orderid=vt_orderid,
                    vt_symbol=instruction_ask.vt_symbol,
                    direction=instruction_ask.direction,
                    offset=instruction_ask.offset,
                    volume=instruction_ask.volume,
                    price=instruction_ask.price,
                    signal_type=open_signal
                )
                self.position_aggregate.add_pending_order(order)

            # 发布告警
            self._publish_alert(
                "open_signal",
                f"开仓信号（双卖）: {open_signal.value}, 合约: {option_contract.vt_symbol}\n1. ({instruction_bid.direction.value}) 价格：{instruction_bid.price} 手数：{instruction_bid.volume}\n2. ({instruction_ask.direction.value}) 价格：{instruction_ask.price} 手数：{instruction_ask.volume}",
                option_contract.vt_symbol,
                filled_intent_volume
            )
        else:
            self.logger.info(f"仓位管理拒绝开仓: {vt_symbol}")
    
    def _check_and_execute_close(self, underlying_vt_symbol: str) -> None:
        """检查并执行平仓"""
        if not bool(getattr(self.strategy_context, "trading", True)):
            return

        instrument = self.target_aggregate.get_instrument(underlying_vt_symbol)
        if instrument is None:
            return
        
        positions = self.position_aggregate.get_positions_by_underlying(underlying_vt_symbol)
        
        for position in positions:
            # 检查平仓信号
            close_signal = SignalService.check_close_signal(position, instrument)
            if not close_signal:
                continue

            close_bar_dt = None
            try:
                bars_df = getattr(instrument, "bars", None)
                if bars_df is not None and not getattr(bars_df, "empty", True):
                    close_bar_dt = self.monitor.parse_bar_dt(bars_df.iloc[-1].get("datetime"))
            except Exception:
                close_bar_dt = None
            
            # 检查是否已有平仓订单
            if self.position_aggregate.has_pending_close(position):
                continue
            
            # 生成平仓指令
            instruction = self.position_sizing_service.calculate_close_volumn(
                position=position,
                close_price=0,  # 市价平仓
                signal_type=close_signal
            )
            
            if instruction:
                close_event_key = (
                    f"{self.variant_name}|{self.monitor.monitor_instance_id}|{position.vt_symbol}|"
                    f"{(close_bar_dt.isoformat() if close_bar_dt else '')}|{close_signal.value}"
                )
                self.monitor.insert_monitor_event(
                    event_type="signal",
                    event_key=close_event_key,
                    payload={
                        "signal_type": close_signal.value,
                        "bar_dt": close_bar_dt.isoformat() if close_bar_dt else "",
                        "vt_symbol": position.vt_symbol,
                        "underlying_vt_symbol": underlying_vt_symbol,
                        "volume": float(getattr(position, "volume", 0) or 0),
                    },
                    vt_symbol=position.vt_symbol,
                    bar_dt=close_bar_dt,
                )
                # 执行: 调用 ExecGateway 下单
                vt_orderids = self.exec_gateway.send_order(instruction)
                
                # 记录订单
                for vt_orderid in vt_orderids:
                    order = Order(
                        vt_orderid=vt_orderid,
                        vt_symbol=instruction.vt_symbol,
                        direction=instruction.direction,
                        offset=instruction.offset,
                        volume=instruction.volume,
                        price=instruction.price,
                        signal_type=close_signal
                    )
                    self.position_aggregate.add_pending_order(order)
                
                # 发布告警
                self._publish_alert(
                    "close_signal",
                    f"平仓信号: {close_signal.value}",
                    position.vt_symbol,
                    position.volume
                )
    
    def _select_option(
        self,
        underlying_vt_symbol: str,
        signal_type: SignalType
    ) -> Optional[Any]:
        """
        选择期权合约 (虚值四档)
        
        Args:
            underlying_vt_symbol: 标的期货代码
            signal_type: 信号类型 (决定选择 Put 还是 Call)
            
        Returns:
            选中的期权合约，或 None
        """
        # 确定期权类型
        if signal_type.is_put_signal():
            option_type = "put"
        else:
            option_type = "call"
        
        # 获取标的当前价格
        underlying_price = self.target_aggregate.get_latest_price(underlying_vt_symbol)
        if underlying_price <= 0:
            return None
        
        # 获取期权合约列表
        # 使用 MarketGateway 获取全部合约，然后筛选
        all_contracts = self.market_gateway.get_all_contracts()
        contracts_df = ContractHelper.get_option_chain(
            all_contracts, 
            underlying_vt_symbol,
            log_func=self.logger.warning
        )
        
        if contracts_df.empty:
            self.logger.warning(f"[DEBUG-OPT] 未找到标的 {underlying_vt_symbol} 的期权链 (全市场合约数: {len(all_contracts)})")
            
            # 深度诊断: 检查是否有合约存在但被过滤
            import re
            symbol_part = underlying_vt_symbol.split(".")[0]
            match = re.match(r"^([a-zA-Z]+)(\d+)", symbol_part)
            if match:
                code = match.group(1).upper()
                suffix = match.group(2)
                # 简单的映射逻辑复现
                map_code = {"IF": "IO", "IM": "MO", "IH": "HO"}.get(code, code)
                prefix = f"{map_code}{suffix}"
                
                potential = [c for c in all_contracts if c.symbol.startswith(prefix)]
                self.logger.warning(f"[DEBUG-OPT] 深度诊断: 发现 {len(potential)} 个疑似合约 (前缀 {prefix})")
                
                if potential:
                    for i, c in enumerate(potential[:5]):
                        self.logger.warning(
                            f"  [疑似合约 {i}] {c.vt_symbol} | Exchange: {c.exchange} | "
                            f"Type: {getattr(c, 'option_type', 'N/A')} | "
                            f"Strike: {getattr(c, 'option_strike', 'N/A')} | "
                            f"Underlying: {getattr(c, 'underlying_symbol', 'N/A')}"
                        )
                else:
                    self.logger.warning(f"[DEBUG-OPT] 深度诊断: 未发现任何以 {prefix} 开头的合约")

            return None
            
        # 填充实时行情数据
        # 注意: 这里需要逐个获取 Tick，可能会有性能开销，但在低频策略下通常可接受
        # 如果是高频，建议维护一个 Tick 缓存
        prices = []
        volumes = []
        ask_prices = []
        ask_volumes = []
        
        for vt_symbol in contracts_df["vt_symbol"]:
            tick = self.market_gateway.get_tick(vt_symbol)
            if tick:
                prices.append(tick.bid_price_1)
                volumes.append(tick.bid_volume_1)
                ask_prices.append(tick.ask_price_1)
                ask_volumes.append(tick.ask_volume_1)
            else:
                prices.append(0.0)
                volumes.append(0)
                ask_prices.append(0.0)
                ask_volumes.append(0)
        
        contracts_df["bid_price"] = prices
        contracts_df["bid_volume"] = volumes
        contracts_df["ask_price"] = ask_prices
        contracts_df["ask_volume"] = ask_volumes
        contracts_df["days_to_expiry"] = 30 # 简化处理，后续可优化
        
        # 选择虚值四档
        return self.option_selector_service.select_target_option(
            contracts=contracts_df,
            option_type=option_type,
            underlying_price=underlying_price,
            log_func=self.logger.debug
        )
    
    def _publish_domain_events(self) -> None:
        """将领域事件转换为 VnPy Event 并发布"""
        events = self.position_aggregate.pop_domain_events()
        
        for domain_event in events:
            alert_data = self._create_alert_from_event(domain_event)
            if alert_data and self.event_engine:
                try:
                    # 创建 VnPy Event
                    from vnpy.event import Event
                    vnpy_event = Event(type=EVENT_STRATEGY_ALERT, data=alert_data)
                    self.event_engine.put(vnpy_event)
                except ImportError:
                    # VnPy 未安装，跳过事件发布
                    pass

    def _get_current_date(self):
        if getattr(self.strategy_context, "backtesting", False):
            return self.current_dt.date()
        return datetime.now().date()
    
    def _create_alert_from_event(self, event: DomainEvent) -> Optional[StrategyAlertData]:
        """从领域事件创建告警数据"""
        if isinstance(event, ManualCloseDetectedEvent):
            return StrategyAlertData(
                strategy_name=self.strategy_name,
                alert_type="manual_close",
                message="检测到手动平仓",
                timestamp=event.timestamp,
                vt_symbol=event.vt_symbol,
                volume=event.volume
            )
        elif isinstance(event, ManualOpenDetectedEvent):
            return StrategyAlertData(
                strategy_name=self.strategy_name,
                alert_type="manual_open",
                message="检测到手动开仓",
                timestamp=event.timestamp,
                vt_symbol=event.vt_symbol,
                volume=event.volume
            )
        elif isinstance(event, RiskLimitExceededEvent):
            return StrategyAlertData(
                strategy_name=self.strategy_name,
                alert_type="warning",
                message=f"风控限额警告: {event.limit_type} ({event.current_volume}/{event.limit_volume})",
                timestamp=event.timestamp,
                vt_symbol=event.vt_symbol,
                volume=event.current_volume
            )
        return None
    
    def _publish_alert(
        self,
        alert_type: str,
        message: str,
        vt_symbol: str = "",
        volume: float = 0
    ) -> None:
        """发布告警事件"""
        alert_dt = datetime.now()
        alert_event_key = (
            f"{self.variant_name}|{self.monitor.monitor_instance_id}|{vt_symbol}|"
            f"{alert_dt.isoformat()}|{alert_type}"
        )
        self.monitor.insert_monitor_event(
            event_type="alert",
            event_key=alert_event_key,
            payload={
                "alert_type": alert_type,
                "message": message,
                "timestamp": alert_dt.isoformat(),
                "vt_symbol": vt_symbol,
                "volume": float(volume or 0),
            },
            vt_symbol=vt_symbol,
            bar_dt=None,
            created_at=alert_dt,
        )
        if not self.event_engine:
            return
        
        try:
            from vnpy.event import Event
            
            alert_data = StrategyAlertData(
                strategy_name=self.strategy_name,
                alert_type=alert_type,
                message=message,
                timestamp=alert_dt,
                vt_symbol=vt_symbol,
                volume=volume
            )
            event = Event(type=EVENT_STRATEGY_ALERT, data=alert_data)
            self.event_engine.put(event)
        except ImportError:
            pass
