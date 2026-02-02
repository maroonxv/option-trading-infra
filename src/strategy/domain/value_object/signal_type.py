"""
SignalType 值对象 - 信号类型枚举

定义开仓信号和平仓信号类型，以及信号间的匹配关系。
"""
from enum import Enum
from typing import Set


class SignalType(Enum):
    """
    信号类型枚举
    
    开仓信号:
    - SELL_PUT_*: 卖沽开仓 (看涨)
    - SELL_CALL_*: 卖购开仓 (看跌)
    
    平仓信号:
    - CLOSE_PUT_*: 卖沽平仓
    - CLOSE_CALL_*: 卖购平仓
    """
    
    # ========== 卖沽开仓信号 (看涨) ==========
    SELL_PUT_DIVERGENCE_TD9 = "sell_put_divergence_td9"       # 底钝化 + 低8/9
    SELL_PUT_DIVERGENCE_CONFIRM = "sell_put_divergence_confirm"  # 底背离确认
    
    # ========== 卖购开仓信号 (看跌) ==========
    SELL_CALL_DIVERGENCE_TD9 = "sell_call_divergence_td9"     # 顶钝化 + 高8/9
    SELL_CALL_DIVERGENCE_CONFIRM = "sell_call_divergence_confirm"  # 顶背离确认
    
    # ========== 卖沽平仓信号 ==========
    CLOSE_PUT_TD_HIGH9 = "close_put_td_high9"                 # 高8/9止盈
    CLOSE_PUT_TOP_DIVERGENCE = "close_put_top_divergence"     # 顶背离止盈
    CLOSE_PUT_FLATTENING_INVALID = "close_put_flattening_invalid"  # 钝化失效止损
    
    # ========== 卖购平仓信号 ==========
    CLOSE_CALL_TD_LOW9 = "close_call_td_low9"                 # 低8/9止盈
    CLOSE_CALL_BOTTOM_DIVERGENCE = "close_call_bottom_divergence"  # 底背离止盈
    CLOSE_CALL_FLATTENING_INVALID = "close_call_flattening_invalid"  # 钝化失效止损
    
    @staticmethod
    def get_valid_close_signals(open_signal: "SignalType") -> Set["SignalType"]:
        """
        获取某开仓信号对应的有效平仓信号集合
        
        Args:
            open_signal: 开仓信号类型
            
        Returns:
            该开仓信号可用的平仓信号集合
        """
        mapping: dict[SignalType, Set[SignalType]] = {
            # 卖沽持仓的平仓信号
            SignalType.SELL_PUT_DIVERGENCE_TD9: {
                SignalType.CLOSE_PUT_TD_HIGH9,
                SignalType.CLOSE_PUT_TOP_DIVERGENCE,
                SignalType.CLOSE_PUT_FLATTENING_INVALID,
            },
            SignalType.SELL_PUT_DIVERGENCE_CONFIRM: {
                SignalType.CLOSE_PUT_TD_HIGH9,
                SignalType.CLOSE_PUT_TOP_DIVERGENCE,
                SignalType.CLOSE_PUT_FLATTENING_INVALID,
            },
            # 卖购持仓的平仓信号
            SignalType.SELL_CALL_DIVERGENCE_TD9: {
                SignalType.CLOSE_CALL_TD_LOW9,
                SignalType.CLOSE_CALL_BOTTOM_DIVERGENCE,
                SignalType.CLOSE_CALL_FLATTENING_INVALID,
            },
            SignalType.SELL_CALL_DIVERGENCE_CONFIRM: {
                SignalType.CLOSE_CALL_TD_LOW9,
                SignalType.CLOSE_CALL_BOTTOM_DIVERGENCE,
                SignalType.CLOSE_CALL_FLATTENING_INVALID,
            },
        }
        return mapping.get(open_signal, set())
    
    def is_open_signal(self) -> bool:
        """判断是否为开仓信号"""
        return self.value.startswith("sell_")
    
    def is_close_signal(self) -> bool:
        """判断是否为平仓信号"""
        return self.value.startswith("close_")
    
    def is_put_signal(self) -> bool:
        """判断是否为卖沽相关信号"""
        return "put" in self.value
    
    def is_call_signal(self) -> bool:
        """判断是否为卖购相关信号"""
        return "call" in self.value
