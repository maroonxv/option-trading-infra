"""
TargetInstrument 实体 - 标的合约

贫血模型实体，仅作为数据容器使用。
所有业务逻辑由服务层处理。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

import pandas as pd


@dataclass
class TargetInstrument:
    """
    标的合约实体（贫血模型）
    
    职责:
    1. 数据容器: 存储合约基础信息
    2. K 线队列: 维护历史 K 线数据
    3. 指标容器: 提供动态指标存储（indicators 字典）
    
    设计理念:
    - 不包含任何计算逻辑
    - indicators 字典由 IIndicatorService 负责填充
    - 保持实体稳定，新增指标无需修改实体结构
    
    Attributes:
        vt_symbol: VnPy 格式的合约代码 (如 "rb2501.SHFE")
        bars: K 线数据 DataFrame (包含 open, high, low, close, volume 等列)
        indicators: 动态指标容器，存储任意类型的指标数据
        last_update_time: 最后更新时间
    """
    vt_symbol: str
    bars: pd.DataFrame = field(default_factory=pd.DataFrame)
    indicators: Dict[str, Any] = field(default_factory=dict)
    last_update_time: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """初始化后处理 - 创建基础 K 线结构"""
        if self.bars.empty:
            # 初始化空 DataFrame，仅包含基础 OHLCV 列
            self.bars = pd.DataFrame(columns=[
                "datetime", "open", "high", "low", "close", "volume"
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
