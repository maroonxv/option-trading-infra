"""
TdCalculatorService - TD 序列计算服务

负责 TD (Tom DeMark) 序列相关的纯数学计算。
无状态服务，使用静态方法。
"""
from typing import Optional

import pandas as pd
import numpy as np

from ...value_object.td_value import TDValue


class TdCalculatorService:
    """
    TD 序列计算服务 (无状态, 纯静态方法)
    
    职责:
    - 计算 TD 序列 (Setup 阶段)
    - 判断买入/卖出 8/9 信号
    
    TD 序列规则:
    - 买入 Setup: 连续 9 根收盘价低于 4 根前的收盘价
    - 卖出 Setup: 连续 9 根收盘价高于 4 根前的收盘价
    """
    
    # TD 比较的回看周期
    LOOKBACK = 4
    
    @staticmethod
    def compute(bars: pd.DataFrame) -> pd.DataFrame:
        """
        计算并向 DataFrame 追加/更新 td_count, td_setup 列
        
        td_count: 正数表示买入计数 (价格下跌), 负数表示卖出计数 (价格上涨)
        td_setup: Setup 阶段完成计数 (达到 9 时触发信号)
        
        Args:
            bars: K 线数据 DataFrame (必须包含 'close' 列)
            
        Returns:
            更新后的 DataFrame
        """
        if bars.empty or "close" not in bars.columns:
            return bars
        
        df = bars.copy()
        n = len(df)
        
        td_count = np.zeros(n, dtype=int)
        td_setup = np.zeros(n, dtype=int)
        
        close = df["close"].values
        
        for i in range(TdCalculatorService.LOOKBACK, n):
            compare_price = close[i - TdCalculatorService.LOOKBACK]
            current_price = close[i]
            prev_count = td_count[i - 1]
            
            # 买入 Setup: 收盘价 < 4 根前收盘价
            if current_price < compare_price:
                if prev_count > 0:
                    # 继续买入计数
                    td_count[i] = prev_count + 1
                else:
                    # 开始新的买入计数
                    td_count[i] = 1
            
            # 卖出 Setup: 收盘价 > 4 根前收盘价
            elif current_price > compare_price:
                if prev_count < 0:
                    # 继续卖出计数
                    td_count[i] = prev_count - 1
                else:
                    # 开始新的卖出计数
                    td_count[i] = -1
            
            # 等于时计数中断
            else:
                td_count[i] = 0
            
            # Setup 完成检测 (达到 9 或 -9)
            if td_count[i] >= 9:
                td_setup[i] = 9
            elif td_count[i] <= -9:
                td_setup[i] = -9
            else:
                td_setup[i] = 0
        
        df["td_count"] = td_count
        df["td_setup"] = td_setup
        
        return df
    
    @staticmethod
    def get_latest_value(bars: pd.DataFrame) -> Optional[TDValue]:
        """
        获取最新的 TD 值对象
        
        Args:
            bars: 包含 TD 指标的 DataFrame
            
        Returns:
            TDValue 对象，如果数据不足则返回 None
        """
        required_cols = ["td_count", "td_setup"]
        if bars.empty or not all(col in bars.columns for col in required_cols):
            return None
        
        # 检查最近的 8/9 信号
        has_buy_8_9, has_sell_8_9 = TdCalculatorService.check_8_9_signal(bars)
        
        latest = bars.iloc[-1]
        td_count = int(latest["td_count"])
        td_setup = int(latest["td_setup"])
        
        return TDValue(
            td_count=td_count,
            td_setup=td_setup,
            has_buy_8_9=has_buy_8_9,
            has_sell_8_9=has_sell_8_9
        )
    
    @staticmethod
    def check_8_9_signal(
        bars: pd.DataFrame,
        lookback: int = 3
    ) -> tuple[bool, bool]:
        """
        检查最近是否出现 8/9 信号
        
        8/9 信号定义:
        - 买入 8/9: 最近 lookback 根 K 线内 td_count 为 8 或 9
        - 卖出 8/9: 最近 lookback 根 K 线内 td_count 为 -8 或 -9
        
        Args:
            bars: 包含 TD 指标的 DataFrame
            lookback: 回看的 K 线数量
            
        Returns:
            (has_buy_8_9, has_sell_8_9) 元组
        """
        if bars.empty or "td_count" not in bars.columns:
            return False, False
        
        recent = bars.tail(lookback)
        td_counts = recent["td_count"].values
        
        has_buy_8_9 = any(c in [8, 9] for c in td_counts if not pd.isna(c))
        has_sell_8_9 = any(c in [-8, -9] for c in td_counts if not pd.isna(c))
        
        return has_buy_8_9, has_sell_8_9
    
    @staticmethod
    def find_setup_bars(bars: pd.DataFrame) -> dict:
        """
        查找最近一次 Setup 完成的 K 线
        
        Args:
            bars: 包含 TD 指标的 DataFrame
            
        Returns:
            包含买入和卖出 Setup 信息的字典
        """
        result = {
            "buy_setup_idx": None,
            "buy_setup_time": None,
            "sell_setup_idx": None,
            "sell_setup_time": None,
        }
        
        if bars.empty or "td_setup" not in bars.columns:
            return result
        
        # 从后往前查找
        for i in range(len(bars) - 1, -1, -1):
            setup = bars.iloc[i]["td_setup"]
            
            if setup == 9 and result["buy_setup_idx"] is None:
                result["buy_setup_idx"] = i
                result["buy_setup_time"] = bars.iloc[i].get("datetime")
            
            elif setup == -9 and result["sell_setup_idx"] is None:
                result["sell_setup_idx"] = i
                result["sell_setup_time"] = bars.iloc[i].get("datetime")
            
            # 如果两个都找到了就退出
            if result["buy_setup_idx"] is not None and result["sell_setup_idx"] is not None:
                break
        
        return result
