"""
MacdCalculatorService - MACD 计算服务

负责 MACD 相关的纯数学计算。
无状态服务，使用静态方法。
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd
import numpy as np

from ...value_object.macd_value import MACDValue


@dataclass
class MACDPeakInfo:
    """MACD 峰值信息"""
    index: int          # 峰值所在的索引
    datetime: object    # 峰值时间
    price: float        # 峰值时的价格
    dif: float          # 峰值时的 DIF 值
    is_top: bool        # True=顶峰, False=底峰


class MacdCalculatorService:
    """
    MACD 计算服务 (无状态, 纯静态方法)
    
    职责:
    - 计算 MACD 指标 (DIF, DEA, MACD柱)
    - 检测 MACD 峰值
    """
    
    # 默认参数
    DEFAULT_FAST_PERIOD = 12
    DEFAULT_SLOW_PERIOD = 26
    DEFAULT_SIGNAL_PERIOD = 9
    
    @staticmethod
    def compute(
        bars: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> pd.DataFrame:
        """
        计算并向 DataFrame 追加/更新 dif, dea, macd 列
        
        Args:
            bars: K 线数据 DataFrame (必须包含 'close' 列)
            fast_period: 快速 EMA 周期 (默认 12)
            slow_period: 慢速 EMA 周期 (默认 26)
            signal_period: 信号线 EMA 周期 (默认 9)
            
        Returns:
            更新后的 DataFrame (包含 dif, dea, macd 列)
        """
        if bars.empty or "close" not in bars.columns:
            return bars
        
        df = bars.copy()
        close = df["close"]
        
        # 计算快慢 EMA
        ema_fast = close.ewm(span=fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=slow_period, adjust=False).mean()
        
        # 计算 DIF (快线)
        dif = ema_fast - ema_slow
        
        # 计算 DEA (慢线 / 信号线)
        dea = dif.ewm(span=signal_period, adjust=False).mean()
        
        # 计算 MACD 柱状图 (2 倍差值)
        macd = 2 * (dif - dea)
        
        df["dif"] = dif
        df["dea"] = dea
        df["macd"] = macd
        
        return df
    
    @staticmethod
    def get_latest_value(bars: pd.DataFrame) -> Optional[MACDValue]:
        """
        获取最新的 MACD 值对象
        
        Args:
            bars: 包含 MACD 指标的 DataFrame
            
        Returns:
            MACDValue 对象，如果数据不足则返回 None
        """
        required_cols = ["dif", "dea", "macd"]
        if bars.empty or not all(col in bars.columns for col in required_cols):
            return None
        
        latest = bars.iloc[-1]
        
        dif = latest["dif"]
        dea = latest["dea"]
        macd = latest["macd"]
        
        # 检查是否有 NaN
        if pd.isna(dif) or pd.isna(dea) or pd.isna(macd):
            return None
        
        return MACDValue(
            dif=float(dif),
            dea=float(dea),
            macd_bar=float(macd)
        )
    
    @staticmethod
    def detect_peaks(
        bars: pd.DataFrame,
        lookback: int = 5
    ) -> List[MACDPeakInfo]:
        """
        检测红绿柱峰值
        
        峰值定义:
        - 顶峰: MACD 柱为正，且当前值大于前后各 lookback 根 K 线
        - 底峰: MACD 柱为负，且当前值小于前后各 lookback 根 K 线
        
        Args:
            bars: 包含 MACD 指标的 DataFrame
            lookback: 峰值检测的回看周期
            
        Returns:
            峰值信息列表
        """
        if bars.empty or "macd" not in bars.columns:
            return []
        
        peaks: List[MACDPeakInfo] = []
        macd_values = bars["macd"].values
        n = len(macd_values)
        
        for i in range(lookback, n - lookback):
            current = macd_values[i]
            
            if pd.isna(current):
                continue
            
            # 检查顶峰 (红柱峰值)
            if current > 0:
                is_peak = all(
                    current >= macd_values[j]
                    for j in range(i - lookback, i + lookback + 1)
                    if j != i and not pd.isna(macd_values[j])
                )
                if is_peak:
                    peaks.append(MACDPeakInfo(
                        index=i,
                        datetime=bars.iloc[i].get("datetime"),
                        price=float(bars.iloc[i].get("close", 0)),
                        dif=float(bars.iloc[i].get("dif", 0)),
                        is_top=True
                    ))
            
            # 检查底峰 (绿柱峰值)
            elif current < 0:
                is_valley = all(
                    current <= macd_values[j]
                    for j in range(i - lookback, i + lookback + 1)
                    if j != i and not pd.isna(macd_values[j])
                )
                if is_valley:
                    peaks.append(MACDPeakInfo(
                        index=i,
                        datetime=bars.iloc[i].get("datetime"),
                        price=float(bars.iloc[i].get("close", 0)),
                        dif=float(bars.iloc[i].get("dif", 0)),
                        is_top=False
                    ))
        
        return peaks
    
    @staticmethod
    def check_cross(bars: pd.DataFrame) -> Tuple[bool, bool]:
        """
        检查 MACD 金叉/死叉
        
        Args:
            bars: 包含 MACD 指标的 DataFrame
            
        Returns:
            (is_golden_cross, is_death_cross) 元组
        """
        if len(bars) < 2 or "dif" not in bars.columns or "dea" not in bars.columns:
            return False, False
        
        prev = bars.iloc[-2]
        curr = bars.iloc[-1]
        
        prev_dif, prev_dea = prev["dif"], prev["dea"]
        curr_dif, curr_dea = curr["dif"], curr["dea"]
        
        if any(pd.isna(x) for x in [prev_dif, prev_dea, curr_dif, curr_dea]):
            return False, False
        
        # 金叉: 前一根 DIF <= DEA, 当前 DIF > DEA
        is_golden = prev_dif <= prev_dea and curr_dif > curr_dea
        
        # 死叉: 前一根 DIF >= DEA, 当前 DIF < DEA
        is_death = prev_dif >= prev_dea and curr_dif < curr_dea
        
        return is_golden, is_death
