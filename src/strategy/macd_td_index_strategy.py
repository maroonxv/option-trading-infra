"""
MacdTdIndexStrategy - 商品波动率策略入口

VnPy 策略模板的接口层实现。
作为 VnPy 回调入口和适配器，将回调转换为应用层调用。

设计原则:
1. 仅作为 VnPy 回调的入口和适配器
2. 不包含业务逻辑，只做组装和转发
3. 依赖注入: self -> StrategyEngine -> VnpyTradeGateway
"""
from typing import Any, Dict, Optional
from pathlib import Path
import os
from datetime import datetime


from vnpy_portfoliostrategy import StrategyTemplate, StrategyEngine
from vnpy_portfoliostrategy.utility import PortfolioBarGenerator
from vnpy.trader.object import BarData, OrderData, TradeData, PositionData, TickData
from vnpy.trader.constant import Interval
from vnpy.event.engine import Event


from .application.volatility_trade import StrategyEngine
from .domain.domain_service.indicator_service import IndicatorService
from .domain.domain_service.signal_service import SignalService
from .domain.domain_service.position_sizing_service import PositionSizingService
from .domain.domain_service.option_selector_service import OptionSelectorService
from .domain.domain_service.future_selection_service import BaseFutureSelector
from .domain.event.event_types import EVENT_STRATEGY_ALERT
from .infrastructure.reporting.feishu_handler import FeishuEventHandler
from .infrastructure.logging.logging_utils import setup_strategy_logger
from .infrastructure.persistence.history_data_repository import HistoryDataRepository


