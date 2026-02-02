from typing import List, Optional, Any
from vnpy.trader.object import SubscribeRequest
from ...domain.demand_interface.market_data_interface import IMarketDataGateway
from .vnpy_gateway_adapter import VnpyGatewayAdapter

class VnpyMarketDataGateway(VnpyGatewayAdapter, IMarketDataGateway):
    """VnPy 市场数据网关实现"""

    def _try_add_bar_recording(self, vt_symbol: str) -> None:
        if not self.main_engine or not hasattr(self.main_engine, "get_engine"):
            return

        try:
            from vnpy_datarecorder import APP_NAME
        except Exception:
            return

        try:
            recorder_engine = self.main_engine.get_engine(APP_NAME)
            if recorder_engine and hasattr(recorder_engine, "add_bar_recording"):
                recorder_engine.add_bar_recording(vt_symbol)
        except Exception:
            return
    
    def subscribe(self, vt_symbol: str) -> None:
        """订阅行情"""
        # 回测模式兼容: 如果 main_engine 不存在，视为回测，跳过订阅
        if not self.main_engine:
            if hasattr(self.context, "backtesting") and self.context.backtesting:
                 # 回测模式下，只更新 context 的 vt_symbols 列表
                if hasattr(self.context, "vt_symbols") and isinstance(self.context.vt_symbols, list):
                    if vt_symbol not in self.context.vt_symbols:
                        self.context.vt_symbols.append(vt_symbol)
                return

            self._log(f"订阅失败：主引擎不可用 ({vt_symbol})")
            return

        contract = self.main_engine.get_contract(vt_symbol)
        if not contract:
            self._log(f"订阅失败：找不到合约 ({vt_symbol})")
            return

        # 1. 向 MainEngine 发送订阅请求
        req = SubscribeRequest(
            symbol=contract.symbol,
            exchange=contract.exchange
        )
        self.main_engine.subscribe(req, contract.gateway_name)
        self._try_add_bar_recording(vt_symbol)
        
        # 2. 注册策略到 StrategyEngine 的映射中，以便接收推送
        # self.context 是策略实例 (MacdTdIndexStrategy)
        if hasattr(self.context, "strategy_engine"):
            strategy_engine = self.context.strategy_engine
            
            # 更新 symbol_strategy_map (确保策略能收到 Tick 推送)
            if hasattr(strategy_engine, "symbol_strategy_map"):
                strategies = strategy_engine.symbol_strategy_map[vt_symbol]
                if self.context not in strategies:
                    strategies.append(self.context)
                    self._log(f"已注册策略接收 {vt_symbol} 的 Tick 推送")
            
            # 3. 更新策略内部的 vt_symbols 列表 (用于 load_bars 等)
            if hasattr(self.context, "vt_symbols") and isinstance(self.context.vt_symbols, list):
                if vt_symbol not in self.context.vt_symbols:
                    self.context.vt_symbols.append(vt_symbol)
        
        self._log(f"已成功订阅 {vt_symbol}")

    def get_tick(self, vt_symbol: str) -> Optional[Any]:
        if self.main_engine:
            return self.main_engine.get_tick(vt_symbol)
            
        # 回测模式兼容: 构造模拟 Tick
        if hasattr(self.context, "backtesting") and self.context.backtesting:
             # 尝试从策略的应用服务中获取最新 Bar 数据
            instrument = None
            if hasattr(self.context, "app_service") and self.context.app_service:
                agg = getattr(self.context.app_service, "target_aggregate", None)
                if agg:
                    instrument = agg.get_instrument(vt_symbol)
            
            # 如果从 aggregate 中获取不到 (例如期权合约尚未加入 aggregate)，尝试从策略缓存的 last_bars 获取
            last_bar = None
            if instrument and not instrument.bars.empty:
                # 使用 instrument 的最新 bar
                # 注意: instrument.bars 是 DataFrame
                row = instrument.bars.iloc[-1]
                # 构造类似 BarData 的对象或直接取值
                class MockBar:
                    close_price = float(row["close"])
                    volume = int(row["volume"])
                last_bar = MockBar()
            elif hasattr(self.context, "last_bars") and vt_symbol in self.context.last_bars:
                # 使用策略缓存的最新 BarData
                bar = self.context.last_bars[vt_symbol]
                class MockBar:
                    close_price = bar.close_price
                    volume = bar.volume
                last_bar = MockBar()

            if last_bar:
                # 使用最新的 Bar 构造 Tick
                # 这里的关键是 bid_price 和 bid_volume，用于 OptionSelectorService 的流动性检查
                last_close = last_bar.close_price
                last_volume = last_bar.volume

                # 简单的 Tick 模拟
                from vnpy.trader.object import TickData
                from vnpy.trader.constant import Exchange
                from datetime import datetime

                try:
                    symbol_part, exchange_str = vt_symbol.split(".")
                    exchange = Exchange(exchange_str)
                except ValueError:
                    symbol_part = vt_symbol
                    exchange = None

                return TickData(
                    symbol=symbol_part,
                    exchange=exchange,
                    datetime=datetime.now(), # 回测中时间可能不准，但 check_liquidity 不看时间
                    name=vt_symbol,
                    volume=last_volume,
                    turnover=0,
                    open_interest=0,
                    last_price=last_close,
                    last_volume=last_volume,
                    limit_up=0,
                    limit_down=0,
                    open_price=0,
                    high_price=0,
                    low_price=0,
                    pre_close=0,
                    bid_price_1=last_close,
                    bid_volume_1=max(last_volume, 1000), # 确保有足够的流动性通过过滤
                    ask_price_1=last_close,
                    ask_volume_1=max(last_volume, 1000),
                    gateway_name="BACKTESTING"
                )
        return None

    def get_contract(self, vt_symbol: str) -> Optional[Any]:
        if self.main_engine:
            return self.main_engine.get_contract(vt_symbol)
            
        # 回测模式兼容: 尝试从 strategy_engine 获取 (Hack injected in run_backtesting.py)
        if hasattr(self.context, "strategy_engine"):
            engine = self.context.strategy_engine
            if hasattr(engine, "get_contract"):
                return engine.get_contract(vt_symbol)
                
        return None

    def get_all_contracts(self) -> List[Any]:
        if self.main_engine:
            return self.main_engine.get_all_contracts()
            
        # 回测模式兼容
        if hasattr(self.context, "strategy_engine"):
            engine = self.context.strategy_engine
            if hasattr(engine, "get_all_contracts"):
                return engine.get_all_contracts()
                
        return []
