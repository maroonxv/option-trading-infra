"""
IndicatorService - 计算 MACD，TD，EMA，背离，钝化
"""
from datetime import datetime
from typing import Optional, Callable, List

import pandas as pd

from .calculation_service.macd_calculation_service import MacdCalculatorService
from .calculation_service.td_calculation_service import TdCalculatorService
from .calculation_service.ema_calculation_service import EmaCalculatorService
from ..value_object.indicator_states import IndicatorResultDTO
from ..value_object.macd_value import MACDValue
from ..value_object.td_value import TDValue
from ..value_object.ema_state import EMAState
from ..value_object.dullness_state import DullnessState
from ..value_object.divergence_state import DivergenceState
from ..entity.target_instrument import TargetInstrument


class IndicatorService:
    """
    指标服务
    
    职责:
    - 协调各项指标计算 (MACD, TD, EMA)
    - 提供统一计算接口
    """
    
    def __init__(
        self,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        ema_fast: int = 5,
        ema_slow: int = 20
    ):
        """
        初始化指标服务
        
        Args:
            macd_fast: MACD 快速周期
            macd_slow: MACD 慢速周期
            macd_signal: MACD 信号线周期
            ema_fast: EMA 快速周期
            ema_slow: EMA 慢速周期
        """
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
    
    def calculate_all(
        self,
        instrument: TargetInstrument,
        prev_dullness: Optional[DullnessState] = None,
        prev_divergence: Optional[DivergenceState] = None,
        log_func: Optional[Callable] = None
    ) -> IndicatorResultDTO:
        """
        计算所有指标
        
        流程:
        1. 计算 MACD
        2. 计算 TD 序列
        3. 计算 EMA
        4. 计算钝化状态 (依赖 MACD)
        5. 计算背离状态 (依赖 MACD + 钝化)
        6. 封装为 IndicatorResultDTO 返回
        
        Args:
            instrument: 标的实体
            prev_dullness: 前一个钝化状态
            prev_divergence: 前一个背离状态
            log_func: 日志回调函数
            
        Returns:
            IndicatorResultDTO 包含所有指标计算结果
        """
        bars = instrument.bars
        
        if bars.empty or len(bars) < 30:
            return IndicatorResultDTO()
        
        # 1. 计算 MACD
        bars_with_macd = MacdCalculatorService.compute(
            bars,
            fast_period=self.macd_fast,
            slow_period=self.macd_slow,
            signal_period=self.macd_signal
        )
        macd_value = MacdCalculatorService.get_latest_value(bars_with_macd)
        
        # 2. 计算 TD 序列
        bars_with_td = TdCalculatorService.compute(bars_with_macd)
        td_value = TdCalculatorService.get_latest_value(bars_with_td)
        
        # 3. 计算 EMA
        bars_with_ema = EmaCalculatorService.compute(
            bars_with_td,
            period_fast=self.ema_fast,
            period_slow=self.ema_slow
        )
        ema_state = EmaCalculatorService.get_latest_state(bars_with_ema)
        
        # 4. 更新 instrument 的 bars (包含所有指标列)
        instrument.bars = bars_with_ema
        
        # 5. 计算钝化状态
        # 如果没有提供前值，尝试从 instrument 获取，或者是初始状态
        current_dullness_prev = prev_dullness or instrument.dullness_state or DullnessState()
        new_dullness = self.check_dullness(
            bars=bars_with_ema,
            prev_state=current_dullness_prev,
            log_func=log_func
        )
        
        # 6. 计算背离状态
        current_divergence_prev = prev_divergence or instrument.divergence_state or DivergenceState()
        new_divergence = self.check_divergence(
            bars=bars_with_ema,
            dullness_state=new_dullness,
            prev_state=current_divergence_prev,
            log_func=log_func
        )
        
        # 7. 记录调试日志
        if log_func:
            latest = bars_with_ema.iloc[-1]
            close = latest.get("close", 0)
            
            # 格式化 TD flags
            buy_flag = "B8/9" if td_value.has_buy_8_9 else ""
            sell_flag = "S8/9" if td_value.has_sell_8_9 else ""
            flags = " ".join(filter(None, [buy_flag, sell_flag])) or "None"

            log_func(f"[DEBUG-IND] {instrument.vt_symbol} | 收盘价: {close}")
            log_func(f"[DEBUG-IND] {instrument.vt_symbol} MACD | 差离值: {macd_value.dif:.3f}, 讯号线: {macd_value.dea:.3f}, MACD柱: {macd_value.macd_bar:.3f}")
            log_func(f"[DEBUG-IND] {instrument.vt_symbol} TD   | 计数: {td_value.td_count}, 结构: {td_value.td_setup}, 标记: {flags}")
            log_func(f"[DEBUG-IND] {instrument.vt_symbol} EMA  | 快线: {ema_state.fast_ema:.3f}, 慢线: {ema_state.slow_ema:.3f}")
            
            # 记录状态变化
            if new_dullness.is_top_active != current_dullness_prev.is_top_active:
                log_func(f"[DEBUG-IND] {instrument.vt_symbol} 顶钝化状态变更: {current_dullness_prev.is_top_active} -> {new_dullness.is_top_active}")
            if new_dullness.is_bottom_active != current_dullness_prev.is_bottom_active:
                log_func(f"[DEBUG-IND] {instrument.vt_symbol} 底钝化状态变更: {current_dullness_prev.is_bottom_active} -> {new_dullness.is_bottom_active}")
        
        # 8. 返回结果
        return IndicatorResultDTO(
            macd_value=macd_value,
            td_value=td_value,
            ema_state=ema_state,
            dullness_state=new_dullness,
            divergence_state=new_divergence
        )
    
    @staticmethod
    def check_dullness(
        bars: pd.DataFrame,
        prev_state: DullnessState,
        log_func: Optional[Callable] = None
    ) -> DullnessState:
        """
        检查钝化状态
        
        钝化定义:
        - 顶钝化: MACD 在零轴上方，红柱持续缩小
        - 底钝化: MACD 在零轴下方，绿柱持续缩小
        
        Args:
            bars: K 线数据 (必须包含 dif, dea, macd 列)
            prev_state: 前一个钝化状态
            log_func: 日志回调函数
            
        Returns:
            更新后的钝化状态
        """
        if len(bars) < 3:
            return prev_state
        
        # 获取最后 3 行数据
        rows = bars.tail(3)
        
        # 构造 MACDValue 对象以便复用逻辑
        def to_macd_val(idx):
            row = rows.iloc[idx]
            return MACDValue(
                dif=float(row.get("dif", 0)),
                dea=float(row.get("dea", 0)),
                macd_bar=float(row.get("macd", 0))
            )
            
        current = to_macd_val(-1)
        prev1 = to_macd_val(-2)
        prev2 = to_macd_val(-3)
        
        latest_bar = rows.iloc[-1]
        current_time = latest_bar.get("datetime", datetime.now())
        current_price = float(latest_bar.get("close", 0))
        vt_symbol = getattr(latest_bar, "vt_symbol", "")
        
        # 检查顶钝化
        if current.is_above_zero:
            # 红柱持续缩小
            if current.macd_bar < prev1.macd_bar < prev2.macd_bar:
                if not prev_state.is_top_active:
                    if log_func:
                        log_func(f"[DEBUG-SIG] {vt_symbol} 顶钝化形成 | 价格: {current_price}, 差离值: {current.dif:.3f}")
                    return prev_state.with_top_active(
                        start_time=current_time,
                        start_price=current_price,
                        start_diff=current.dif
                    )
            # 红柱开始放大，钝化失效
            elif prev_state.is_top_active and current.macd_bar > prev1.macd_bar:
                if log_func:
                    log_func(f"[DEBUG-SIG] {vt_symbol} 顶钝化消失 (红柱放大) | 柱值: {prev1.macd_bar:.3f} -> {current.macd_bar:.3f}")
                return prev_state.with_top_invalidated()
        
        # 检查底钝化
        elif current.is_below_zero:
            # 绿柱持续缩小 (绝对值变小，即 macd 值变大)
            if current.macd_bar > prev1.macd_bar > prev2.macd_bar:
                if not prev_state.is_bottom_active:
                    if log_func:
                        log_func(f"[DEBUG-SIG] {vt_symbol} 底钝化形成 | 价格: {current_price}, 差离值: {current.dif:.3f}")
                    return prev_state.with_bottom_active(
                        start_time=current_time,
                        start_price=current_price,
                        start_diff=current.dif
                    )
            # 绿柱开始放大，钝化失效
            elif prev_state.is_bottom_active and current.macd_bar < prev1.macd_bar:
                if log_func:
                    log_func(f"[DEBUG-SIG] {vt_symbol} 底钝化消失 (绿柱放大) | 柱值: {prev1.macd_bar:.3f} -> {current.macd_bar:.3f}")
                return prev_state.with_bottom_invalidated()
        
        # DIF 穿越零轴，重置钝化状态
        if prev_state.is_active:
            if (prev1.is_above_zero and current.is_below_zero) or \
               (prev1.is_below_zero and current.is_above_zero):
                if log_func:
                    log_func(f"[DEBUG-SIG] {vt_symbol} 钝化重置 (穿越零轴)")
                return prev_state.reset()
        
        return prev_state
    
    @staticmethod
    def check_divergence(
        bars: pd.DataFrame,
        dullness_state: DullnessState,
        prev_state: DivergenceState,
        log_func: Optional[Callable] = None
    ) -> DivergenceState:
        """
        检查背离状态
        
        背离定义:
        - 顶背离: 价格创新高，但 MACD (DIF) 未创新高
        - 底背离: 价格创新低，但 MACD (DIF) 未创新低
        
        Args:
            bars: K 线数据
            dullness_state: 当前钝化状态
            prev_state: 前一个背离状态
            log_func: 日志回调函数
            
        Returns:
            更新后的背离状态
        """
        if len(bars) < 20:
            return prev_state
        
        # 检测 MACD 峰值
        peaks = MacdCalculatorService.detect_peaks(bars)
        
        if len(peaks) < 2:
            return prev_state
        
        latest_bar = bars.iloc[-1]
        current_time = latest_bar.get("datetime", datetime.now())
        current_price = float(latest_bar.get("close", 0))
        current_dif = float(latest_bar.get("dif", 0))
        vt_symbol = getattr(latest_bar, "vt_symbol", "")
        
        # 获取最近两个同向峰值
        top_peaks = [p for p in peaks if p.is_top]
        bottom_peaks = [p for p in peaks if not p.is_top]
        
        # 检查顶背离 (需要顶钝化激活状态)
        if len(top_peaks) >= 2 and dullness_state.is_top_active:
            recent_top = top_peaks[-1]
            prev_top = top_peaks[-2]
            
            # 价格创新高，但 DIF 未创新高
            if recent_top.price > prev_top.price and recent_top.dif < prev_top.dif:
                if log_func:
                    log_func(f"[DEBUG-SIG] {vt_symbol} 顶背离确认 | 价格: {prev_top.price}->{recent_top.price}, 差离值: {prev_top.dif:.3f}->{recent_top.dif:.3f}")
                return prev_state.with_top_confirmed(
                    confirm_time=current_time,
                    confirm_price=current_price,
                    confirm_diff=current_dif
                )
        
        # 检查底背离 (需要底钝化激活状态)
        if len(bottom_peaks) >= 2 and dullness_state.is_bottom_active:
            recent_bottom = bottom_peaks[-1]
            prev_bottom = bottom_peaks[-2]
            
            # 价格创新低，但 DIF 未创新低 (DIF 更高)
            if recent_bottom.price < prev_bottom.price and recent_bottom.dif > prev_bottom.dif:
                if log_func:
                    log_func(f"[DEBUG-SIG] {vt_symbol} 底背离确认 | 价格: {prev_bottom.price}->{recent_bottom.price}, 差离值: {prev_bottom.dif:.3f}->{recent_bottom.dif:.3f}")
                return prev_state.with_bottom_confirmed(
                    confirm_time=current_time,
                    confirm_price=current_price,
                    confirm_diff=current_dif
                )
        
        return prev_state
    
    def calculate_macd(
        self,
        bars: pd.DataFrame
    ) -> Optional[MACDValue]:
        """
        单独计算 MACD
        
        Args:
            bars: K 线数据
            
        Returns:
            MACDValue 对象
        """
        if bars.empty:
            return None
        
        bars_with_macd = MacdCalculatorService.compute(
            bars,
            fast_period=self.macd_fast,
            slow_period=self.macd_slow,
            signal_period=self.macd_signal
        )
        return MacdCalculatorService.get_latest_value(bars_with_macd)
    
    def calculate_td(
        self,
        bars: pd.DataFrame
    ) -> Optional[TDValue]:
        """
        单独计算 TD 序列
        
        Args:
            bars: K 线数据
            
        Returns:
            TDValue 对象
        """
        if bars.empty:
            return None
        
        bars_with_td = TdCalculatorService.compute(bars)
        return TdCalculatorService.get_latest_value(bars_with_td)
    
    def calculate_ema(
        self,
        bars: pd.DataFrame
    ) -> Optional[EMAState]:
        """
        单独计算 EMA
        
        Args:
            bars: K 线数据
            
        Returns:
            EMAState 对象
        """
        if bars.empty:
            return None
        
        bars_with_ema = EmaCalculatorService.compute(
            bars,
            period_fast=self.ema_fast,
            period_slow=self.ema_slow
        )
        return EmaCalculatorService.get_latest_state(bars_with_ema)
