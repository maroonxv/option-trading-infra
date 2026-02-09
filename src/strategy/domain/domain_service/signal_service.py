"""
SignalService - 信号判断领域服务

根据标的当前指标状态判断是否触发开平仓信号。
"""
from typing import Optional, Callable

from ..entity.target_instrument import TargetInstrument
from ..entity.position import Position


# 信号常量定义
class SignalConstants:
    """信号字符串常量"""
    # 卖沽开仓信号 (看涨)
    SELL_PUT_DIVERGENCE_TD9 = "sell_put_divergence_td9"
    SELL_PUT_DIVERGENCE_CONFIRM = "sell_put_divergence_confirm"
    
    # 卖购开仓信号 (看跌)
    SELL_CALL_DIVERGENCE_TD9 = "sell_call_divergence_td9"
    SELL_CALL_DIVERGENCE_CONFIRM = "sell_call_divergence_confirm"
    
    # 卖沽平仓信号
    CLOSE_PUT_TD_HIGH9 = "close_put_td_high9"
    CLOSE_PUT_TOP_DIVERGENCE = "close_put_top_divergence"
    CLOSE_PUT_FLATTENING_INVALID = "close_put_flattening_invalid"
    
    # 卖购平仓信号
    CLOSE_CALL_TD_LOW9 = "close_call_td_low9"
    CLOSE_CALL_BOTTOM_DIVERGENCE = "close_call_bottom_divergence"
    CLOSE_CALL_FLATTENING_INVALID = "close_call_flattening_invalid"
    
    @staticmethod
    def get_valid_close_signals(open_signal: str) -> set[str]:
        """
        获取某开仓信号对应的有效平仓信号集合
        
        Args:
            open_signal: 开仓信号字符串
            
        Returns:
            该开仓信号可用的平仓信号集合
        """
        mapping = {
            # 卖沽持仓的平仓信号
            SignalConstants.SELL_PUT_DIVERGENCE_TD9: {
                SignalConstants.CLOSE_PUT_TD_HIGH9,
                SignalConstants.CLOSE_PUT_TOP_DIVERGENCE,
                SignalConstants.CLOSE_PUT_FLATTENING_INVALID,
            },
            SignalConstants.SELL_PUT_DIVERGENCE_CONFIRM: {
                SignalConstants.CLOSE_PUT_TD_HIGH9,
                SignalConstants.CLOSE_PUT_TOP_DIVERGENCE,
                SignalConstants.CLOSE_PUT_FLATTENING_INVALID,
            },
            # 卖购持仓的平仓信号
            SignalConstants.SELL_CALL_DIVERGENCE_TD9: {
                SignalConstants.CLOSE_CALL_TD_LOW9,
                SignalConstants.CLOSE_CALL_BOTTOM_DIVERGENCE,
                SignalConstants.CLOSE_CALL_FLATTENING_INVALID,
            },
            SignalConstants.SELL_CALL_DIVERGENCE_CONFIRM: {
                SignalConstants.CLOSE_CALL_TD_LOW9,
                SignalConstants.CLOSE_CALL_BOTTOM_DIVERGENCE,
                SignalConstants.CLOSE_CALL_FLATTENING_INVALID,
            },
        }
        return mapping.get(open_signal, set())


