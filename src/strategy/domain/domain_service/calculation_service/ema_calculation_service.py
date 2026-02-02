"""
EmaCalculatorService - EMA 均线计算服务

负责指数移动平均线 (EMA) 相关的纯数学计算。
无状态服务，使用静态方法。
"""
from typing import Optional, Literal

import pandas as pd
import numpy as np

from ...value_object.ema_state import EMAState, TrendStatus


class EmaCalculatorService:
    """
    EMA 计算服务 (无状态, 纯静态方法)
    
    职责:
    - 计算快慢 EMA 均线
    - 判断趋势状态
    """
    
    # 默认参数
    DEFAULT_FAST_PERIOD = 5
    DEFAULT_SLOW_PERIOD = 20
    
    @staticmethod
    def compute(
        bars: pd.DataFrame,
        period_fast: int = 5,
        period_slow: int = 20
    ) -> pd.DataFrame:
        """
        计算并向 DataFrame 追加/更新 ema_fast, ema_slow 列
        
        Args:
            bars: K 线数据 DataFrame (必须包含 'close' 列)
            period_fast: 快速 EMA 周期 (默认 5)
            period_slow: 慢速 EMA 周期 (默认 20)
            
        Returns:
            更新后的 DataFrame
        """
        if bars.empty or "close" not in bars.columns:
            return bars
        
        df = bars.copy()
        close = df["close"]
        
        # 计算 EMA
        df["ema_fast"] = close.ewm(span=period_fast, adjust=False).mean()
        df["ema_slow"] = close.ewm(span=period_slow, adjust=False).mean()
        
        return df
    
    @staticmethod
    def get_latest_state(
        bars: pd.DataFrame,
        trend_lookback: int = 5
    ) -> Optional[EMAState]:
        """
        获取最新的 EMA 状态对象
        
        Args:
            bars: 包含 EMA 指标的 DataFrame
            trend_lookback: 趋势判断的回看周期
            
        Returns:
            EMAState 对象，如果数据不足则返回 None
        """
        required_cols = ["ema_fast", "ema_slow"]
        if bars.empty or not all(col in bars.columns for col in required_cols):
            return None
        
        latest = bars.iloc[-1]
        fast_ema = latest["ema_fast"]
        slow_ema = latest["ema_slow"]
        
        if pd.isna(fast_ema) or pd.isna(slow_ema):
            return None
        
        # 判断趋势
        trend_status = EmaCalculatorService.determine_trend(bars, trend_lookback)
        
        return EMAState(
            fast_ema=float(fast_ema),
            slow_ema=float(slow_ema),
            trend_status=trend_status
        )
    
    @staticmethod
    def determine_trend(
        bars: pd.DataFrame,
        lookback: int = 5
    ) -> TrendStatus:
        """
        判断趋势状态
        
        趋势判断规则:
        - up: 快速 EMA 在慢速 EMA 上方，且快速 EMA 在上升
        - down: 快速 EMA 在慢速 EMA 下方，且快速 EMA 在下降
        - neutral: 其他情况
        
        Args:
            bars: 包含 EMA 指标的 DataFrame
            lookback: 趋势判断的回看周期
            
        Returns:
            趋势状态 ('up', 'down', 'neutral')
        """
        if len(bars) < lookback or "ema_fast" not in bars.columns:
            return "neutral"
        
        recent = bars.tail(lookback)
        fast_ema = recent["ema_fast"].values
        slow_ema = recent["ema_slow"].values
        
        # 检查是否有 NaN
        if any(pd.isna(x) for x in fast_ema) or any(pd.isna(x) for x in slow_ema):
            return "neutral"
        
        # 计算快速 EMA 的变化方向
        fast_direction = fast_ema[-1] - fast_ema[0]
        
        # 检查快慢均线关系
        is_fast_above_slow = all(f > s for f, s in zip(fast_ema, slow_ema))
        is_fast_below_slow = all(f < s for f, s in zip(fast_ema, slow_ema))
        
        if is_fast_above_slow and fast_direction > 0:
            return "up"
        elif is_fast_below_slow and fast_direction < 0:
            return "down"
        else:
            return "neutral"
    
    @staticmethod
    def check_cross(bars: pd.DataFrame) -> tuple[bool, bool]:
        """
        检查 EMA 金叉/死叉
        
        Args:
            bars: 包含 EMA 指标的 DataFrame
            
        Returns:
            (is_golden_cross, is_death_cross) 元组
        """
        required_cols = ["ema_fast", "ema_slow"]
        if len(bars) < 2 or not all(col in bars.columns for col in required_cols):
            return False, False
        
        prev = bars.iloc[-2]
        curr = bars.iloc[-1]
        
        prev_fast, prev_slow = prev["ema_fast"], prev["ema_slow"]
        curr_fast, curr_slow = curr["ema_fast"], curr["ema_slow"]
        
        if any(pd.isna(x) for x in [prev_fast, prev_slow, curr_fast, curr_slow]):
            return False, False
        
        # 金叉: 前一根 fast <= slow, 当前 fast > slow
        is_golden = prev_fast <= prev_slow and curr_fast > curr_slow
        
        # 死叉: 前一根 fast >= slow, 当前 fast < slow
        is_death = prev_fast >= prev_slow and curr_fast < curr_slow
        
        return is_golden, is_death
    
    @staticmethod
    def calculate_spread(bars: pd.DataFrame) -> Optional[float]:
        """
        计算最新的快慢均线差值百分比
        
        Args:
            bars: 包含 EMA 指标的 DataFrame
            
        Returns:
            差值百分比，如果数据不足则返回 None
        """
        required_cols = ["ema_fast", "ema_slow"]
        if bars.empty or not all(col in bars.columns for col in required_cols):
            return None
        
        latest = bars.iloc[-1]
        fast_ema = latest["ema_fast"]
        slow_ema = latest["ema_slow"]
        
        if pd.isna(fast_ema) or pd.isna(slow_ema) or slow_ema == 0:
            return None
        
        return (fast_ema - slow_ema) / slow_ema * 100
