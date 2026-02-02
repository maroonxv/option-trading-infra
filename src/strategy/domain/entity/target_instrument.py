"""
TargetInstrument 实体 - 标的合约

管理单个标的的 K 线数据和指标状态快照。
作为只读数据容器，不包含计算逻辑。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

import pandas as pd

from ..value_object.macd_value import MACDValue
from ..value_object.td_value import TDValue
from ..value_object.ema_state import EMAState
from ..value_object.dullness_state import DullnessState
from ..value_object.divergence_state import DivergenceState


@dataclass
class TargetInstrument:
    """
    标的合约实体
    
    职责:
    1. 数据仓库: bars DataFrame 存储完整的历史 K 线及指标序列
    2. 状态快照: 存储当前时刻的指标状态 (Value Objects)
    3. 一致性: 保证所有状态在同一时间点对齐
    
    Attributes:
        vt_symbol: VnPy 格式的合约代码 (如 "rb2501.SHFE")
        bars: K 线数据 DataFrame (包含 open, high, low, close 等列)
        macd_value: 当前 MACD 指标快照
        td_value: 当前 TD 序列快照
        ema_state: 当前 EMA 均线状态
        dullness_state: 当前钝化状态
        divergence_state: 当前背离状态
        last_update_time: 最后更新时间
    """
    vt_symbol: str
    bars: pd.DataFrame = field(default_factory=pd.DataFrame)
    macd_value: Optional[MACDValue] = None
    td_value: Optional[TDValue] = None
    ema_state: Optional[EMAState] = None
    dullness_state: DullnessState = field(default_factory=DullnessState)
    divergence_state: DivergenceState = field(default_factory=DivergenceState)
    macd_history: List[MACDValue] = field(default_factory=list)
    last_update_time: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """初始化后处理"""
        if self.bars.empty:
            # 初始化空 DataFrame 结构
            self.bars = pd.DataFrame(columns=[
                "datetime", "open", "high", "low", "close", "volume",
                "dif", "dea", "macd",
                "td_count", "td_setup",
                "ema_fast", "ema_slow"
            ])
    
    def append_bar(self, bar_data: dict) -> None:
        """
        追加新的 K 线数据
        
        Args:
            bar_data: 包含 datetime, open, high, low, close, volume 的字典
        """
        new_row = pd.DataFrame([bar_data])
        if self.bars.empty:
            existing_cols = list(self.bars.columns)
            new_cols = [c for c in new_row.columns if c not in existing_cols]
            self.bars = new_row.reindex(columns=existing_cols + new_cols)
        else:
            self.bars = pd.concat([self.bars, new_row], ignore_index=True)
        self.last_update_time = bar_data.get("datetime", datetime.now())
    
    def update_indicators(
        self,
        macd_value: MACDValue,
        td_value: TDValue,
        ema_state: EMAState,
        dullness_state: DullnessState,
        divergence_state: DivergenceState
    ) -> None:
        """
        全量更新指标状态 (原子操作)
        
        由应用层在调用领域服务计算完指标后调用此方法更新状态。
        
        Args:
            macd_value: 新的 MACD 指标值
            td_value: 新的 TD 序列值
            ema_state: 新的 EMA 状态
            dullness_state: 新的钝化状态
            divergence_state: 新的背离状态
        """
        self.macd_value = macd_value
        if macd_value:
            self.macd_history.append(macd_value)
            # 限制长度，保留最近 500 个数据
            if len(self.macd_history) > 500:
                self.macd_history = self.macd_history[-500:]
        self.td_value = td_value
        self.ema_state = ema_state
        self.dullness_state = dullness_state
        self.divergence_state = divergence_state
    
    def update_bar_indicators(
        self,
        dif: float,
        dea: float,
        macd: float,
        td_count: int,
        td_setup: int,
        ema_fast: float,
        ema_slow: float
    ) -> None:
        """
        更新最新 K 线的指标列数据
        
        Args:
            dif: MACD DIF 值
            dea: MACD DEA 值
            macd: MACD 柱状图值
            td_count: TD 计数
            td_setup: TD Setup 计数
            ema_fast: 快速 EMA 值
            ema_slow: 慢速 EMA 值
        """
        if self.bars.empty:
            return
        
        idx = self.bars.index[-1]
        self.bars.loc[idx, "dif"] = dif
        self.bars.loc[idx, "dea"] = dea
        self.bars.loc[idx, "macd"] = macd
        self.bars.loc[idx, "td_count"] = td_count
        self.bars.loc[idx, "td_setup"] = td_setup
        self.bars.loc[idx, "ema_fast"] = ema_fast
        self.bars.loc[idx, "ema_slow"] = ema_slow
    
    def get_latest_bar(self) -> Optional[pd.Series]:
        """获取最新的 K 线数据"""
        if self.bars.empty:
            return None
        return self.bars.iloc[-1]
    
    def get_bar_history(self, n: int = 50) -> pd.DataFrame:
        """
        获取最近 n 根 K 线历史
        
        Args:
            n: 获取的 K 线数量
            
        Returns:
            最近 n 根 K 线的 DataFrame
        """
        return self.bars.tail(n).copy()
    
    @property
    def has_enough_data(self) -> bool:
        """判断是否有足够的数据进行指标计算 (至少 30 根 K 线)"""
        return len(self.bars) >= 30
    
    @property
    def latest_close(self) -> float:
        """获取最新收盘价"""
        if self.bars.empty:
            return 0.0
        return float(self.bars["close"].iloc[-1])
    
    @property
    def latest_high(self) -> float:
        """获取最新最高价"""
        if self.bars.empty:
            return 0.0
        return float(self.bars["high"].iloc[-1])
    
    @property
    def latest_low(self) -> float:
        """获取最新最低价"""
        if self.bars.empty:
            return 0.0
        return float(self.bars["low"].iloc[-1])
    
    def __repr__(self) -> str:
        return (
            f"TargetInstrument({self.vt_symbol}, "
            f"bars={len(self.bars)}, "
            f"last_update={self.last_update_time})"
        )