class SignalService:
    """
    信号判断领域服务 (无状态, 纯函数)
    
    职责:
    - 检查开仓信号 (钝化 + TD 或 背离确认)
    - 检查平仓信号 (止盈/止损)
    """
    
    @staticmethod
    def check_open_signal(
        instrument: TargetInstrument,
        log_func: Optional[Callable] = None
    ) -> Optional[str]:
        """
        检查开仓信号
        
        卖沽开仓 (看涨):
        - 底钝化 + 低8/9 => SELL_PUT_DIVERGENCE_TD9
        - 底背离确认 => SELL_PUT_DIVERGENCE_CONFIRM
        
        卖购开仓 (看跌):
        - 顶钝化 + 高8/9 => SELL_CALL_DIVERGENCE_TD9
        - 顶背离确认 => SELL_CALL_DIVERGENCE_CONFIRM
        
        Args:
            instrument: 标的实体 (包含指标状态)
            log_func: 日志回调函数
            
        Returns:
            触发的信号字符串，无信号返回 None
        """
        dullness = instrument.dullness_state
        divergence = instrument.divergence_state
        td = instrument.td_value
        ema = instrument.ema_state
        
        if td is None:
            return None
            
        # 调试日志
        if log_func:
            log_func(f"[DEBUG-DECISION] {instrument.vt_symbol} 开仓检查:")
            log_func(f"  1. TD信号: 买入结构8/9={td.has_buy_8_9}, 卖出结构8/9={td.has_sell_8_9}")
            log_func(f"  2. 背离状态: 底部={divergence.is_bottom_confirmed}, 顶部={divergence.is_top_confirmed}")
            log_func(f"  3. 钝化状态: 底部={dullness.is_bottom_active}, 顶部={dullness.is_top_active}")
            
        # 卖沽信号 (看涨)
        if dullness.is_bottom_active and td.has_buy_8_9:
            if log_func: log_func(f"  -> 触发 SELL_PUT_DIVERGENCE_TD9 (底钝化 + 低9)")
            return SignalConstants.SELL_PUT_DIVERGENCE_TD9
        
        if divergence.is_bottom_confirmed:
            if log_func: log_func(f"  -> 触发 SELL_PUT_DIVERGENCE_CONFIRM (底背离确认)")
            return SignalConstants.SELL_PUT_DIVERGENCE_CONFIRM
        
        # 卖购信号 (看跌)
        if dullness.is_top_active and td.has_sell_8_9:
            if log_func: log_func(f"  -> 触发 SELL_CALL_DIVERGENCE_TD9 (顶钝化 + 高9)")
            return SignalConstants.SELL_CALL_DIVERGENCE_TD9
        
        if divergence.is_top_confirmed:
            if log_func: log_func(f"  -> 触发 SELL_CALL_DIVERGENCE_CONFIRM (顶背离确认)")
            return SignalConstants.SELL_CALL_DIVERGENCE_CONFIRM
        
        if log_func: log_func(f"  -> 无开仓信号")
        return None
    
    @staticmethod
    def check_close_signal(
        position: Position,
        instrument: TargetInstrument,
        log_func: Optional[Callable] = None
    ) -> Optional[str]:
        """
        检查平仓信号 (根据持仓的开仓信号类型)
        
        Args:
            position: 持仓实体
            instrument: 标的实体
            log_func: 日志回调函数
            
        Returns:
            匹配的平仓信号字符串，或 None
        """
        dullness = instrument.dullness_state
        divergence = instrument.divergence_state
        td = instrument.td_value
        
        if td is None:
            return None
        
        open_signal = position.signal
        if not open_signal:
            if log_func: log_func(f"  -> 持仓无信号类型")
            return None

        valid_close_signals = SignalConstants.get_valid_close_signals(open_signal)

        # 调试日志
        if log_func:
            log_func(f"[DEBUG-DECISION] {instrument.vt_symbol} 平仓检查 (持仓信号: {open_signal}):")
            log_func(f"  1. TD信号: 买入结构8/9={td.has_buy_8_9}, 卖出结构8/9={td.has_sell_8_9}")
            log_func(f"  2. 背离状态: 底部={divergence.is_bottom_confirmed}, 顶部={divergence.is_top_confirmed}")
            log_func(f"  3. 钝化状态: 底失={dullness.is_bottom_invalidated}, 顶失={dullness.is_top_invalidated}")
        
        # 卖沽持仓的平仓信号
        if open_signal in [SignalConstants.SELL_PUT_DIVERGENCE_TD9, SignalConstants.SELL_PUT_DIVERGENCE_CONFIRM]:
            # 止盈: 高8/9
            if td.has_sell_8_9 and SignalConstants.CLOSE_PUT_TD_HIGH9 in valid_close_signals:
                if log_func: log_func(f"  -> 触发 CLOSE_PUT_TD_HIGH9 (卖沽止盈: 高9)")
                return SignalConstants.CLOSE_PUT_TD_HIGH9
            # 止盈: 顶背离
            if divergence.is_top_confirmed and SignalConstants.CLOSE_PUT_TOP_DIVERGENCE in valid_close_signals:
                if log_func: log_func(f"  -> 触发 CLOSE_PUT_TOP_DIVERGENCE (卖沽止盈: 顶背离)")
                return SignalConstants.CLOSE_PUT_TOP_DIVERGENCE
            # 止损: 钝化失效
            if dullness.is_bottom_invalidated and SignalConstants.CLOSE_PUT_FLATTENING_INVALID in valid_close_signals:
                if log_func: log_func(f"  -> 触发 CLOSE_PUT_FLATTENING_INVALID (卖沽止损: 底钝化消失)")
                return SignalConstants.CLOSE_PUT_FLATTENING_INVALID
        
        # 卖购持仓的平仓信号
        if open_signal in [SignalConstants.SELL_CALL_DIVERGENCE_TD9, SignalConstants.SELL_CALL_DIVERGENCE_CONFIRM]:
            # 止盈: 低8/9
            if td.has_buy_8_9 and SignalConstants.CLOSE_CALL_TD_LOW9 in valid_close_signals:
                if log_func: log_func(f"  -> 触发 CLOSE_CALL_TD_LOW9 (卖购止盈: 低9)")
                return SignalConstants.CLOSE_CALL_TD_LOW9
            # 止盈: 底背离
            if divergence.is_bottom_confirmed and SignalConstants.CLOSE_CALL_BOTTOM_DIVERGENCE in valid_close_signals:
                if log_func: log_func(f"  -> 触发 CLOSE_CALL_BOTTOM_DIVERGENCE (卖购止盈: 底背离)")
                return SignalConstants.CLOSE_CALL_BOTTOM_DIVERGENCE
            # 止损: 钝化失效
            if dullness.is_top_invalidated and SignalConstants.CLOSE_CALL_FLATTENING_INVALID in valid_close_signals:
                if log_func: log_func(f"  -> 触发 CLOSE_CALL_FLATTENING_INVALID (卖购止损: 顶钝化消失)")
                return SignalConstants.CLOSE_CALL_FLATTENING_INVALID
        
        if log_func: log_func(f"  -> 无平仓信号")
        return None
    
