"""
TargetInstrumentAggregate - 标的聚合根

管理多个 TargetInstrument 实体，维护行情数据和指标状态。
只读聚合根，不产生领域事件。
"""
from datetime import datetime
from typing import Dict, Optional, List, Any

import pandas as pd

from ..entity.target_instrument import TargetInstrument
from ..value_object.macd_value import MACDValue
from ..value_object.td_value import TDValue
from ..value_object.ema_state import EMAState
from ..value_object.dullness_state import DullnessState
from ..value_object.divergence_state import DivergenceState


class TargetInstrumentAggregate:
    """
    标的聚合根 (只读, 行情状态)
    
    职责:
    1. 管理 instruments 字典 (多标的支持)
    2. 追加 K 线数据到 DataFrame
    3. 存储指标计算结果
    4. 提供查询接口
    
    设计原则:
    - 纯数据容器，无计算逻辑
    - 计算逻辑委托给 IndicatorService 和 SignalService
    - 由应用层 (VolatilityTrade) 调用领域服务并更新聚合根
    """
    
    def __init__(self) -> None:
        """初始化聚合根"""
        self._instruments: Dict[str, TargetInstrument] = {}
        self._active_contracts: Dict[str, str] = {}  # product -> vt_symbol

    # ========== 持久化接口 ==========

    def to_snapshot(self) -> Dict[str, Any]:
        """生成状态快照"""
        return {
            "instruments": self._instruments,
            "active_contracts": self._active_contracts
        }

    @classmethod
    def from_snapshot(cls, snapshot: Dict[str, Any]) -> "TargetInstrumentAggregate":
        """从快照恢复状态"""
        obj = cls()
        obj._instruments = snapshot.get("instruments", {})
        obj._active_contracts = snapshot.get("active_contracts", {})
        return obj

    def set_active_contract(self, product: str, vt_symbol: str) -> None:
        """设置品种当前活跃的合约"""
        self._active_contracts[product] = vt_symbol

    def get_active_contract(self, product: str) -> Optional[str]:
        """获取品种当前活跃的合约"""
        return self._active_contracts.get(product)

    def get_all_active_contracts(self) -> List[str]:
        """获取所有品种当前活跃的合约列表"""
        return list(self._active_contracts.values())

    def get_instrument(self, vt_symbol: str) -> Optional[TargetInstrument]:
        """
        获取指定标的
        
        Args:
            vt_symbol: 合约代码
            
        Returns:
            TargetInstrument 实体，不存在则返回 None
        """
        return self._instruments.get(vt_symbol)
    
    def get_or_create_instrument(self, vt_symbol: str) -> TargetInstrument:
        """
        获取或创建标的
        
        Args:
            vt_symbol: 合约代码
            
        Returns:
            TargetInstrument 实体
        """
        if vt_symbol not in self._instruments:
            self._instruments[vt_symbol] = TargetInstrument(vt_symbol=vt_symbol)
        return self._instruments[vt_symbol]
    
    def update_bar(self, vt_symbol: str, bar_data: dict) -> TargetInstrument:
        """
        更新 K 线数据
        
        由接口层的 on_bars 回调经应用层调用。
        
        Args:
            vt_symbol: 合约代码
            bar_data: K 线数据字典 (包含 datetime, open, high, low, close, volume)
            
        Returns:
            更新后的 TargetInstrument 实体
        """
        instrument = self.get_or_create_instrument(vt_symbol)
        instrument.append_bar(bar_data)
        return instrument
    
    def update_indicators(
        self,
        vt_symbol: str,
        macd_value: MACDValue,
        td_value: TDValue,
        ema_state: EMAState,
        dullness_state: DullnessState,
        divergence_state: DivergenceState
    ) -> None:
        """
        更新指标状态
        
        由应用层在调用领域服务计算完指标后调用。
        
        Args:
            vt_symbol: 合约代码
            macd_value: MACD 指标值
            td_value: TD 序列值
            ema_state: EMA 状态
            dullness_state: 钝化状态
            divergence_state: 背离状态
        """
        instrument = self.get_instrument(vt_symbol)
        if instrument is None:
            return
        
        instrument.update_indicators(
            macd_value=macd_value,
            td_value=td_value,
            ema_state=ema_state,
            dullness_state=dullness_state,
            divergence_state=divergence_state
        )
    
    def get_bar_history(
        self,
        vt_symbol: str,
        n: int = 50
    ) -> pd.DataFrame:
        """
        获取 K 线历史
        
        Args:
            vt_symbol: 合约代码
            n: 获取的 K 线数量
            
        Returns:
            K 线 DataFrame
        """
        instrument = self.get_instrument(vt_symbol)
        if instrument is None:
            return pd.DataFrame()
        return instrument.get_bar_history(n)
    
    def get_latest_price(self, vt_symbol: str) -> float:
        """
        获取最新价格
        
        Args:
            vt_symbol: 合约代码
            
        Returns:
            最新收盘价，不存在则返回 0
        """
        instrument = self.get_instrument(vt_symbol)
        if instrument is None:
            return 0.0
        return instrument.latest_close
    
    def get_all_symbols(self) -> List[str]:
        """
        获取所有已添加的标的代码
        
        Returns:
            标的代码列表
        """
        return list(self._instruments.keys())
    
    def has_instrument(self, vt_symbol: str) -> bool:
        """
        检查是否存在指定标的
        
        Args:
            vt_symbol: 合约代码
            
        Returns:
            True 如果存在
        """
        return vt_symbol in self._instruments
    
    def has_enough_data(self, vt_symbol: str) -> bool:
        """
        检查指定标的是否有足够的数据进行指标计算
        
        Args:
            vt_symbol: 合约代码
            
        Returns:
            True 如果数据量足够
        """
        instrument = self.get_instrument(vt_symbol)
        if instrument is None:
            return False
        return instrument.has_enough_data
    
    def clear(self) -> None:
        """清空所有标的数据"""
        self._instruments.clear()
    
    def __repr__(self) -> str:
        symbols = ", ".join(self._instruments.keys())
        return f"TargetInstrumentAggregate([{symbols}])"