class MacdTdIndexStrategy(StrategyTemplate):
    """
    商品波动率策略
    
    职责:
    1. 组装: 在 on_init 中实例化 Application Layer (并将 self 传递给它)
    2. 适配: 将 VnPy 的 on_bars, on_trade 等回调转换为 Application Layer 的调用
    
    参数:
    - underlying_symbols: 监控的标的期货代码列表
    - feishu_webhook: 飞书群机器人 Webhook URL
    - max_positions: 最大持仓数量
    - position_ratio: 单次开仓资金比例
    - strike_level: 虚值档位
    """
    
    # 策略参数
    author = "Hongxu Lai"
    
    # 标的合约列表 (期货)
    underlying_symbols: list = []
    
    # 飞书通知
    feishu_webhook: str = ""
    
    # 仓位管理
    max_positions: int = 5
    position_ratio: float = 0.1
    
    # 期权选择
    strike_level: int = 3
    
    # MACD 参数
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # EMA 参数
    ema_fast: int = 5
    ema_slow: int = 20
    
    # K线合成参数
    bar_window: int = 15          # K线合成窗口（默认1分钟，不合成）
    bar_interval: str = "MINUTE" # K线合成周期（MINUTE/HOUR/DAILY）
    
    
    def __init__(
        self,
        strategy_engine: StrategyEngine,
        strategy_name: str,
        vt_symbols: list,
        setting: dict
    ) -> None:
        """
        初始化策略
        
        Args:
            strategy_engine: VnPy 策略引擎
            strategy_name: 策略名称
            vt_symbols: 合约代码列表
            setting: 策略设置
        """
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)
        
        # 初始化日志
        # 优先从 setting 中获取 log_dir (由 ChildProcess 注入)
        log_dir_setting = setting.get("log_dir", "")
        log_filename = "strategy.log"
        
        if log_dir_setting:
            # 如果是 data/logs/15m 这种路径，我们需要提取相对于 data/logs 的部分
            # 因为 setup_strategy_logger 内部已经拼了 project_root / "data" / "logs"
            if "data/logs" in log_dir_setting:
                relative_log_dir = os.path.relpath(log_dir_setting, os.path.join("data", "logs"))
                if relative_log_dir != ".":
                    log_filename = os.path.join(relative_log_dir, "strategy.log")
            elif "data\\logs" in log_dir_setting:
                relative_log_dir = os.path.relpath(log_dir_setting, os.path.join("data", "logs"))
                if relative_log_dir != ".":
                    log_filename = os.path.join(relative_log_dir, "strategy.log")
        
        self.logger = setup_strategy_logger(self.strategy_name, log_filename)
        
        # 基础设施: 历史数据仓库
        self.history_repo = HistoryDataRepository(self.logger)

        # 模拟交易标志
        self.paper_trading = setting.get("paper_trading", False)
        
        # 回测模式标志
        self.backtesting = setting.get("backtesting", False)

        self.warmup_days: int = int(setting.get("warmup_days", 5 if self.backtesting else 30))
        
        # 应用服务 (在 on_init 中初始化)
        self.app_service: Optional[StrategyEngine] = None
        self.feishu_handler: Optional[FeishuEventHandler] = None
        
        # K线合成器 (在 on_init 中初始化)
        self.pbg: Optional[PortfolioBarGenerator] = None
        
        # 换月检查标志位
        self.rollover_check_done: bool = False
        
        # 补漏检查计数器 (每 60 分钟触发一次)
        self.universe_check_interval: int = 0
        self.universe_check_threshold: int = 60
        
        # 缓存最新 Bar 数据 (用于回测时 Gateway 获取非标的合约行情)
        self.last_bars: Dict[str, BarData] = {}

        self.warming_up: bool = False
    
    def on_init(self) -> None:
        """
        策略初始化回调
        
        组装依赖:
        1. 创建领域服务
        2. 创建应用服务 (注入 self)
        3. 创建并注册飞书处理器
        4. 加载历史数据
        """
        self.logger.info("策略初始化...")

        # ______________________________  1. 加载交易品种配置  ______________________________

        from src.main.utils.config_loader import ConfigLoader
        self.target_products = ConfigLoader.load_target_products()
        if not self.target_products:
            self.logger.error("未配置任何交易品种，请先检查并配置 target_products.yaml")
            raise RuntimeError("策略初始化失败：未配置交易品种")
        else:
            self.logger.info(f"已加载配置的标的: {len(self.target_products)} 个品种")

        # ______________________________  2. 创建领域服务  ______________________________

        indicator_service = IndicatorService(
            macd_fast=self.macd_fast,
            macd_slow=self.macd_slow,
            macd_signal=self.macd_signal,
            ema_fast=self.ema_fast,
            ema_slow=self.ema_slow
        )
        
        signal_service = SignalService()
        
        position_sizing_service = PositionSizingService(
            max_positions=self.max_positions,
            position_ratio=self.position_ratio
        )
        
        future_selection_service = BaseFutureSelector()
        
        option_selector_service = OptionSelectorService(
            strike_level=self.strike_level
        )

        # ______________________________  3. 组装应用服务  ______________________________

        self.app_service = StrategyEngine(
            strategy_context=self,
            indicator_service=indicator_service,
            signal_service=signal_service,
            position_sizing_service=position_sizing_service,
            future_selection_service=future_selection_service,
            option_selector_service=option_selector_service,
            target_products=self.target_products
        )


        # ______________________________  4. 初始化组合K线生成器  ______________________________

        interval_map = {
            "MINUTE": Interval.MINUTE,
            "HOUR": Interval.HOUR,
            "DAILY": Interval.DAILY,
        }
        interval = interval_map.get(self.bar_interval, Interval.MINUTE)
        
        self.pbg = PortfolioBarGenerator(
            on_bars=self.on_bars,
            window=self.bar_window,
            on_window_bars=self.on_window_bars,
            interval=interval
        )
        self.logger.info(f"K线生成器已启用: {self.bar_window}{self.bar_interval}")

        # ______________________________  5. warmup 初始化行情状态  ______________________________

        original_trading = getattr(self, "trading", True)

        if self.backtesting:
            # 5.1 回测 warmup: load_bars
            self.logger.info("当前处于回测模式，跳过状态恢复，直接加载历史数据进行初始化")
            self.warming_up = True
            setattr(self, "trading", False)
            try:
                self.load_bars(self.warmup_days)
            except Exception:
                self.logger.error("回测 warmup 失败", exc_info=True)
                raise
            finally:
                setattr(self, "trading", original_trading)
                self.warming_up = False
        else:
            # 5.2 实盘 warmup: load_state + universe_validation + MySQL replay
            project_root = Path(__file__).resolve().parents[2]
            pickle_dir = project_root / "data" / "pickle"
            pickle_dir.mkdir(parents=True, exist_ok=True)

            state_path = str(pickle_dir / f"{self.strategy_name}.state.pkl")

            if self.app_service:
                try:
                    loaded = self.app_service.load_state(state_path)
                    if not loaded:
                        self.logger.warning(f"未加载到策略状态: {state_path}")
                except Exception:
                    self.logger.error(f"加载策略状态失败: {state_path}", exc_info=True)
                    raise

                try:
                    self.app_service.handle_universe_validation()
                except Exception:
                    self.logger.error("实盘补漏/主力合约初始化失败", exc_info=True)
                    raise

                active_contracts = list(self.app_service.target_aggregate.get_all_active_contracts() or [])
                if isinstance(getattr(self, "vt_symbols", None), list):
                    for vt_symbol in active_contracts:
                        if vt_symbol and vt_symbol not in self.vt_symbols:
                            self.vt_symbols.append(vt_symbol)

            self.warming_up = True
            setattr(self, "trading", False)
            try:
                # 准备回放的合约列表
                vt_symbols = []
                if self.app_service:
                    vt_symbols = list(self.app_service.target_aggregate.get_all_active_contracts() or [])
                elif isinstance(getattr(self, "vt_symbols", None), list):
                    vt_symbols = list(self.vt_symbols)
                
                # 执行回放
                ok = self.history_repo.replay_bars_from_database(
                    vt_symbols=vt_symbols,
                    days=self.warmup_days,
                    on_bars_callback=self.on_bars
                )
                
                if not ok:
                    self.logger.error("实盘 warmup 失败: MySQL 中未能回放到有效 K 线")
                    raise RuntimeError("live warmup failed")
            except Exception:
                self.logger.error("实盘 warmup 执行失败", exc_info=True)
                raise
            finally:
                setattr(self, "trading", original_trading)
                self.warming_up = False

        # ______________________________  6. 注册飞书告警  ______________________________
        if self.feishu_webhook:
            self.feishu_handler = FeishuEventHandler(
                webhook_url=self.feishu_webhook,
                strategy_name=self.strategy_name
            )
            
            if hasattr(self, "strategy_engine") and hasattr(self.strategy_engine, "event_engine"):
                self.strategy_engine.event_engine.register(
                    EVENT_STRATEGY_ALERT,
                    self.feishu_handler.handle_alert_event
                )
                self.logger.info("飞书通知已启用")

        # ______________________________  7. 初始化完成  ______________________________

        self.logger.info("策略初始化完成")
    
    def on_start(self) -> None:
        """策略启动回调"""
        try:
            super().on_start()
        except Exception:
            pass

        self.logger.info("策略启动")
        
        # 验证并初始化主力合约 (补漏)
        if self.app_service:
            self.app_service.handle_universe_validation()
    
    def on_stop(self) -> None:
        """策略停止回调"""
        try:
            super().on_stop()
        except Exception:
            pass

        self.logger.info("策略停止")
        
        # 保存状态 (Pickle) - 仅在非回测模式下保存
        if self.app_service and not self.backtesting:
            project_root = Path(__file__).resolve().parents[2]
            pickle_path = str(project_root / "data" / "pickle" / f"{self.strategy_name}.state.pkl")
            self.app_service.dump_state(pickle_path)
        
        # 注销飞书处理器
        if self.feishu_handler:
            if hasattr(self, "strategy_engine") and hasattr(self.strategy_engine, "event_engine"):
                try:
                    self.strategy_engine.event_engine.unregister(
                        EVENT_STRATEGY_ALERT,
                        self.feishu_handler.handle_alert_event
                    )
                except Exception:
                    pass
    
 
    def on_order(self, order: OrderData) -> None:
        """
        订单推送回调
        
        Args:
            order: 订单对象
        """
        if self.app_service:
            order_data = {
                "vt_orderid": order.vt_orderid,
                "vt_symbol": order.vt_symbol,
                "direction": order.direction.value if hasattr(order.direction, "value") else str(order.direction),
                "offset": order.offset.value if hasattr(order.offset, "value") else str(order.offset),
                "price": order.price,
                "volume": order.volume,
                "traded": order.traded,
                "status": order.status.value if hasattr(order.status, "value") else str(order.status),
            }
            self.app_service.handle_order_update(order_data)
    
    def on_trade(self, trade: TradeData) -> None:
        """
        成交推送回调
        
        Args:
            trade: 成交对象
        """
        if self.app_service:
            trade_data = {
                "vt_tradeid": trade.vt_tradeid,
                "vt_orderid": trade.vt_orderid,
                "vt_symbol": trade.vt_symbol,
                "direction": trade.direction.value if hasattr(trade.direction, "value") else str(trade.direction),
                "offset": trade.offset.value if hasattr(trade.offset, "value") else str(trade.offset),
                "price": trade.price,
                "volume": trade.volume,
                "datetime": trade.datetime,
            }
            self.app_service.handle_trade_update(trade_data)
    
    def process_position_event(self, event: Event) -> None:
        """
        自定义的持仓事件处理函数
        """
        # 从事件中提取 PositionData
        position = event.data
        
        # 调用策略原本的 on_position
        self.on_position(position)

    def on_position(self, position: PositionData) -> None:
        """
        持仓推送回调 (用于检测手动平仓)
        
        Args:
            position: 持仓对象
        """
        if self.app_service:
            position_data = {
                "vt_symbol": position.vt_symbol,
                "direction": position.direction.value if hasattr(position.direction, "value") else str(position.direction),
                "volume": position.volume,
                "frozen": position.frozen,
                "price": position.price,
                "pnl": position.pnl,
            }
            self.app_service.handle_position_update(position_data)
    
    def on_tick(self, tick: TickData) -> None:
        """
        Tick 推送回调
        """
        if self.pbg:
            self.pbg.update_tick(tick)

    def on_bars(self, bars: Dict[str, BarData]) -> None:
        """
        K 线推送回调（1分钟K线）
        
        如果启用了K线合成器，则将1分钟K线推送给合成器
        否则直接转发给应用层
        
        Args:
            bars: K 线字典 {vt_symbol: BarData}
        """
        
        # 缓存最新 Bar 数据
        self.last_bars.update(bars)
        
        if self.app_service and not self.warming_up:
            first_bar = list(bars.values())[0]
            current_dt = first_bar.datetime
            
            if current_dt.hour == 14 and current_dt.minute == 50:
                if not self.rollover_check_done:
                    self.logger.info(f"触发每日换月检查: {current_dt}")
                    self.app_service.handle_universe_rollover_check(current_dt)
                    self.rollover_check_done = True
            else:
                self.rollover_check_done = False
                
            self.universe_check_interval += 1
            if self.universe_check_interval >= self.universe_check_threshold:
                self.universe_check_interval = 0
                self.app_service.handle_universe_validation()

        if self.pbg:
            self.pbg.update_bars(bars)
        else:
            if self.app_service:
                self.app_service.handle_bars(bars)
    
    def on_window_bars(self, bars: Dict[str, BarData]) -> None:
        """
        合成K线回调
        """
        self.logger.debug(f"on_window_bars received: {list(bars.keys())}")
        if self.app_service:
            self.app_service.handle_bars(bars)
